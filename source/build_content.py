"""Publisher-only package authoring. This module is not imported into the EXE.

Read clean, disposable game files; emit a complete signed ZIP. Private keys live
outside the checkout and are protected by Windows DPAPI for the current user.
"""

from pathlib import Path
import argparse
import base64
import ctypes
from ctypes import wintypes
import datetime
import json
import os
import tempfile
import zipfile

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from kks_installer._application import (
    APP_VERSION,
    PROFILE,
    WRITER,
    TRANSLATION_PROFILE,
    TRANSLATION_CAPABILITIES,
    LOCALIZATION_PROFILE,
    GERMAN_PROFILE,
    LOCALIZED_PROFILES,
    CONTENT_LANGUAGES,
)
from kks_installer.ba2 import BA2, hash_file
from kks_installer.engine import demand, digest
from kks_installer.packages import (
    DOMAIN,
    ARCHIVES,
    STRINGS,
    IDENTITIES,
    PAYLOADS,
    validate_manifest,
    import_package,
    strict_json,
    archive_members,
    profile_payloads,
    profile_capabilities,
    profile_strings,
    profile_language,
)


def protect(data, decrypt=False):
    demand(
        os.name == "nt",
        "Publisher key protection requires Windows; use the same signing account and machine",
    )

    class Blob(ctypes.Structure):
        _fields_ = [
            ("cbData", wintypes.DWORD),
            ("pbData", ctypes.POINTER(ctypes.c_ubyte)),
        ]

    buf = ctypes.create_string_buffer(data)
    src = Blob(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_ubyte)))
    dst = Blob()
    dll = ctypes.WinDLL("crypt32", use_last_error=True)
    function = dll.CryptUnprotectData if decrypt else dll.CryptProtectData
    function.argtypes = [
        ctypes.POINTER(Blob),
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(Blob),
    ]
    function.restype = wintypes.BOOL
    demand(
        function(ctypes.byref(src), None, None, None, None, 1, ctypes.byref(dst)),
        "Windows could not protect/unlock the publisher key",
    )
    try:
        return ctypes.string_at(dst.pbData, dst.cbData)
    finally:
        ctypes.memset(dst.pbData, 0, dst.cbData)
        k = ctypes.WinDLL("kernel32")
        k.LocalFree.argtypes = [ctypes.c_void_p]
        k.LocalFree(dst.pbData)


def create_key(path, key_id):
    path = Path(path)
    demand(not path.exists(), "A signing key already exists here; it will not be replaced")
    demand(
        not path.resolve().is_relative_to(Path(__file__).resolve().parent.parent),
        "Private keys must be outside the repository",
    )
    key = Ed25519PrivateKey.generate()
    public = key.public_key().public_bytes_raw().hex()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "schema": 1,
        "key_id": key_id,
        "public_key": public,
        "dpapi": base64.b64encode(protect(key.private_bytes_raw())).decode(),
    }
    with path.open("x", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    return {"key_id": key_id, "public_key": public, "protected_key_path": str(path)}


def load_key(path):
    data = strict_json(Path(path).read_bytes(), 16384)
    key = Ed25519PrivateKey.from_private_bytes(
        protect(base64.b64decode(data["dpapi"], validate=True), True)
    )
    demand(
        key.public_key().public_bytes_raw().hex() == data["public_key"],
        "Publisher key metadata is inconsistent",
    )
    return key, data["key_id"]


def export_key(path, destination):
    """Interactive publisher recovery export, never print or store the passphrase."""
    import getpass
    from cryptography.hazmat.primitives import serialization

    key, _ = load_key(path)
    first = getpass.getpass("Recovery-key passphrase: ")
    demand(
        len(first) >= 16 and first == getpass.getpass("Repeat passphrase: "),
        "Passphrases must match and contain at least 16 characters",
    )
    raw = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.BestAvailableEncryption(first.encode()),
    )
    with Path(destination).open("xb") as f:
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())
    return {"encrypted_recovery_key": str(destination)}


