from copy import deepcopy
import json, struct, tempfile, unittest, zipfile
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from kks_installer.packages import import_package, SignedRelease, MAX_ASSET
from kks_installer.platforms import SafetyError
from package_fixture import PackageFixture


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.fx = PackageFixture(self.base)
        self.bad = self.base / "bad.zip"

    def tearDown(self):
        self.temp.cleanup()

    def reject(self, path=None):
        before = self.fx.snapshot()
        with self.assertRaises((SafetyError, ValueError, TypeError)):
            import_package(path or self.bad, self.base / "cache", self.fx.keys)
        self.assertEqual(before, self.fx.snapshot())
        if (self.base / "cache").exists():
            self.assertTrue(
                all(p.name.startswith("import-") for p in (self.base / "cache").iterdir())
            )

    def test_valid_complete_package(self):
        r = import_package(self.fx.a, self.base / "cache", self.fx.keys)
        r.verify_payloads()
        self.assertEqual(len(r.files), 5)

    def test_unsupported_or_extra_manifest_fields(self):
        cases = [
            lambda m: m.update(extra="value"),
            lambda m: m.update(product="OTHER"),
            lambda m: m.update(channel="beta"),
            lambda m: m.update(schema=True),
            lambda m: m.update(schema=2),
            lambda m: m.update(installer_api=999),
            lambda m: m.update(release_sequence=0),
            lambda m: m.update(release_sequence=True),
            lambda m: m.update(release_sequence=1.0),
            lambda m: m.update(minimum_installer_version="99.0.0"),
            lambda m: m.update(required_capabilities=["exec"]),
            lambda m: m["game"].update(platform="gamepass"),
            lambda m: m["game"].update(language="ru"),
            lambda m: m["game"].update(app_id=True),
            lambda m: m["game"].update(identity=[]),
            lambda m: m["game"]["identity"][0].update(path="other.exe"),
            lambda m: m["files"][0].update(size=MAX_ASSET + 1),
            lambda m: m["files"][0].update(sha256="A" * 64),
            lambda m: m["targets"][0].update(path="Fallout76.exe"),
            lambda m: m["targets"][0]["assets"][0].update(name="other.swf"),
            lambda m: m["targets"][0].update(writer="shell"),
            lambda m: m["targets"][0].update(version=8),
            lambda m: m["targets"][0].update(type="DX10"),
            lambda m: m["files"].append(m["files"][0]),
            lambda m: m["qa"].update(status="trust-me"),
        ]
        for i, mutate in enumerate(cases):
            with self.subTest(case=i):
                m = deepcopy(self.fx.manifest)
                mutate(m)
                self.fx.write(self.bad, m, self.fx.payloads)
                self.reject()

    def test_duplicate_json_keys(self):
        raw = json.dumps(self.fx.manifest).encode()
        raw = raw[:-1] + b',"schema":1}'
        self.fx.write(self.bad, self.fx.manifest, self.fx.payloads, raw=raw)
        self.reject()

    def test_json_bom_nonfinite_and_depth(self):
        for raw in (
            b"\xef\xbb\xbf" + json.dumps(self.fx.manifest).encode(),
            b'{"schema":NaN}',
            b"[" * 1000 + b"0" + b"]" * 1000,
        ):
            self.fx.write(self.bad, self.fx.manifest, self.fx.payloads, raw=raw)
            self.reject()

    def test_unknown_key_and_bad_signature(self):
        for mutate in (
            lambda s: s.update(key_id="outsider"),
            lambda s: s.update(algorithm="none"),
            lambda s: s.update(signature="not base64"),
            lambda s: s.update(signature="AA=="),
            lambda s: s.update(schema=True),
        ):
            self.fx.write(self.bad, self.fx.manifest, self.fx.payloads, signature_mutator=mutate)
            self.reject()
        self.fx.write(
            self.bad, self.fx.manifest, self.fx.payloads, key=Ed25519PrivateKey.generate()
        )
        self.reject()

    def test_tampered_payload_and_missing_member(self):
        p = deepcopy(self.fx.payloads)
        name = next(iter(p))
        p[name] = b"tampered"
        self.fx.write(self.bad, self.fx.manifest, p)
        self.reject()
        del p[name]
        self.fx.write(self.bad, self.fx.manifest, p)
        self.reject()

    def test_extra_code_paths_aliases_and_duplicate_entries(self):
        for name in (
            "evil.exe",
            "payload/evil.dll",
            "../outside",
            "/absolute",
            "C:/outside",
            "payload\\font.swf",
            "payload/interface/fonts_en.swf:ads",
            "PAYLOAD/interface/fonts_en.swf",
            "payload/interface/fonts_en.swf.",
            "payload/interface/NUL",
            "nested.zip",
            "manifest.json",
        ):
            with self.subTest(name=name):
                self.fx.write(self.bad, self.fx.manifest, self.fx.payloads, extra=[(name, b"evil")])
                self.reject()

    def test_symlink_member(self):
        info = zipfile.ZipInfo("payload/interface/fonts_en.swf")
        info.create_system = 3
        info.external_attr = 0o120777 << 16
        with zipfile.ZipFile(self.fx.a) as z:
            entries = [(x, z.read(x.filename)) for x in z.infolist()]
        with zipfile.ZipFile(self.bad, "w") as z:
            for old, data in entries:
                z.writestr(info if old.filename == info.filename else old, data)
        self.reject()

    def test_truncated_prefixed_trailing_and_comment_containers(self):
        raw = self.fx.a.read_bytes()
        for content in (raw[:-1], b"MZ" + raw, raw + b"extra", raw[:100]):
            self.bad.write_bytes(content)
            self.reject()
        self.bad.write_bytes(raw)
        with zipfile.ZipFile(self.bad, "a") as z:
            z.comment = b"unsupported comment"
        self.reject()

    def test_local_header_size_and_name_mismatch(self):
        original = self.fx.a.read_bytes()
        data = bytearray(original)
        struct.pack_into("<I", data, 18, 1)
        self.bad.write_bytes(data)
        self.reject()
        data = bytearray(original)
        data[30] = ord("X")
        self.bad.write_bytes(data)
        self.reject()

    def test_central_directory_resource_limits(self):
        data = bytearray(self.fx.a.read_bytes())
        struct.pack_into("<I", data, len(data) - 10, 1000000)
        self.bad.write_bytes(data)
        self.reject()

    def test_cache_manifest_tampering_is_rejected(self):
        release = import_package(self.fx.a, self.base / "cache", self.fx.keys)
        (release.folder / "manifest.json").write_bytes(b"{}")
        with self.assertRaises(SafetyError):
            SignedRelease.load(release.folder, self.fx.keys)


if __name__ == "__main__":
    unittest.main()
