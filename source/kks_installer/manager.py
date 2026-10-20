"""Offline package selection and recoverable, independently versioned updates.

The outer journal coordinates restore -> verified installation baseline -> install. Each phase
uses the profile-bound transaction engine. Downloads are never needed for
restoration; signed descriptors and installation-specific backups are retained.
"""

from contextlib import ExitStack
from copy import deepcopy
from pathlib import Path
import json
import re
import shutil
import uuid

from ._application import APP_VERSION
from .engine import demand, digest, durable_json, sync_directory, verified_copy
from .ba2 import BA2, hash_file
from .platforms import safe_path, operation_lock, game_guard, game_running, SafetyError, can_launch, launch_game
from .packages import (
    SignedRelease,
    import_package,
    strict_json,
    bounded_file,
    fields,
    integer,
    MAX_MANIFEST,
    ARCHIVES,
    STRINGS,
    archive_members,
    profile_strings,
)
from ._application import PROFILE, CONTENT_LANGUAGES, LEGACY_CONTENT_LANGUAGES, NEW_CONTENT_LANGUAGES
from . import string_modes as modes
from .managed_engine import ManagedEngine, LegacyDescriptor, LEGACY_STATE
from .equipment import FULL, NAMING_PROFILES
from .perks import ON, PERK_PROFILES
from .migration import inspect_original, consent_token
from .engine import is_digest

STATE = ".kks-manager"


def content_language(release):
    return getattr(release, "manifest", {}).get("game", {}).get("language", "en")


def content_strings(release):
    return profile_strings(getattr(release, "manifest", {}).get("profile", PROFILE))


def content_identity(package):
    m = package.manifest
    language = content_language(package)
    prefix = language + "/" if language != "en" else ""
    return prefix + m["content_version"] + "/" + str(m["package_revision"])


def sequence_highest(state, language):
    if state["schema"] == 2:
        return state["highest_sequence"] if language == "en" else 0
    return state["language_sequences"].get(language, 0)


def token(value):
    demand(
        type(value) is str and re.fullmatch("[0-9a-f]{32}", value),
        "Invalid local state identifier",
    )


def fingerprint(release):
    release = getattr(release, "certified", release)
    if content_language(release) != "en":
        # Language-specific member/target catalog; historical EN fingerprints stay exact.
        return digest(
            json.dumps(
                {
                    "language": content_language(release),
                    "identity": sorted((x["path"], x["sha256"]) for x in release.data["identity"]),
                    "targets": sorted(
                        (
                            t["path"],
                            t["vanilla_sha256"],
                            sorted((a["name"], a["vanilla_sha256"]) for a in t.get("assets", [])),
                        )
                        for t in release.targets
                    ),
                },
                sort_keys=True,
            ).encode()
        )
    original = {
        "identity": sorted((x["path"], x["sha256"]) for x in release.data["identity"]),
        "targets": [],
    }
    for t in sorted(release.targets, key=lambda x: x["path"]):
        if t["path"] not in set(ARCHIVES) | STRINGS:
            # The new Localization target is already bound by the unchanged
            # certified game-identity hash. Preserve historical fingerprints.
            continue
        original["targets"].append(
            [
                t["path"],
                t["vanilla_sha256"],
                # Preserve the 1.1.0 fingerprint across an expanded member set.
                # The complete vanilla archive hash above already authenticates
                # translate_en; the original member pins must stay byte-stable
                # for saved baselines and pending recovery from older installers.
                sorted(
                    (a["name"], a["vanilla_sha256"])
                    for a in t.get("assets", [])
                    if a["name"] == ARCHIVES.get(t["path"])
                ),
            ]
        )
    return digest(json.dumps(original, sort_keys=True).encode())