def build(
    game,
    payload,
    output,
    key_path,
    *,
    content_version,
    revision,
    sequence,
    baseline_id,
    build_label,
    report_id,
    expected_legacy=None,
    include_translation=False,
    translation_localization=False,
    language="en",
    equipment_naming=False,
    perk_cards=False,
):
    game = Path(game)
    payload = Path(payload)
    output = Path(output)
    demand(not output.exists(), "Refusing to replace an existing package")
    files = []
    targets = []
    demand(
        not (include_translation and translation_localization),
        "Choose one translation profile",
    )
    demand(language in CONTENT_LANGUAGES, "Unsupported content language")
    demand(not perk_cards or equipment_naming,
           "Optional perk cards require the equipment-capable content profile")
    demand(
        language == "en" or (translation_localization and not include_translation),
        "Localized content requires the Localization profile",
    )
    profile = (
        LOCALIZED_PROFILES[language]
        if language != "en"
        else (
            LOCALIZATION_PROFILE
            if translation_localization
            else TRANSLATION_PROFILE if include_translation else PROFILE
        )
    )
    catalog = archive_members(profile)
    for p in sorted(profile_payloads(profile)):
        src = payload / p.removeprefix("payload/")
        files.append({"path": p, "sha256": hash_file(src), "size": src.stat().st_size})
    byfile = {f["path"]: f for f in files}
    identity = [
        {"path": p, "sha256": hash_file(game / p), "size": (game / p).stat().st_size}
        for p in sorted(IDENTITIES)
    ]
    with tempfile.TemporaryDirectory(prefix="kks-content-certify-") as temporary:
        for idx, (path, names) in enumerate(catalog.items()):
            src = game / path
            before = hash_file(src)
            archive = BA2(src)
            out = Path(temporary) / f"{idx}.ba2"
            archive.replace_to(out, {name: (payload / name).read_bytes() for name in names})
            assets = []
            for name in names:
                original = archive.extract(name)
                f = byfile["payload/" + name]
                assets.append(
                    {
                        "name": name,
                        "payload": f["path"],
                        "vanilla_sha256": digest(original),
                        "vanilla_size": len(original),
                        "sha256": f["sha256"],
                        "size": f["size"],
                    }
                )
            demand(hash_file(src) == before, "Game archive changed during certification")
            targets.append(
                {
                    "path": path,
                    "kind": "archive",
                    "version": 1,
                    "type": "GNRL",
                    "writer": WRITER,
                    "vanilla_sha256": before,
                    "vanilla_size": src.stat().st_size,
                    "after_sha256": hash_file(out),
                    "after_size": out.stat().st_size,
                    "assets": assets,
                }
            )
        localization = BA2(game / "Data/SeventySix - Localization.ba2")
        for p in sorted(profile_strings(profile)):
            raw = localization.extract(p.removeprefix("Data/"))
            f = byfile["payload/" + p[5:]]
            targets.append(
                {
                    "path": p,
                    "kind": "loose",
                    "payload": f["path"],
                    "vanilla_sha256": digest(raw),
                    "vanilla_size": len(raw),
                    "after_sha256": f["sha256"],
                    "after_size": f["size"],
                }
            )
        for item in identity:
            demand(
                hash_file(game / item["path"]) == item["sha256"],
                "Game identity changed during certification",
            )
        m = {
            "schema": 1,
            "package_type": "kks-content",
            "product": "KKS",
            "channel": "release",
            "content_version": content_version,
            "package_revision": revision,
            "release_sequence": sequence,
            "created_utc": datetime.datetime.now(datetime.timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            "installer_api": 1,
            "minimum_installer_version": APP_VERSION,
            "required_capabilities": profile_capabilities(profile),
            "profile": profile,
            "game": {
                "id": "fallout76",
                "platform": "steam",
                "app_id": 1151340,
                "language": profile_language(profile),
                "build_label": build_label,
                "baseline_id": baseline_id,
                "identity": identity,
            },
            "files": files,
            "targets": targets,
            "qa": {"status": "candidate", "report_id": report_id},
        }
        if equipment_naming:
            from equipment_catalog import equipment_categories
            from kks_installer.equipment import CAPABILITY, reset_equipment

            demand(language == "en" and translation_localization,
                   "The equipment naming preview requires English Localization content")
            categories = equipment_categories(game / "Data/SeventySix.esm")
            member = "strings/seventysix_en.strings"
            derived = reset_equipment((payload / member).read_bytes(), localization.extract(member), categories)
            m["schema"] = 2
            m["required_capabilities"] = m["required_capabilities"] + [CAPABILITY]
            m["equipment_naming"] = dict(algorithm=CAPABILITY, categories=categories,
                                         sha256=digest(derived), size=len(derived))
            for item in identity:
                demand(hash_file(game / item["path"]) == item["sha256"],
                       "Game identity changed during equipment certification")
        if perk_cards:
            from equipment_catalog import perk_categories
            from kks_installer.perks import CAPABILITY, reset_perks

            categories = perk_categories(game / "Data/SeventySix.esm")
            member = "strings/seventysix_en.dlstrings"
            derived = reset_perks((payload / member).read_bytes(), localization.extract(member), categories)
            m["schema"] = 3
            m["required_capabilities"] = m["required_capabilities"] + [CAPABILITY]
            m["perk_cards"] = dict(algorithm=CAPABILITY, categories=categories,
                                    sha256=digest(derived), size=len(derived))
            for item in identity:
                demand(hash_file(game / item["path"]) == item["sha256"],
                       "Game identity changed during perk certification")
        validate_manifest(m)
        if expected_legacy:
            old = json.loads(Path(expected_legacy).read_bytes())
            demand(
                {x["path"]: x["sha256"] for x in identity}
                == {x["path"]: x["sha256"] for x in old["identity"]},
                "Game differs from the frozen 1.0 baseline",
            )
            for t in targets:
                previous = next(x for x in old["targets"] if x["path"] == t["path"])
                for field in ("vanilla_sha256", "after_sha256"):
                    demand(
                        t[field] == previous[field],
                        "Output differs from frozen 1.0: " + t["path"],
                    )
                for a, b in zip(t.get("assets", []), previous.get("assets", [])):
                    demand(
                        a["sha256"] == b["sha256"] and a["vanilla_sha256"] == b["vanilla_sha256"],
                        "Embedded asset differs from 1.0",
                    )
        key, key_id = load_key(key_path)
        raw = (json.dumps(m, sort_keys=True, indent=2) + "\n").encode()
        envelope = {
            "schema": 1,
            "algorithm": "Ed25519",
            "key_id": key_id,
            "signature": base64.b64encode(key.sign(DOMAIN + raw)).decode(),
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            z.writestr("manifest.json", raw)
            z.writestr("manifest.sig.json", json.dumps(envelope, sort_keys=True).encode())
            for f in files:
                z.write(payload / f["path"].removeprefix("payload/"), f["path"])
        verified = import_package(
            output,
            Path(temporary) / "verification",
            {key_id: key.public_key().public_bytes_raw().hex()},
        )
        return {
            "package": str(output),
            "sha256": hash_file(output),
            "size": output.stat().st_size,
            "manifest_sha256": verified.manifest_digest,
            "content_version": content_version,
            "payload_files": files,
            "targets_match_frozen_1_0": bool(expected_legacy),
        }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    k = sub.add_parser("create-key")
    k.add_argument("--key", required=True)
    k.add_argument("--key-id", required=True)
    e = sub.add_parser("export-recovery-key")
    e.add_argument("--key", required=True)
    e.add_argument("--output", required=True)
    b = sub.add_parser("build")
    for name in (
        "game",
        "payload",
        "output",
        "key",
        "content-version",
        "baseline-id",
        "build-label",
        "report-id",
    ):
        b.add_argument("--" + name, required=True)
    b.add_argument("--revision", type=int, default=1)
    b.add_argument("--sequence", type=int, required=True)
    b.add_argument("--expected-legacy")
    b.add_argument("--include-translation", action="store_true")
    b.add_argument("--translation-localization", action="store_true")
    b.add_argument("--language", choices=CONTENT_LANGUAGES, default="en")
    b.add_argument("--equipment-naming", action="store_true")
    b.add_argument("--perk-cards", action="store_true")
    a = p.parse_args()
    if a.command == "create-key":
        result = create_key(a.key, a.key_id)
    elif a.command == "export-recovery-key":
        result = export_key(a.key, a.output)
    else:
        result = build(
            a.game,
            a.payload,
            a.output,
            a.key,
            content_version=a.content_version,
            revision=a.revision,
            sequence=a.sequence,
            baseline_id=a.baseline_id,
            build_label=a.build_label,
            report_id=a.report_id,
            expected_legacy=a.expected_legacy,
            include_translation=a.include_translation,
            translation_localization=a.translation_localization,
            language=a.language,
            equipment_naming=a.equipment_naming,
            perk_cards=a.perk_cards,
        )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
