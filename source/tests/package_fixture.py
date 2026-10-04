"""Independent synthetic game/package authoring for adversarial tests."""

from copy import deepcopy
from pathlib import Path
import base64
import json
import zipfile
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from kks_installer.ba2 import BA2, hash_file
from kks_installer.engine import digest
from kks_installer.packages import (
    DOMAIN,
    ARCHIVES,
    STRINGS,
    IDENTITIES,
    CONFIG,
    TRANSLATION,
    archive_members,
    LOCALIZATION,
    profile_capabilities,
    profile_strings,
)
from kks_installer._application import (
    PROFILE,
    WRITER,
    APP_VERSION,
    TRANSLATION_PROFILE,
    TRANSLATION_CAPABILITIES,
    LOCALIZATION_PROFILE,
    GERMAN_PROFILE,
)
from kks_installer.manager import Manager
from kks_installer.managed_engine import LegacyDescriptor
from test_installer import archive


class PackageFixture:
    def __init__(self, base, loose=False, german=False):
        self.base = Path(base)
        self.game = self.base / "game"
        (self.game / "Data").mkdir(parents=True)
        self.key = Ed25519PrivateKey.generate()
        self.keys = {"fixture": self.key.public_key().public_bytes_raw().hex()}
        for path in IDENTITIES:
            (self.game / path).write_bytes(("game identity " + path).encode())
        for path, name in ARCHIVES.items():
            archive(
                self.game / path,
                [
                    (name, ("vanilla " + name).encode(), True),
                    ("untouched.dat", b"unrelated payload", False),
                ]
                + (
                    [("interface/fontconfig_de.txt", b"fontlib fonts_en DE", True)]
                    if german and path == CONFIG
                    else []
                )
                + (
                    [
                        (
                            TRANSLATION,
                            b"\xff\xfe" + "$Known\t(Known)\r\n$Keep\tKeep\r\n".encode("utf-16le"),
                            True,
                        )
                    ]
                    if path == CONFIG
                    else []
                ),
            )
        (self.game / "Fallout76.ini").write_bytes(b"INI MUST NOT CHANGE")
        archive(
            self.game / LOCALIZATION,
            [
                (
                    TRANSLATION,
                    b"\xff\xfe" + "$Known\t(Known)\r\n$Keep\tLive English\r\n".encode("utf-16le"),
                    True,
                ),
                ("strings/other-language.strings", b"untouched localization", True),
            ]
            + (
                [
                    (
                        "interface/translate_de.txt",
                        b"\xff\xfe" + "$Known\t(Bekannt)\r\n".encode("utf-16le"),
                        True,
                    )
                ]
                if german
                else []
            ),
        )
        self.loose = {p: ("vanilla " + p).encode() for p in STRINGS}
        if german:
            self.loose.update(
                {p: ("vanilla " + p).encode() for p in profile_strings(GERMAN_PROFILE)}
            )
        if loose:
            (self.game / "Data/strings").mkdir()
            for p, b in self.loose.items():
                (self.game / p).write_bytes(b)
        self.original = self.snapshot()
        self.raw_originals = {
            p: (self.game / p).read_bytes() for p in set(ARCHIVES) | {LOCALIZATION}
        }
        self.a, self.manifest, self.payloads = self.build(1)
        old = {
            "schema": 1,
            "release": "KKS 1.0.0",
            "supported_build": "fixture game",
            "identity": self.manifest["game"]["identity"],
            "targets": self.manifest["targets"],
        }
        self.legacy_raw = json.dumps(old).encode()
        self.legacy = LegacyDescriptor(self.legacy_raw, digest(self.legacy_raw))

    def snapshot(self):
        return {
            p.relative_to(self.game).as_posix(): hash_file(p)
            for p in self.game.rglob("*")
            if p.is_file()
            and not any(x.startswith(".kks-") for x in p.relative_to(self.game).parts)
        }

    def manager(self, event=None):
        return Manager(self.game, keys=self.keys, legacy=self.legacy, event=event)

    def build(
        self,
        sequence,
        *,
        version=None,
        revision=1,
        one_change=False,
        mutate=None,
        include_translation=False,
        translation_localization=False,
        language="en",
    ):
        payloads = {}
        targets = []
        profile = (
            GERMAN_PROFILE
            if language == "de"
            else (
                LOCALIZATION_PROFILE
                if translation_localization
                else TRANSLATION_PROFILE if include_translation else PROFILE
            )
        )
        for idx, (path, names) in enumerate(archive_members(profile).items()):
            for name in names:
                payloads["payload/" + name] = (
                    f"KKS asset {name} v{1 if one_change else sequence}"
                ).encode()
            src = self.base / f"vanilla-{language}-{sequence}-{idx}.ba2"
            src.write_bytes(
                self.raw_originals[path]
                if hasattr(self, "raw_originals")
                else (self.game / path).read_bytes()
            )
            out = self.base / f"output-{language}-{sequence}-{idx}.ba2"
            BA2(src).replace_to(out, {name: payloads["payload/" + name] for name in names})
            assets = []
            for name in names:
                payload = "payload/" + name
                vanilla = BA2(src).extract(name)
                assets.append(
                    {
                        "name": name,
                        "payload": payload,
                        "vanilla_sha256": digest(vanilla),
                        "vanilla_size": len(vanilla),
                        "sha256": digest(payloads[payload]),
                        "size": len(payloads[payload]),
                    }
                )
            targets.append(
                {
                    "path": path,
                    "kind": "archive",
                    "version": 1,
                    "type": "GNRL",
                    "writer": WRITER,
                    "vanilla_sha256": hash_file(src),
                    "vanilla_size": src.stat().st_size,
                    "after_sha256": hash_file(out),
                    "after_size": out.stat().st_size,
                    "assets": assets,
                }
            )
        for idx, path in enumerate(sorted(profile_strings(profile))):
            payload = "payload/" + path[5:]
            n = sequence if not one_change or idx == 0 else 1
            payloads[payload] = (f"compiled {path} v{n}").encode()
            targets.append(
                {
                    "path": path,
                    "kind": "loose",
                    "payload": payload,
                    "vanilla_sha256": digest(self.loose[path]),
                    "vanilla_size": len(self.loose[path]),
                    "after_sha256": digest(payloads[payload]),
                    "after_size": len(payloads[payload]),
                }
            )
        m = {
            "schema": 1,
            "package_type": "kks-content",
            "product": "KKS",
            "channel": "release",
            "content_version": version or f"1.{sequence-1}.0",
            "package_revision": revision,
            "release_sequence": sequence,
            "created_utc": "2026-10-01T12:00:00Z",
            "installer_api": 1,
            "minimum_installer_version": APP_VERSION,
            "required_capabilities": profile_capabilities(profile),
            "profile": profile,
            "game": {
                "id": "fallout76",
                "platform": "steam",
                "app_id": 1151340,
                "language": language,
                "build_label": "fixture game",
                "baseline_id": "fixture-baseline" + ("-de" if language == "de" else ""),
                "identity": [
                    {
                        "path": p,
                        "sha256": hash_file(self.game / p),
                        "size": (self.game / p).stat().st_size,
                    }
                    for p in sorted(IDENTITIES)
                ],
            },
            "files": [
                {"path": p, "sha256": digest(b), "size": len(b)}
                for p, b in sorted(payloads.items())
            ],
            "targets": targets,
            "qa": {"status": "candidate", "report_id": "synthetic test fixture"},
        }
        if translation_localization or language == "de":
            original = self.raw_originals[LOCALIZATION]
            next(i for i in m["game"]["identity"] if i["path"] == LOCALIZATION).update(
                sha256=digest(original), size=len(original)
            )
        if mutate:
            mutate(m)
        path = self.base / f"content-{'de-' if language == 'de' else ''}{sequence}-{revision}.zip"
        self.write(path, m, payloads)
        return path, m, payloads

    def write(
        self, path, manifest, payloads, *, raw=None, key=None, extra=None, signature_mutator=None
    ):
        raw = (
            json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
            if raw is None
            else raw
        )
        sig = {
            "schema": 1,
            "algorithm": "Ed25519",
            "key_id": "fixture",
            "signature": base64.b64encode((key or self.key).sign(DOMAIN + raw)).decode(),
        }
        if signature_mutator:
            signature_mutator(sig)
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr("manifest.json", raw)
            z.writestr("manifest.sig.json", json.dumps(sig).encode())
            for p, b in payloads.items():
                z.writestr(p, b)
            if extra:
                for p, b in extra:
                    z.writestr(p, b)
        return path
