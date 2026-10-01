"""Offline package selection and recoverable, independently versioned updates.

The outer journal coordinates restore -> verified vanilla -> install. Each phase
uses the original five-target transaction engine. Downloads are never needed for
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
from .platforms import safe_path, operation_lock, game_guard, game_running, SafetyError
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
)
from .managed_engine import ManagedEngine, LegacyDescriptor, LEGACY_STATE

STATE = ".kks-manager"


def token(value):
    demand(
        type(value) is str and re.fullmatch("[0-9a-f]{32}", value), "Invalid local state identifier"
    )


def fingerprint(release):
    original = {
        "identity": sorted((x["path"], x["sha256"]) for x in release.data["identity"]),
        "targets": [],
    }
    for t in sorted(release.targets, key=lambda x: x["path"]):
        original["targets"].append(
            [
                t["path"],
                t["vanilla_sha256"],
                sorted((a["name"], a["vanilla_sha256"]) for a in t.get("assets", [])),
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
        fields(
            data,
            "schema root installation_id active highest_sequence release_ids baseline_ids retired",
        )
        integer(data["schema"], 2, 2)
        demand(
            data["root"] == str(self.root), "This saved installation belongs to another game folder"
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
                re.fullmatch(r"[0-9.]+/[0-9]+", key)
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
        fields(ref, "kind manifest state baseline")
        demand(ref["kind"] in ("managed", "legacy"), "Unknown installation owner")
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
        return result

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
        integer(data["schema"], 2, 2)
        demand(
            data["root"] == str(self.root) and data["id"] == ref["baseline"],
            "Baseline belongs to another installation",
        )
        release = self._release(ref)
        demand(
            data["fingerprint"] == fingerprint(release),
            "Baseline fingerprint disagrees with the signed release",
        )
        self._originals(data["originals"], release)
        engine = self._engine(ref)
        receipt = engine._receipt()
        if receipt:
            demand(
                data["originals"] == {p: r["before"] for p, r in receipt["files"].items()},
                "Original file-presence history changed",
            )
        return data

    def _originals(self, records, release):
        demand(
            type(records) is dict and set(records) == set(release.by_path),
            "Invalid original file set",
        )
        for p, h in records.items():
            permitted = [release.by_path[p]["vanilla_sha256"]] + ([None] if p in STRINGS else [])
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
        for path in ARCHIVES:
            demand(
                new.current(path) == package.by_path[path]["vanilla_sha256"],
                "The game update is incomplete or another mod changed an archive. Verify Fallout 76 in Steam before updating KKS: "
                + path,
            )
        cleanup = []
        for path in sorted(STRINGS):
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
        for path in ARCHIVES:
            demand(
                engine.current(path) == package.by_path[path]["vanilla_sha256"],
                "New vanilla archive changed during reconciliation",
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
            for path in ARCHIVES:
                demand(
                    engine.current(path) == package.by_path[path]["vanilla_sha256"],
                    "New game archive changed during cleanup",
                )
            path = self.path(entry["path"])
            demand(hash_file(path) == entry["before"], "String override changed during cleanup")
            path.unlink()
            sync_directory(path.parent)
            self.event("override_retired", {"index": index, "path": entry["path"]})
        self._verify_vanilla(plan, engine)

    def _sequence(self, package, state, active=None):
        m = package.manifest
        identity = m["content_version"] + "/" + str(m["package_revision"])
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
        reinstall = (
            m["release_sequence"] == state["highest_sequence"]
            and existing == package.manifest_digest
        )
        demand(
            same or reinstall or m["release_sequence"] > state["highest_sequence"],
            "This package is older than or conflicts with an installed release. Select a newer complete package",
        )

    def inspect(self, selected=None):
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
            old, _, cleanup = self._reconcile_inputs(selected, active)
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
            result["repair_available"] = cache_ready
            result["restore_available"] = True
            if active["kind"] == "legacy":
                result.update(
                    status="legacy_installed",
                    message="KKS 1.0 is installed. Select a content package to migrate, or restore vanilla without the old EXE.",
                )
            elif not cache_ready:
                result[
                    "message"
                ] += " The repair cache is incomplete; select the same content ZIP to repair. Vanilla restoration is still available."
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
                result.update(changed_payload_files=changed)
                if active["kind"] == "legacy" or active["manifest"] != selected.manifest_digest:
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
                self._sequence(selected, state)
                result.update(
                    status="ready",
                    message="The selected package matches this game and is ready to install.",
                )
            result.update(
                selected_content=selected.name,
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
        return result

    def _preflight_output(self, package, old, tx):
        package.verify_payloads()
        originals = {}
        for t in package.targets:
            if t["kind"] == "loose":
                continue
            src = old._backup_path(t["vanilla_sha256"]) if old else self.path(t["path"])
            demand(
                hash_file(src) == t["vanilla_sha256"],
                "The selected package needs a different vanilla archive",
            )
            stage = self.saved("preflight/" + tx + "/" + str(len(originals)) + ".ba2")
            stage.parent.mkdir(parents=True, exist_ok=True)
            replacements = {
                a["name"]: package.payload(a["payload"], a["sha256"]).read_bytes()
                for a in t["assets"]
            }
            BA2(src).replace_to(stage, replacements)
            demand(
                hash_file(stage) == t["after_sha256"] and stage.stat().st_size == t["after_size"],
                "The package output does not match this installer writer. Existing KKS was not removed",
            )
            originals[t["path"]] = str(stage)
        self.event("outputs_verified", tx)

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
            in ("restore_pending", "vanilla_committed", "install_pending", "cleanup_pending"),
            "Invalid coordinated recovery plan",
        )
        before = self._validate_state(p["before"])
        demand(
            before["installation_id"] == p["installation_id"], "Recovery installation ID changed"
        )
        for r in (p["old"], p["new"]):
            if r is not None:
                self._validate_ref(r)
                self._release(r)
        demand(p["old"] is not None or p["new"] is not None, "Empty recovery operation")
        demand((p["operation"] == "restore") == (p["new"] is None), "Invalid recovery destination")
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
            demand(type(p["cleanup"]) is list and len(p["cleanup"]) == 3, "Invalid cleanup plan")
            seen = set()
            for e in p["cleanup"]:
                fields(e, "path before after")
                path = e["path"]
                demand(path in STRINGS and path not in seen, "Invalid cleanup target")
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
        integer(b["schema"], 2, 2)
        token(b["id"])
        demand(
            b["root"] == str(self.root) and b["fingerprint"] == fingerprint(descriptor),
            "Invalid recovery baseline",
        )
        self._originals(b["originals"], descriptor)
        if p["operation"] == "reconcile":
            demand(
                all(b["originals"][e["path"]] == e["after"] for e in p["cleanup"]),
                "New baseline disagrees with cleanup results",
            )
        if p["new"]:
            demand(p["new"]["baseline"] == b["id"], "New installation points to another baseline")
        stored = strict_json(
            bounded_file(self.saved("baselines/" + b["id"] + ".json"), MAX_MANIFEST)
        )
        demand(stored == b, "Immutable baseline record changed")
        state = self._read_state()
        demand(state["installation_id"] == p["installation_id"], "Recovery root identity changed")
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
            state["highest_sequence"] = max(state["highest_sequence"], m["release_sequence"])
            state["release_ids"][
                m["content_version"] + "/" + str(m["package_revision"])
            ] = package.manifest_digest
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

    def run(self, operation, selected=None):
        demand(operation in ("install", "repair", "restore"), "Unknown operation")
        if selected is not None:
            # Reopen the authenticated local descriptor rather than use a stale UI object.
            selected = self.package(
                selected.manifest_digest if isinstance(selected, SignedRelease) else selected
            )
        with self._locks():
            demand(not self.saved("pending.json").exists(), "Recover the interrupted change first")
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
                demand(active is not None, "There is no managed installation to " + operation)
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
            identity_engine._identity()
            with game_guard(self.path("Fallout76.exe"), identity_engine.executable_hash()):
                identity_engine._identity(skip_exe=True)
                cleanup = None
                if reconcile:
                    _, _, cleanup = self._reconcile_inputs(selected, active, skip_exe=True)
                elif old:
                    old._identity(skip_exe=True)
                    old._validate_current(old._receipt())
                else:
                    identity_engine._validate_current(None)
                free = shutil.disk_usage(self.root).free
                total = sum(
                    self.path(t["path"]).stat().st_size if self.path(t["path"]).exists() else 0
                    for t in identity_engine.release.targets
                )
                demand(
                    free >= total * 6 + 128 * 1024 * 1024,
                    "Not enough free space for archive staging, backup and recovery",
                )
                tx = uuid.uuid4().hex
                if operation != "restore":
                    self._preflight_output(selected, None if reconcile else old, tx)
                if state["installation_id"] is None:
                    state["installation_id"] = uuid.uuid4().hex
                    durable_json(self.saved("installation.json"), state)
                if reconcile:
                    originals = {p: selected.by_path[p]["vanilla_sha256"] for p in ARCHIVES}
                    originals.update({e["path"]: e["after"] for e in cleanup})
                    baseline = {
                        "schema": 2,
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
                                    hash_file(dest) == entry["before"], "Damaged quarantine object"
                                )
                elif active:
                    baseline = self._baseline(active)
                    if baseline["id"] is None:
                        baseline["id"] = uuid.uuid4().hex
                else:
                    baseline = {
                        "schema": 2,
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
                            self.saved("installation.json"), self._after_state(plan, False)
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
                            "message": "Verified vanilla files restored. All restoration history is retained.",
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
                engine.current(path) == expected, "Vanilla checkpoint validation failed: " + path
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
            "message": "Verified vanilla is the recovery checkpoint. Select the content package to install again.",
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
            return {"status": "no_recovery_needed", "message": "There is no pending recovery."}
