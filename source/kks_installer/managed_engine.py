"""Strict profile-bound state reader around the file transaction engine."""

import re
from .engine import Installer, demand, digest
from .ba2 import hash_file
from .packages import (
    bounded_file,
    strict_json,
    fields,
    integer,
    ARCHIVES,
    STRINGS,
    IDENTITIES,
    MAX_MANIFEST,
    archive_members,
    profile_strings,
    profile_language,
    LOCALIZATION,
)
from ._application import PROFILE, GERMAN_PROFILE
from .platforms import SafetyError
from . import _legacy

LEGACY_STATE = ".kks-installer-1.0.0"


class LegacyDescriptor:
    def __init__(self, raw=None, pin=None):
        raw = _legacy.MANIFEST_BYTES if raw is None else raw
        pin = _legacy.MANIFEST_SHA256 if pin is None else pin
        demand(digest(raw) == pin, "The built-in 1.0.0 restoration descriptor is damaged")
        self.data = strict_json(raw)
        self.manifest_digest = pin
        self.name = self.data["release"]
        self.targets = self.data["targets"]
        self.by_path = {t["path"]: t for t in self.targets}
        demand(
            set(self.by_path) == set(ARCHIVES) | STRINGS,
            "Invalid legacy target catalog",
        )

    def verify_payloads(self):
        raise SafetyError("The legacy descriptor permits restoration and recovery only")

    def payload(self, *args):
        raise SafetyError("Legacy content is not bundled. Select a signed content package")


class ManagedEngine(Installer):
    def __init__(self, game, release, log=None, *, state_name, event=None):
        profile = getattr(release, "manifest", {}).get("profile", PROFILE)
        catalog = archive_members(profile)
        self.strings = profile_strings(profile)
        self.interface_overrides = {"Data/" + n for names in catalog.values() for n in names}
        self.interface_overrides.add("Data/interface/fontconfig.txt")
        # Historical EN profiles also refuse a loose translation override.
        if profile_language(profile) == "en":
            self.interface_overrides.add("Data/interface/translate_en.txt")
        demand(
            set(release.by_path) == set(catalog) | self.strings,
            "Invalid managed target set",
        )
        demand(
            {i["path"] for i in release.data["identity"]} == IDENTITIES,
            "Invalid managed game identity",
        )
        for path, names in catalog.items():
            t = release.by_path[path]
            demand(
                t["kind"] == "archive" and [a["name"] for a in t["assets"]] == list(names),
                "Forbidden archive operation",
            )
        self.event = event or (lambda *args: None)
        super().__init__(game, release, log, state_name=state_name)

    def _identity(self, *, skip_exe=False):
        self.log("Verifying the supported game build…")
        for item in self.release.data["identity"]:
            if skip_exe and item["path"] == "Fallout76.exe":
                continue
            path = self.target(item["path"])
            permitted = {item["sha256"]: item.get("size")}
            # Localization remains a baseline identity. Only the authenticated
            # v3 profile can additionally recognize its own exact patched bytes.
            # Receipt/current-target checks still enforce ownership separately.
            if item["path"] == LOCALIZATION and LOCALIZATION in self.release.by_path:
                target = self.release.by_path[LOCALIZATION]
                permitted[target["after_sha256"]] = target["after_size"]
            current = hash_file(path) if path.is_file() else None
            demand(
                current in permitted,
                "Unsupported or changed game build: " + item["path"],
            )
            if "size" in item:
                demand(
                    path.stat().st_size == permitted[current],
                    "Game identity size changed",
                )
        for path in sorted(self.interface_overrides):
            demand(
                not self.target(path).exists(),
                "A loose interface override conflicts with KKS: " + path,
            )

    def _receipt(self):
        if not self.receipt_path.exists():
            return None
        return self._validate_receipt(strict_json(bounded_file(self.receipt_path, MAX_MANIFEST)))

    def _validate_receipt(self, value):
        fields(value, "schema manifest root status release files")
        integer(value["schema"], 1, 1)
        demand(type(value["files"]) is dict, "Invalid saved target records")
        for record in value["files"].values():
            fields(record, "before after")
        demand(
            value["release"] == self.release.name,
            "Saved content identity is inconsistent",
        )
        return super()._validate_receipt(value)

    def _read_journal(self):
        j = strict_json(bounded_file(self.journal_path, MAX_MANIFEST))
        fields(j, "schema manifest root operation transaction entries receipt_before")
        integer(j["schema"], 1, 1)
        demand(
            j["manifest"] == self.release.manifest_digest and j["root"] == str(self.root),
            "Recovery belongs to a different installation",
        )
        demand(
            j["operation"] in ("install", "repair", "restore")
            and type(j["transaction"]) is str
            and re.fullmatch("[0-9a-f]{32}", j["transaction"]),
            "Invalid recovery operation",
        )
        receipt = j["receipt_before"]
        if receipt is not None:
            self._validate_receipt(receipt)
        installed = bool(receipt and receipt["status"] == "installed")
        demand(
            j["operation"] == "install" or installed,
            "Recovery has no prior managed installation",
        )
        demand(
            type(j["entries"]) is list and len(j["entries"]) == len(self.release.targets),
            "Invalid recovery entries",
        )
        seen = set()
        for entry in j["entries"]:
            fields(entry, "path before after")
            path = entry["path"]
            demand(
                type(path) is str and path in self.release.by_path and path not in seen,
                "Invalid recovery path",
            )
            seen.add(path)
            target = self.release.by_path[path]
            permitted = {target["vanilla_sha256"]}
            if path in self.strings:
                permitted.add(None)
            if installed:
                permitted.add(target["after_sha256"])
            demand(entry["before"] in permitted, "Unknown pre-transaction file version")
            expected = (
                receipt["files"][path]["before"]
                if j["operation"] == "restore"
                else target["after_sha256"]
            )
            demand(
                entry["after"] == expected,
                "Recovery destination is not authorized by the saved operation",
            )
            if entry["before"] is not None:
                self._backup_path(entry["before"])
        return j

    def _run_locked(self, operation):
        demand(
            not isinstance(self.release, LegacyDescriptor) or operation == "restore",
            "Legacy state is restore-only",
        )
        return super()._run_locked(operation)

    def _after_replace(self, index, entry):
        self.event("file_replaced", {"state": self.state_name, "index": index, "entry": entry})

    def _checkpoint(self, name):
        self.event("engine_" + name, {"state": self.state_name})