class Manager:
    def __init__(self, game, log=None, *, keys=None, legacy=None, event=None):
        candidate = Path(game).absolute()
        for parent in (candidate, *candidate.parents):
            if parent.exists():
                info = parent.lstat()
                demand(
                    not parent.is_symlink()
                    and not (getattr(info, "st_file_attributes", 0) & 0x400),
                    "A linked game folder is not supported",
                )
        self.root = candidate.resolve()
        demand(
            self.root.is_dir()
            and self.path("Fallout76.exe").is_file()
            and self.path("Data", regular=False).is_dir(),
            "Choose the Fallout 76 folder containing Fallout76.exe and Data",
        )
        self.log = log or (lambda text: None)
        self.keys = keys
        self.legacy = legacy or LegacyDescriptor()
        self.event = event or (lambda *args: None)
        self.state = self.path(STATE, regular=False)
        demand(not self.state.exists() or self.state.is_dir(), "Invalid KKS state folder")

    def path(self, relative, regular=True):
        return safe_path(self.root, relative, regular=regular)

    def saved(self, relative, regular=True):
        return self.path(STATE + "/" + relative, regular)

    def _empty(self):
        return {
            "schema": 2,
            "root": str(self.root),
            "installation_id": None,
            "active": None,
            "highest_sequence": 0,
            "release_ids": {},
            "baseline_ids": {},
            "retired": [],
        }

    def _validate_state(self, data):
        integer(data.get("schema") if isinstance(data, dict) else None, 2, 8)
        fields(
            data,
            "schema root installation_id active highest_sequence release_ids baseline_ids retired"
            + (" language_sequences" if data["schema"] >= 3 else ""),
        )
        if data["schema"] >= 3:
            fields(
                data["language_sequences"],
                "en de" if data["schema"] == 3 else
                "en de ru fr" if data["schema"] <= 6 else
                " ".join(LEGACY_CONTENT_LANGUAGES) if data["schema"] == 7 else " ".join(CONTENT_LANGUAGES),
            )
            for value in data["language_sequences"].values():
                integer(value, 0, 2**53 - 1)
            demand(
                data["highest_sequence"] == data["language_sequences"]["en"],
                "English sequence history is inconsistent",
            )
        demand(
            data["root"] == str(self.root),
            "This saved installation belongs to another game folder",
        )
        if data["installation_id"] is not None:
            token(data["installation_id"])
        integer(data["highest_sequence"], 0, 2**53 - 1)
        demand(
            type(data["release_ids"]) is dict
            and type(data["baseline_ids"]) is dict
            and len(data["release_ids"]) <= 10000
            and len(data["baseline_ids"]) <= 10000,
            "Invalid saved release registry",
        )
        for key, value in data["release_ids"].items():
            demand(
                re.fullmatch(
                    (
                        r"(?:(?:" + "|".join(CONTENT_LANGUAGES[1:]) + r")/)?[0-9.]+/[0-9]+"
                        if data["schema"] >= 8 else
                        r"(?:(?:de|ru|fr|ptbr)/)?[0-9.]+/[0-9]+"
                        if data["schema"] == 7 else
                        r"(?:(?:de|ru|fr)/)?[0-9.]+/[0-9]+"
                        if data["schema"] >= 4
                        else (
                            r"(?:de/)?[0-9.]+/[0-9]+" if data["schema"] == 3 else r"[0-9.]+/[0-9]+"
                        )
                    ),
                    key,
                )
                and type(value) is str
                and re.fullmatch("[0-9a-f]{64}", value),
                "Invalid saved content identity",
            )
        for key, value in data["baseline_ids"].items():
            demand(
                type(key) is str
                and 0 < len(key) <= 100
                and type(value) is str
                and re.fullmatch("[0-9a-f]{64}", value),
                "Invalid saved baseline identity",
            )
        if data["active"] is not None:
            self._validate_ref(data["active"])
        demand(
            type(data["retired"]) is list and len(data["retired"]) <= 10000,
            "Invalid retired installation records",
        )
        for ref in data["retired"]:
            self._validate_ref(ref)
        demand(
            data["active"] is None or data["active"] not in data["retired"],
            "Active installation is also marked obsolete",
        )
        return data

    def _read_state(self):
        p = self.saved("installation.json")
        if not p.exists():
            return self._empty()
        return self._validate_state(strict_json(bounded_file(p, MAX_MANIFEST)))

    def _validate_ref(self, ref):
        fields(ref, "kind manifest state baseline"
               + (" naming" if isinstance(ref, dict) and "naming" in ref else "")
               + (" perks" if isinstance(ref, dict) and "perks" in ref else "")
               + (" food junk" if isinstance(ref, dict) and ("food" in ref or "junk" in ref) else ""))
        demand(ref["kind"] in ("managed", "legacy"), "Unknown installation owner")
        if "naming" in ref:
            demand(ref["kind"] == "managed" and ref["naming"] in NAMING_PROFILES,
                   "Invalid saved equipment naming profile")
        if "perks" in ref:
            demand(ref["kind"] == "managed" and ref["perks"] in PERK_PROFILES,
                   "Invalid saved perk card choice")
        if "food" in ref:
            demand(ref["kind"] == "managed" and ref["food"] in modes.FOOD_PROFILES
                   and ref["junk"] in modes.JUNK_PROFILES, "Invalid saved food or junk choice")
        demand(
            type(ref["manifest"]) is str and re.fullmatch("[0-9a-f]{64}", ref["manifest"]),
            "Invalid descriptor reference",
        )
        if ref["kind"] == "legacy":
            demand(
                ref["manifest"] == self.legacy.manifest_digest
                and ref["state"] == LEGACY_STATE
                and ref["baseline"] is None,
                "Unrecognized legacy installation",
            )
        else:
            token(ref["state"])
            token(ref["baseline"])
        return ref

    def _release(self, ref):
        self._validate_ref(ref)
        if ref["kind"] == "legacy":
            return self.legacy
        folder = self.saved("packages/" + ref["manifest"], regular=False)
        result = SignedRelease.load(folder, self.keys)
        demand(
            result.manifest_digest == ref["manifest"],
            "Saved descriptor does not match its identity",
        )
        if "naming" in ref:
            demand(result.manifest["schema"] >= 2, "Saved naming profile requires a supported package")
        if "perks" in ref:
            demand(result.manifest["schema"] >= 3, "Saved perk choice requires a supported package")
        if "food" in ref:
            demand(result.manifest["schema"] == 4, "Saved food or junk choice requires a supported package")
        return result.with_features(naming=ref.get("naming", FULL), perks=ref.get("perks", ON),
                                    food=ref.get("food", modes.FOOD_DEFAULT), junk=ref.get("junk", modes.JUNK_DEFAULT))

    def package(self, manifest):
        demand(
            type(manifest) is str and re.fullmatch("[0-9a-f]{64}", manifest),
            "Invalid package selection",
        )
        result = SignedRelease.load(self.saved("packages/" + manifest, regular=False), self.keys)
        demand(result.manifest_digest == manifest, "Cached manifest digest changed")
        return result

    def _engine(self, ref):
        release = self._release(ref)
        state_name = (
            LEGACY_STATE if ref["kind"] == "legacy" else STATE + "/installs/" + ref["state"]
        )
        return ManagedEngine(self.root, release, self.log, state_name=state_name, event=self.event)

    def _locks(self):
        stack = ExitStack()
        try:
            stack.enter_context(operation_lock(self.saved("operation.lock")))
            # The 1.0 EXE does not know the stable lock. Always exclude it too.
            if self.path(LEGACY_STATE, regular=False).exists():
                stack.enter_context(operation_lock(self.path(LEGACY_STATE + "/operation.lock")))
            return stack
        except BaseException:
            stack.close()
            raise

    def select(self, zip_path):
        with self._locks():
            result = import_package(zip_path, self.saved("packages", regular=False), self.keys)
            self.log("Verified " + result.name + " content package.")
            return result

    def _historical(self, retired=()):
        legacy_ref = None
        for p in self.root.iterdir():
            if not p.name.startswith(".kks-") or p.name == STATE:
                continue
            checked = self.path(p.name, regular=False)
            demand(checked.is_dir(), "Unexpected KKS state object: " + p.name)
            receipt = self.path(p.name + "/receipt.json")
            pending = self.path(p.name + "/pending.json")
            if p.name == LEGACY_STATE:
                if receipt.exists() or pending.exists():
                    ref = {
                        "kind": "legacy",
                        "manifest": self.legacy.manifest_digest,
                        "state": LEGACY_STATE,
                        "baseline": None,
                    }
                    engine = self._engine(ref)
                    record = engine._receipt()
                    if pending.exists():
                        engine._read_journal()
                    if ref in retired:
                        demand(
                            not pending.exists(),
                            "An obsolete legacy state has an unresolved journal",
                        )
                    elif pending.exists() or (record and record["status"] == "installed"):
                        legacy_ref = ref
            elif pending.exists() or receipt.exists():
                # Historical experiments have no authenticated migration descriptor.
                record = (
                    strict_json(bounded_file(receipt, MAX_MANIFEST)) if receipt.exists() else {}
                )
                demand(
                    not pending.exists()
                    and type(record) is dict
                    and record.get("status") == "restored",
                    "An unsupported KKS experiment or older installer still owns this game: "
                    + p.name,
                )
        return legacy_ref

    def _owners(self, state, allowed=()):
        legacy = self._historical(state["retired"])
        for ref in state["retired"]:
            demand(
                not self._engine(ref).journal_path.exists(),
                "An obsolete installation has an unresolved journal",
            )
        active = state["active"]
        demand(
            not (legacy and active),
            "More than one KKS installation claims this game. Keep all backups and resolve the conflict",
        )
        root = self.saved("installs", regular=False)
        permitted = {
            r["state"]
            for r in [active, *allowed, *state["retired"]]
            if r and r["kind"] == "managed"
        }
        if root.exists():
            children = list(root.iterdir())
            demand(len(children) <= 10000, "Too many saved installations")
            for child in children:
                token(child.name)
                path = self.saved("installs/" + child.name, regular=False)
                demand(path.is_dir(), "Invalid saved installation directory")
                receipt = self.saved("installs/" + child.name + "/receipt.json")
                pending = self.saved("installs/" + child.name + "/pending.json")
                if child.name not in permitted:
                    record = (
                        strict_json(bounded_file(receipt, MAX_MANIFEST))
                        if receipt.exists()
                        else None
                    )
                    demand(
                        not pending.exists()
                        and (record is None or record.get("status") == "restored"),
                        "An unreferenced active installation needs recovery. Saved data has been retained",
                    )
        return active or legacy

    def _baseline(self, ref):
        if ref["kind"] == "legacy":
            engine = self._engine(ref)
            receipt = engine._receipt()
            demand(receipt is not None, "Legacy restoration receipt is missing")
            return {
                "schema": 2,
                "root": str(self.root),
                "id": None,
                "fingerprint": fingerprint(engine.release),
                "originals": {p: r["before"] for p, r in receipt["files"].items()},
            }
        p = self.saved("baselines/" + ref["baseline"] + ".json")
        data = strict_json(bounded_file(p, MAX_MANIFEST))
        fields(data, "schema root id fingerprint originals")
        integer(data["schema"], 2, 3)
        demand(
            data["root"] == str(self.root) and data["id"] == ref["baseline"],
            "Baseline belongs to another installation",
        )
        release = self._release(ref)
        demand(
            data["fingerprint"] == fingerprint(release),
            "Baseline fingerprint disagrees with the signed release",
        )
        self._originals(data["originals"], release, captured=data["schema"] == 3)
        engine = self._engine(ref)
        if data["schema"] == 3:
            demand(engine.baseline_context is not None and data["originals"] ==
                   {p: r["before"] for p, r in engine.baseline_context["files"].items()},
                   "Captured baseline has no matching verified installation context")
        receipt = engine._receipt()
        if receipt:
            demand(
                data["originals"] == {p: r["before"] for p, r in receipt["files"].items()},
                "Original file-presence history changed",
            )
        return data

    def _originals(self, records, release, *, captured=False):
        demand(
            type(records) is dict and set(records) == set(release.by_path),
            "Invalid original file set",
        )
        for p, h in records.items():
            if captured:
                demand(is_digest(h) or h is None and p in content_strings(release), "Invalid captured original")
                continue
            permitted = [release.by_path[p]["vanilla_sha256"]] + (
                [None] if p in content_strings(release) else []
            )
            demand(h in permitted, "Unknown vanilla original")

    def _verify_old(self, ref):
        engine = self._engine(ref)
        demand(
            not engine.journal_path.exists(),
            "Recover the interrupted operation before selecting an update",
        )
        engine._identity()
        receipt = engine._receipt()
        demand(
            receipt and receipt["status"] == "installed",
            "The active installation receipt is missing or no longer installed",
        )
        self._baseline(ref)
        for r in receipt["files"].values():
            if r["before"] is not None:
                engine._backup_path(r["before"])
        engine._validate_current(receipt)
        return engine

    def _historical_data(self, ref):
        engine = self._engine(ref)
        demand(
            not engine.journal_path.exists(),
            "The old installation has an unresolved journal; automatic baseline reconciliation is blocked",
        )
        receipt = engine._receipt()
        demand(
            receipt and receipt["status"] == "installed",
            "The old installation has no valid ownership receipt",
        )
        self._baseline(ref)
        for record in receipt["files"].values():
            if record["before"] is not None:
                engine._backup_path(record["before"])
        return engine

    def _reconcile_inputs(self, package, ref, *, skip_exe=False):
        old = self._historical_data(ref)
        demand(
            fingerprint(old.release) != fingerprint(package),
            "Reconciliation requires a different certified game baseline",
        )
        new = ManagedEngine(self.root, package, self.log, state_name=STATE + "/preflight")
        new._identity(skip_exe=skip_exe)
        for path in archive_members(package.manifest["profile"]):
            target = package.by_path[path]
            current = new.current(path)
            demand(current is not None, "Required archive is missing: " + path)
            if current != target["vanilla_sha256"] and path in old.release.by_path:
                previous = old.release.by_path[path]
                demand(current != previous["after_sha256"] and current != old.certified.by_path[path]["vanilla_sha256"],
                       "The game update left an old archive in place: " + path)
                archive = BA2(new.target(path))
                old_assets = {a["name"]: a["sha256"] for a in previous["assets"]}
                for asset in target["assets"]:
                    if asset["name"] in old_assets:
                        h = digest(archive.extract(asset["name"]))
                        demand(h != old_assets[asset["name"]] or h == asset["vanilla_sha256"],
                               "Old KKS resources remain in an updated archive. Verify the game before establishing a new baseline: " + path)
            inspect_original(new.target(path), target)
        cleanup = []
        for path in sorted(content_strings(package)):
            current = new.current(path)
            target = package.by_path[path]
            if current is None or current == target["vanilla_sha256"]:
                after = current
            elif current == old.release.by_path[path]["after_sha256"]:
                after = None
            else:
                raise SafetyError(
                    "A loose string table is neither new vanilla nor the receipt-owned old KKS file. It was left untouched: "
                    + path
                )
            cleanup.append({"path": path, "before": current, "after": after})
        return old, new, cleanup

    def _cleanup(self, plan, *, skip_exe=True):
        """Forward recovery only: never reintroduce an old override on a new build."""
        package = self._release(plan["new"])
        old = self._historical_data(plan["old"])
        engine = self._engine(plan["new"])
        engine._identity(skip_exe=skip_exe)
        for path in archive_members(package.manifest["profile"]):
            demand(
                engine.current(path) == plan["baseline"]["originals"][path],
                "New baseline archive changed during reconciliation",
            )
        for entry in plan["cleanup"]:
            demand(
                engine.current(entry["path"]) in (entry["before"], entry["after"]),
                "An outside writer changed a string table during reconciliation",
            )
            if entry["before"] != entry["after"]:
                backup = self.saved(
                    "quarantine/" + plan["transaction"] + "/" + entry["before"] + ".bin"
                )
                demand(
                    backup.is_file() and hash_file(backup) == entry["before"],
                    "A reconciliation quarantine copy is missing or damaged",
                )
        for index, entry in enumerate(plan["cleanup"]):
            if entry["before"] == entry["after"] or engine.current(entry["path"]) == entry["after"]:
                continue
            engine._identity(skip_exe=True)
            for path in archive_members(package.manifest["profile"]):
                demand(
                    engine.current(path) == plan["baseline"]["originals"][path],
                    "New game archive changed during cleanup",
                )
            path = self.path(entry["path"])
            demand(
                hash_file(path) == entry["before"],
                "String override changed during cleanup",
            )
            path.unlink()
            sync_directory(path.parent)
            self.event("override_retired", {"index": index, "path": entry["path"]})
        self._verify_vanilla(plan, engine)

    def _sequence(self, package, state, active=None):
        if active:
            demand(
                content_language(self._release(active)) == content_language(package),
                "Restore Baseline before switching the KKS content language",
            )
            demand(
                set(self._release(active).by_path) <= set(package.by_path),
                "Restore Baseline before selecting a package that removes managed game targets",
            )
        m = package.manifest
        identity = content_identity(package)
        highest = sequence_highest(state, content_language(package))
        existing = state["release_ids"].get(identity)
        demand(
            existing in (None, package.manifest_digest),
            "Different bytes reuse an already installed content version/revision",
        )
        known_baseline = state["baseline_ids"].get(m["game"]["baseline_id"])
        demand(
            known_baseline in (None, fingerprint(package)),
            "A baseline ID was reused for different game files",
        )
        same = bool(active and active["manifest"] == package.manifest_digest)
        reinstall = m["release_sequence"] == highest and existing == package.manifest_digest
        demand(
            same or reinstall or m["release_sequence"] > highest,
            "This package is older than or conflicts with an installed release. Select a newer complete package",
        )

    def inspect(self, selected=None, *, naming=None, perks=None, food=None, junk=None):
        if selected is not None:
            selected = selected.with_features(naming=naming, perks=perks, food=food, junk=junk)
        state = self._read_state()
        result = {
            "application_version": APP_VERSION,
            "game": str(self.root),
            "game_running": game_running(),
        }
        if self.saved("pending.json").exists():
            plan = self._plan()
            result.update(
                status="recovery_required",
                message="An interrupted change needs recovery before another operation.",
                phase=plan["phase"],
            )
            return result
        active = self._owners(state)
        if active and self._engine(active).journal_path.exists():
            self._engine(active)._read_journal()
            return dict(
                result,
                status="recovery_required",
                message="Recover the interrupted managed operation first.",
            )
        if active and selected and fingerprint(self._release(active)) != fingerprint(selected):
            selected.verify_payloads()
            self._sequence(selected, state, active)
            old, new_engine, cleanup = self._reconcile_inputs(selected, active)
            migration = new_engine.migration_info(ignore_loose=True)
            return dict(
                result,
                status="update_available",
                selected_content=selected.name,
                selected_manifest=selected.manifest_digest,
                installed_content=old.release.name,
                supported_build=selected.data["supported_build"],
                restore_available=False,
                repair_available=False,
                qa_status=selected.manifest["qa"]["status"],
                existing_modifications=migration["overlaps"],
                baseline_modified=migration["modified"],
                confirmation_token=consent_token(self.root, selected, migration["originals"]),
                message="The new game baseline is verified. Install will retire "
                + str(sum(e["before"] != e["after"] for e in cleanup))
                + " old KKS string overrides, preserve the old backups, and install this complete package. No old game archives will be restored.",
            )
        current = None
        if active:
            engine = self._verify_old(active)
            current = engine.inspect()
            cache_ready = False
            if active["kind"] == "managed":
                try:
                    engine.release.verify_payloads()
                    cache_ready = True
                except SafetyError:
                    pass
            result.update(current)
            result["application_version"] = APP_VERSION
            result["installed_content"] = engine.release.name
            result["installed_naming"] = getattr(engine.release, "naming", FULL)
            result["installed_perks"] = getattr(engine.release, "perks", ON)
            result["installed_food"] = getattr(engine.release, "food", modes.FOOD_DEFAULT)
            result["installed_junk"] = getattr(engine.release, "junk", modes.JUNK_DEFAULT)
            # Read-only UI metadata from the already inspected active release.
            # A repairable owner record is not a verified installed configuration.
            result["installed_verified"] = (
                active["kind"] == "managed" and current["status"] == "installed"
            )
            if active["kind"] == "managed":
                result["installed_manifest"] = engine.release.manifest_digest
                result["installed_equipment_naming_available"] = "equipment_naming" in engine.release.manifest
                result["installed_perk_cards_available"] = "perk_cards" in engine.release.manifest
                result["installed_string_modes_available"] = "string_modes" in engine.release.manifest
            result["repair_available"] = cache_ready
            result["restore_available"] = True
            if active["kind"] == "legacy":
                result.update(
                    status="legacy_installed",
                    message="KKS 1.0 is installed. Select a content package to migrate, or restore the baseline without the old EXE.",
                )
            elif not cache_ready:
                result[
                    "message"
                ] += " The repair cache is incomplete; select the same content ZIP to repair. Baseline restoration is still available."
        if selected:
            selected.verify_payloads()
            if active:
                demand(
                    fingerprint(self._release(active)) == fingerprint(selected),
                    "The selected package uses a different game baseline. Complete Steam verification; old backups will not be applied to a new game build",
                )
                self._sequence(selected, state, active)
                changed = sum(
                    a["sha256"]
                    != getattr(self._release(active), "files", {}).get(p, {}).get("sha256")
                    for p, a in selected.files.items()
                )
                result.update(
                    changed_payload_files=changed,
                    payload_file_count=len(selected.files),
                )
                if (active["kind"] == "legacy" or active["manifest"] != selected.manifest_digest
                        or active.get("naming", FULL) != selected.naming
                        or active.get("perks", ON) != selected.perks
                        or active.get("food", modes.FOOD_DEFAULT) != selected.food
                        or active.get("junk", modes.JUNK_DEFAULT) != selected.junk):
                    result.update(
                        status="update_available",
                        message="This complete package can be installed directly; intermediate updates are not required.",
                    )
            else:
                selected_engine = ManagedEngine(
                    self.root, selected, self.log, state_name=STATE + "/preflight"
                )
                selected_engine._identity()
                selected_engine._validate_current(None)
                migration = selected_engine.migration_info()
                result.update(existing_modifications=migration["overlaps"],
                              baseline_modified=migration["modified"],
                              confirmation_token=consent_token(self.root, selected, migration["originals"]))
                self._sequence(selected, state)
                result.update(
                    status="ready",
                    message="The selected package matches this game and is ready to install.",
                )
            result.update(
                selected_content=selected.name,
                selected_naming=selected.naming,
                equipment_naming_available="equipment_naming" in selected.manifest,
                selected_perks=selected.perks,
                perk_cards_available="perk_cards" in selected.manifest,
                selected_food=selected.food,
                selected_junk=selected.junk,
                string_modes_available="string_modes" in selected.manifest,
                selected_manifest=selected.manifest_digest,
                supported_build=selected.data["supported_build"],
                qa_status=selected.manifest["qa"]["status"],
            )
        elif not active:
            result.update(
                status="package_required",
                message="Choose a complete KKS content ZIP to check compatibility and install.",
                restore_available=False,
                repair_available=False,
            )
        result["installed_play_available"] = (
            result.get("installed_verified", False)
            and (selected is None or selected.manifest_digest == result.get("installed_manifest"))
            and not result["game_running"] and can_launch(self.root)
        )
        result["play_available"] = (
            result["status"] == "installed" and result["installed_play_available"]
        )
        return result

    def play(self):
        with self._locks():
            demand(not game_running(), "Fallout 76 is already running")
            result = self.inspect()
            demand(result.get("play_available"), "Check and finish installation or recovery before launching Fallout 76")
            launch_game(self.root)
        return {"status": "launched", "message": "Fallout 76 launch requested through Steam."}

    def _preflight_output(self, package, old, tx, cleanup=None):
        package.verify_payloads()
        originals, outputs = {}, {}
        overlaps = []
        migrated = bool(old and old.baseline_context is not None)
        old_receipt = old._receipt() if old else None
        cleaned = {e["path"]: e["after"] for e in cleanup or []}
        for t in package.targets:
            original = (old_receipt["files"][t["path"]]["before"]
                        if old and t["path"] in old.release.by_path else self._current(t["path"]))
            if t["path"] in cleaned:
                original = cleaned[t["path"]]
            originals[t["path"]] = original
            src = (old._backup_path(original) if old and t["path"] in old.release.by_path and original
                   else self.path(t["path"]))
            if original is not None:
                overlaps.extend(inspect_original(src, t))
                migrated |= original != t["vanilla_sha256"]
            if t["kind"] == "loose":
                continue
            stage = self.saved("preflight/" + tx + "/" + str(len(outputs)) + ".ba2")
            stage.parent.mkdir(parents=True, exist_ok=True)
            replacements = {
                a["name"]: package.payload(a["payload"], a["sha256"]).read_bytes()
                for a in t["assets"]
            }
            archive = BA2(src)
            archive.replace_to(stage, replacements)
            if original == t["vanilla_sha256"]:
                demand(hash_file(stage) == t["after_sha256"] and stage.stat().st_size == t["after_size"],
                       "The package output does not match this installer writer. Existing KKS was not removed")
            outputs[t["path"]] = stage
        self.event("outputs_verified", tx)
        return {"originals": originals, "outputs": outputs, "overlaps": overlaps, "migrated": migrated}

    def _current(self, path):
        return hash_file(self.path(path)) if self.path(path).is_file() else None

    def _capture_context(self, ref, prepared, old):
        """Back up all originals and prove all outputs BEFORE restoring an old install."""
        engine = self._engine(ref)
        files = {}
        for target in engine.certified.targets:
            path = target["path"]
            original = prepared["originals"][path]
            if original is not None:
                src = (old._backup_path(original) if old and path in old.release.by_path else self.path(path))
                engine._backup(src, original)
            after = target["after_sha256"]
            if target["kind"] == "archive":
                stage = prepared["outputs"][path]
                after = hash_file(stage)
                engine._backup(stage, after)
            files[path] = {"before": original, "after": after}
        context = {"schema": 1, "manifest": engine.certified.manifest_digest,
                   "root": str(self.root), "files": files}
        path = engine.state_path("baseline-context.json")
        if path.exists():
            demand(strict_json(bounded_file(path, MAX_MANIFEST)) == context, "Immutable baseline context changed")
        else:
            durable_json(path, context)
        self._engine(ref)  # Read back and verify the complete proof, including every backup.

    def _write_plan(self, plan, phase):
        plan["phase"] = phase
        self.event("before_" + phase, plan)
        durable_json(self.saved("pending.json"), plan)
        self.event("after_" + phase, plan)

    def _plan(self):
        p = strict_json(bounded_file(self.saved("pending.json"), MAX_MANIFEST))
        fields(
            p,
            "schema root installation_id transaction operation phase old new before baseline cleanup",
        )
        integer(p["schema"], 2, 2)
        token(p["installation_id"])
        token(p["transaction"])
        demand(
            p["root"] == str(self.root)
            and p["operation"] in ("install", "repair", "restore", "reconcile")
            and p["phase"]
            in (
                "restore_pending",
                "vanilla_committed",
                "install_pending",
                "cleanup_pending",
            ),
            "Invalid coordinated recovery plan",
        )
        before = self._validate_state(p["before"])
        demand(
            before["installation_id"] == p["installation_id"],
            "Recovery installation ID changed",
        )
        for r in (p["old"], p["new"]):
            if r is not None:
                self._validate_ref(r)
                self._release(r)
        demand(p["old"] is not None or p["new"] is not None, "Empty recovery operation")
        demand(
            (p["operation"] == "restore") == (p["new"] is None),
            "Invalid recovery destination",
        )
        if p["operation"] == "repair":
            demand(p["old"] == p["new"], "Repair changed its content identity")
        if p["old"] and p["old"]["kind"] == "managed":
            demand(
                before["active"] == p["old"],
                "Recovery owner does not match the previous active release",
            )
        elif p["old"]:
            demand(before["active"] is None, "Ambiguous legacy recovery owner")
        else:
            demand(before["active"] is None, "Fresh installation has an active predecessor")
        descriptor = self._release(p["new"] or p["old"])
        if p["operation"] == "reconcile":
            demand(
                p["old"] is not None and p["new"] is not None and p["phase"] != "restore_pending",
                "Invalid new-baseline operation",
            )
            old_descriptor = self._release(p["old"])
            demand(
                fingerprint(old_descriptor) != fingerprint(descriptor),
                "Reconciliation did not change game baseline",
            )
            demand(
                type(p["cleanup"]) is list and len(p["cleanup"]) == 3,
                "Invalid cleanup plan",
            )
            seen = set()
            for e in p["cleanup"]:
                fields(e, "path before after")
                path = e["path"]
                demand(
                    path in content_strings(descriptor) and path not in seen,
                    "Invalid cleanup target",
                )
                seen.add(path)
                allowed = (None, descriptor.by_path[path]["vanilla_sha256"])
                demand(
                    e["after"] in allowed,
                    "Cleanup may only preserve new vanilla or remove an old owned override",
                )
                if e["before"] != e["after"]:
                    demand(
                        e["after"] is None
                        and e["before"] == old_descriptor.by_path[path]["after_sha256"],
                        "Cleanup does not own these old bytes",
                    )
        else:
            demand(
                p["cleanup"] is None and p["phase"] != "cleanup_pending",
                "Unexpected cleanup operation",
            )
            if p["new"] and p["old"]:
                demand(
                    fingerprint(self._release(p["old"])) == fingerprint(descriptor),
                    "Recovery cannot cross game baselines",
                )
        b = p["baseline"]
        fields(b, "schema root id fingerprint originals")
        integer(b["schema"], 2, 3)
        token(b["id"])
        demand(
            b["root"] == str(self.root) and b["fingerprint"] == fingerprint(descriptor),
            "Invalid recovery baseline",
        )
        self._originals(b["originals"], descriptor, captured=b["schema"] == 3)
        if b["schema"] == 3:
            owner = self._engine(p["new"] or p["old"])
            demand(owner.baseline_context is not None and b["originals"] ==
                   {path: r["before"] for path, r in owner.baseline_context["files"].items()},
                   "Recovery baseline differs from verified backups")
        if p["operation"] == "reconcile":
            demand(
                all(b["originals"][e["path"]] == e["after"] for e in p["cleanup"]),
                "New baseline disagrees with cleanup results",
            )
        if p["new"]:
            demand(
                p["new"]["baseline"] == b["id"],
                "New installation points to another baseline",
            )
        stored = strict_json(
            bounded_file(self.saved("baselines/" + b["id"] + ".json"), MAX_MANIFEST)
        )
        demand(stored == b, "Immutable baseline record changed")
        state = self._read_state()
        demand(
            state["installation_id"] == p["installation_id"],
            "Recovery root identity changed",
        )
        permitted = [before, self._after_state(p, False)]
        if p["new"]:
            permitted.append(self._after_state(p, True))
        demand(state in permitted, "Active state changed outside this transaction")
        self._owners(before, [r for r in (p["old"], p["new"]) if r])
        return p

    def _after_state(self, plan, installed):
        state = deepcopy(plan["before"])
        state["active"] = plan["new"] if installed else None
        if plan["operation"] == "reconcile" and plan["old"] not in state["retired"]:
            state["retired"].append(plan["old"])
        if installed:
            package = self._release(plan["new"])
            m = package.manifest
            language = content_language(package)
            if m["schema"] >= 2 and state["schema"] < 5:
                state["language_sequences"] = {
                    code: sequence_highest(state, code) for code in ("en", "de", "ru", "fr")
                }
                state["schema"] = 5
            if m["schema"] >= 3:
                state["schema"] = max(state["schema"], 6)
            if language != "en" and state["schema"] == 2:
                state["schema"] = 3
                state["language_sequences"] = {"en": state["highest_sequence"], "de": 0}
            if language in ("ru", "fr") and state["schema"] < 4:
                state["schema"] = 4
                state["language_sequences"].update(ru=0, fr=0)
            if language == "ptbr" and state["schema"] < 7:
                state["language_sequences"] = {
                    code: sequence_highest(state, code) for code in LEGACY_CONTENT_LANGUAGES
                }
                state["schema"] = 7
            if m["schema"] == 4 or language in NEW_CONTENT_LANGUAGES:
                state["language_sequences"] = {code: sequence_highest(state, code) for code in CONTENT_LANGUAGES}
                state["schema"] = 8
            if state["schema"] >= 3:
                state["language_sequences"][language] = max(
                    state["language_sequences"][language], m["release_sequence"]
                )
                state["highest_sequence"] = state["language_sequences"]["en"]
            else:
                state["highest_sequence"] = max(state["highest_sequence"], m["release_sequence"])
            state["release_ids"][content_identity(package)] = package.manifest_digest
            state["baseline_ids"][m["game"]["baseline_id"]] = fingerprint(package)
        return state

    def _publish(self, plan, state, outcome):
        self.event("before_state_publish", plan)
        durable_json(self.saved("installation.json"), state)
        self.event("after_state_publish", plan)
        history = dict(plan, outcome=outcome)
        durable_json(self.saved("history/" + plan["transaction"] + ".json"), history)
        self.event("before_plan_retirement", plan)
        self.saved("pending.json").unlink()
        sync_directory(self.state)
        self.event("after_plan_retirement", plan)

    def run(self, operation, selected=None, *, naming=None, perks=None, food=None, junk=None, accept_modifications=None):
        demand(operation in ("install", "repair", "restore"), "Unknown operation")
        if selected is not None:
            naming = getattr(selected, "naming", FULL) if naming is None else naming
            perks = getattr(selected, "perks", ON) if perks is None else perks
            food = getattr(selected, "food", modes.FOOD_DEFAULT) if food is None else food
            junk = getattr(selected, "junk", modes.JUNK_DEFAULT) if junk is None else junk
            # Reopen the authenticated local descriptor rather than use a stale UI object.
            selected = self.package(
                selected.manifest_digest if isinstance(selected, SignedRelease) else selected
            ).with_features(naming=naming, perks=perks, food=food, junk=junk)
        with self._locks():
            demand(
                not self.saved("pending.json").exists(),
                "Recover the interrupted change first",
            )
            state = self._read_state()
            active = self._owners(state)
            reconcile = bool(
                operation == "install"
                and active
                and selected
                and fingerprint(self._release(active)) != fingerprint(selected)
            )
            old = (
                (self._historical_data(active) if reconcile else self._verify_old(active))
                if active
                else None
            )
            if operation != "install":
                demand(
                    active is not None,
                    "There is no managed installation to " + operation,
                )
            if operation == "repair":
                demand(
                    active["kind"] == "managed",
                    "Select a complete content ZIP to migrate the 1.0 installation",
                )
                selected = self._release(active)
            if operation != "restore":
                demand(selected is not None, "Choose a complete KKS content ZIP first")
                selected.verify_payloads()
                self._sequence(selected, state, active)
                if old and not reconcile:
                    demand(
                        fingerprint(old.release) == fingerprint(selected),
                        "Different game baseline: old archives will not be restored onto updated game files",
                    )
                identity_engine = ManagedEngine(
                    self.root, selected, self.log, state_name=STATE + "/preflight"
                )
            else:
                identity_engine = old
            # On the same certified baseline, the current owner authenticates
            # its patched Localization archive. Incoming content may have a
            # different after-hash; it is checked normally after old restoration.
            identity_check = old if old and not reconcile else identity_engine
            identity_check._identity()
            with game_guard(self.path("Fallout76.exe"), identity_engine.executable_hash()):
                identity_check._identity(skip_exe=True)
                cleanup = None
                if reconcile:
                    _, _, cleanup = self._reconcile_inputs(selected, active, skip_exe=True)
                    migration = identity_engine.migration_info(ignore_loose=True)
                elif old:
                    old._identity(skip_exe=True)
                    old._validate_current(old._receipt())
                else:
                    identity_engine._validate_current(None)
                    migration = identity_engine.migration_info()
                if (not old or reconcile) and migration["overlaps"]:
                    demand(accept_modifications == consent_token(self.root, selected, migration["originals"]),
                           "Existing modifications overlap KKS resources. Check the installation and confirm the exact baseline before continuing.")
                free = shutil.disk_usage(self.root).free
                total = sum(
                    (self.path(t["path"]).stat().st_size if self.path(t["path"]).exists() else 0)
                    for t in identity_engine.release.targets
                )
                demand(
                    free >= total * 6 + 128 * 1024 * 1024,
                    "Not enough free space for archive staging, backup and recovery",
                )
                tx = uuid.uuid4().hex
                if operation != "restore":
                    selected.prepare_features(self.root)
                    prepared = self._preflight_output(selected, None if reconcile else old, tx, cleanup)
                    if not old or reconcile:
                        demand({p: identity_engine.current(p) for p in selected.by_path} == migration["originals"],
                               "Files changed after migration confirmation")
                if state["installation_id"] is None:
                    state["installation_id"] = uuid.uuid4().hex
                    durable_json(self.saved("installation.json"), state)
                if reconcile:
                    originals = prepared["originals"]
                    baseline = {
                        "schema": 3 if prepared["migrated"] else 2,
                        "root": str(self.root),
                        "id": uuid.uuid4().hex,
                        "fingerprint": fingerprint(selected),
                        "originals": originals,
                    }
                    for entry in cleanup:
                        if entry["before"] != entry["after"]:
                            dest = self.saved("quarantine/" + tx + "/" + entry["before"] + ".bin")
                            if not dest.exists():
                                verified_copy(self.path(entry["path"]), dest, entry["before"])
                            else:
                                demand(
                                    hash_file(dest) == entry["before"],
                                    "Damaged quarantine object",
                                )
                elif active:
                    baseline = self._baseline(active)
                    if baseline["id"] is None:
                        baseline["id"] = uuid.uuid4().hex
                    if selected and set(baseline["originals"]) != set(selected.by_path):
                        # Expand into a NEW immutable baseline; never rewrite an
                        # old five-target record or lose its original presence.
                        expanded = deepcopy(baseline)
                        expanded["id"] = uuid.uuid4().hex
                        for path in set(selected.by_path) - set(baseline["originals"]):
                            expected = selected.by_path[path]["vanilla_sha256"]
                            demand(
                                identity_engine.current(path) == expected,
                                "New managed archive is not certified vanilla: " + path,
                            )
                            expanded["originals"][path] = expected
                        self._originals(expanded["originals"], selected, captured=expanded["schema"] == 3)
                        baseline = expanded
                else:
                    baseline = {
                        "schema": 3 if prepared["migrated"] else 2,
                        "root": str(self.root),
                        "id": uuid.uuid4().hex,
                        "fingerprint": fingerprint(selected),
                        "originals": {p: identity_engine.current(p) for p in selected.by_path},
                    }
                bpath = self.saved("baselines/" + baseline["id"] + ".json")
                if bpath.exists():
                    demand(
                        strict_json(bounded_file(bpath, MAX_MANIFEST)) == baseline,
                        "Immutable baseline changed",
                    )
                else:
                    durable_json(bpath, baseline)
                new = (
                    None
                    if operation == "restore"
                    else (
                        active
                        if operation == "repair"
                        else {
                            "kind": "managed",
                            "manifest": selected.manifest_digest,
                            "state": uuid.uuid4().hex,
                            "baseline": baseline["id"],
                        }
                    )
                )
                if new is not None and selected.manifest["schema"] >= 2:
                    new = dict(new, naming=selected.naming)
                if new is not None and selected.manifest["schema"] >= 3:
                    new = dict(new, perks=selected.perks)
                if new is not None and selected.manifest["schema"] == 4:
                    new = dict(new, food=selected.food, junk=selected.junk)
                if new is not None and prepared["migrated"]:
                    self._capture_context(new, prepared, None if reconcile else old)
                plan = {
                    "schema": 2,
                    "root": str(self.root),
                    "installation_id": state["installation_id"],
                    "transaction": tx,
                    "operation": "reconcile" if reconcile else operation,
                    "phase": "install_pending",
                    "old": active,
                    "new": new,
                    "before": state,
                    "baseline": baseline,
                    "cleanup": cleanup,
                }
                try:
                    if reconcile:
                        self._write_plan(plan, "cleanup_pending")
                        self._cleanup(plan)
                        durable_json(
                            self.saved("installation.json"),
                            self._after_state(plan, False),
                        )
                        self._write_plan(plan, "vanilla_committed")
                    elif old and operation != "repair":
                        self._write_plan(plan, "restore_pending")
                        old._run_locked("restore")
                        self._verify_vanilla(plan, old)
                        self._write_plan(plan, "vanilla_committed")
                    if operation == "restore":
                        self._publish(plan, self._after_state(plan, False), "restored")
                        return {
                            "status": "restored",
                            "message": "Baseline restored and verified. All restoration history is retained.",
                        }
                    self._write_plan(plan, "install_pending")
                    engine = self._engine(new)
                    engine.release.verify_payloads()
                    engine._run_locked("repair" if operation == "repair" else "install")
                    self._verify_installed(new, skip_exe=True)
                    self._publish(plan, self._after_state(plan, True), "installed")
                    return {
                        "status": "installed",
                        "message": engine.release.name + " installed and verified.",
                        "content": engine.release.name,
                    }
                except Exception as cause:
                    if self.saved("pending.json").exists():
                        try:
                            recovery = self._recover_locked(skip_exe=True)
                        except Exception as problem:
                            raise SafetyError(
                                f"Operation stopped: {cause}. Recovery needs attention: {problem}. Backups and journals are retained."
                            ) from cause
                        raise SafetyError(
                            f'Operation stopped: {cause}. {recovery["message"]}'
                        ) from cause
                    raise

    def _verify_vanilla(self, plan, engine):
        engine._identity(skip_exe=True)
        for path, expected in plan["baseline"]["originals"].items():
            demand(
                engine.current(path) == expected,
                "Baseline checkpoint validation failed: " + path,
            )
        engine._validate_current(None)

    def _verify_installed(self, ref, *, skip_exe=False):
        engine = self._engine(ref)
        engine._identity(skip_exe=skip_exe)
        receipt = engine._receipt()
        demand(
            receipt and receipt["status"] == "installed",
            "Installed checkpoint has no valid receipt",
        )
        self._baseline(ref)
        for record in receipt["files"].values():
            if record["before"] is not None:
                engine._backup_path(record["before"])
        values = engine._validate_current(receipt)
        demand(
            all(v["sha256"] == engine.release.by_path[v["path"]]["after_sha256"] for v in values),
            "Installed checkpoint is incomplete",
        )

    def _recover_locked(self, *, skip_exe=False):
        plan = self._plan()
        old = self._engine(plan["old"]) if plan["old"] else None
        new = self._engine(plan["new"]) if plan["new"] else None
        owner = (
            new if plan["phase"] == "install_pending" or plan["operation"] == "reconcile" else old
        )
        demand(owner is not None, "Recovery has no owning phase")
        owner._identity(skip_exe=skip_exe)
        if plan["operation"] == "reconcile" and plan["phase"] in (
            "cleanup_pending",
            "vanilla_committed",
        ):
            self._cleanup(plan, skip_exe=skip_exe)
            self._publish(plan, self._after_state(plan, False), "recovered_new_vanilla")
            return {
                "status": "recovered",
                "message": "The new game baseline is verified and old KKS overrides are retired. Select the new package to install; historical backups were not restored.",
            }
        if owner.journal_path.exists():
            owner._recover_locked()
            self.event("phase_recovered", plan)
        receipt = owner._receipt()
        if plan["operation"] == "repair" and receipt and receipt["status"] == "installed":
            owner._validate_current(receipt)
            self._baseline(plan["old"])
            for record in receipt["files"].values():
                if record["before"] is not None:
                    owner._backup_path(record["before"])
            self._publish(plan, plan["before"], "recovered_repair")
            return {
                "status": "recovered",
                "message": "The managed file state was recovered. Run Check to see whether repair is still needed.",
            }
        if plan["phase"] == "install_pending" and receipt and receipt["status"] == "installed":
            self._verify_installed(plan["new"], skip_exe=skip_exe)
            self._publish(plan, self._after_state(plan, True), "recovered_installed")
            return {
                "status": "recovered",
                "message": "The completed installation was verified and its saved state recovered.",
            }
        if (
            old
            and plan["phase"] == "restore_pending"
            and receipt
            and receipt["status"] == "installed"
        ):
            old._validate_current(receipt)
            self._publish(plan, plan["before"], "recovered_previous")
            return {
                "status": "recovered",
                "message": "The previous managed file state was recovered; retry the update when ready.",
            }
        self._verify_vanilla(plan, owner)
        self._publish(plan, self._after_state(plan, False), "recovered_vanilla")
        return {
            "status": "recovered",
            "message": "The verified installation baseline is the recovery checkpoint. Select the content package to install again.",
        }

    def recover(self):
        with self._locks():
            if self.saved("pending.json").exists():
                plan = self._plan()
                ref = (
                    plan["new"]
                    if plan["phase"] == "install_pending" or plan["operation"] == "reconcile"
                    else plan["old"]
                )
                engine = self._engine(ref)
                engine._identity()
                with game_guard(self.path("Fallout76.exe"), engine.executable_hash()):
                    return self._recover_locked(skip_exe=True)
            state = self._read_state()
            ref = self._owners(state)
            if ref:
                engine = self._engine(ref)
                if engine.journal_path.exists():
                    engine._identity()
                    with game_guard(self.path("Fallout76.exe"), engine.executable_hash()):
                        engine._identity(skip_exe=True)
                        engine._recover_locked()
                    return {
                        "status": "recovered",
                        "message": "The interrupted managed operation was recovered.",
                    }
            return {
                "status": "no_recovery_needed",
                "message": "There is no pending recovery.",
            }
