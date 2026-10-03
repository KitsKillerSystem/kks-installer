from copy import deepcopy
from pathlib import Path
import tempfile, unittest
from kks_installer.packages import (
    import_package,
    CONFIG,
    TRANSLATION,
    TRANSLATION_PAYLOAD,
    MAX_TRANSLATION,
)
from kks_installer._application import PROFILE, WRITER
from kks_installer.manager import fingerprint
from kks_installer.ba2 import BA2
from kks_installer.platforms import SafetyError
from package_fixture import PackageFixture


class TranslationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.fx = PackageFixture(self.base)
        self.path, self.manifest, self.payloads = self.fx.build(2, include_translation=True)

    def tearDown(self):
        self.temp.cleanup()

    def test_old_to_translation_update_repair_restore(self):
        manager = self.fx.manager()
        old = manager.select(self.fx.a)
        manager.run("install", old)
        new = manager.select(self.path)
        self.assertEqual(fingerprint(old), fingerprint(new))
        self.assertEqual(manager.inspect(new)["status"], "update_available")
        manager.run("install", new)
        arc = BA2(self.fx.game / CONFIG)
        self.assertEqual(arc.extract(TRANSLATION), self.payloads[TRANSLATION_PAYLOAD])
        self.assertEqual(arc.extract("untouched.dat"), b"unrelated payload")
        manager.run("repair")
        manager.run("restore")
        self.assertEqual(self.fx.snapshot(), self.fx.original)

    def test_fresh_translation_install_restore(self):
        manager = self.fx.manager()
        r = manager.select(self.path)
        manager.run("install", r)
        manager.run("restore")
        self.assertEqual(self.fx.snapshot(), self.fx.original)
        self.assertEqual(len(r.files), 6)

    def test_authentication_and_catalog_rejections(self):
        cases = [
            lambda m: m.update(profile=PROFILE),
            lambda m: m.update(required_capabilities=[WRITER]),
            lambda m: m.update(minimum_installer_version="1.1.0"),
            lambda m: next(t for t in m["targets"] if t["path"] == CONFIG)["assets"].reverse(),
            lambda m: next(t for t in m["targets"] if t["path"] == CONFIG)["assets"][1].update(
                name="interface/translate_fr.txt"
            ),
            lambda m: next(t for t in m["targets"] if t["path"] == CONFIG)["assets"][1].update(
                name="../translate_en.txt"
            ),
            lambda m: next(t for t in m["targets"] if t["path"] == CONFIG)["assets"][1].update(
                payload="payload/interface/fontconfig_en.txt"
            ),
            lambda m: next(f for f in m["files"] if f["path"] == TRANSLATION_PAYLOAD).update(
                size=MAX_TRANSLATION + 1
            ),
        ]
        for mutate in cases:
            with self.subTest(case=cases.index(mutate)):
                m = deepcopy(self.manifest)
                mutate(m)
                p = self.fx.write(self.base / "bad.zip", m, self.payloads)
                with self.assertRaises(SafetyError):
                    import_package(p, self.base / "bad-cache", self.fx.keys)
        self.assertEqual(self.fx.snapshot(), self.fx.original)

    def test_unlisted_translation_cannot_ride_in_an_old_package(self):
        p = self.fx.write(
            self.base / "bad.zip",
            self.fx.manifest,
            self.fx.payloads,
            extra=[(TRANSLATION_PAYLOAD, b"unlisted")],
        )
        with self.assertRaises(SafetyError):
            import_package(p, self.base / "bad-cache", self.fx.keys)

    def test_tampered_or_missing_translation_rejected(self):
        for missing in [False, True]:
            payloads = deepcopy(self.payloads)
            if missing:
                del payloads[TRANSLATION_PAYLOAD]
            else:
                payloads[TRANSLATION_PAYLOAD] = b"tampered"
            p = self.fx.write(self.base / "bad.zip", self.manifest, payloads)
            with self.assertRaises(SafetyError):
                import_package(p, self.base / "bad-cache", self.fx.keys)

    def test_wrong_original_translation_is_rejected_before_game_writes(self):
        m = deepcopy(self.manifest)
        next(t for t in m["targets"] if t["path"] == CONFIG)["assets"][1]["vanilla_sha256"] = (
            "a" * 64
        )
        p = self.fx.write(self.base / "bad.zip", m, self.payloads)
        manager = self.fx.manager()
        r = manager.select(p)
        with self.assertRaises(SafetyError):
            manager.run("install", r)
        self.assertEqual(self.fx.snapshot(), self.fx.original)

    def test_loose_translation_conflict_blocks(self):
        path = self.fx.game / "Data/interface/translate_en.txt"
        path.parent.mkdir()
        path.write_bytes(b"other mod")
        manager = self.fx.manager()
        r = manager.select(self.path)
        with self.assertRaises(SafetyError):
            manager.run("install", r)
        self.assertEqual(path.read_bytes(), b"other mod")

    def test_interrupted_translation_update_recovers_old_package(self):
        manager = self.fx.manager()
        old = manager.select(self.fx.a)
        manager.run("install", old)
        installed = self.fx.snapshot()
        new = manager.select(self.path)

        def fail(name, data):
            if name == "file_replaced" and data["index"] == 1:
                raise RuntimeError("simulated interruption")

        with self.assertRaises(RuntimeError):
            self.fx.manager(event=fail).run("install", new)
        self.fx.manager().recover()
        self.assertEqual(self.fx.snapshot(), installed)
        self.fx.manager().run("restore")
        self.assertEqual(self.fx.snapshot(), self.fx.original)


if __name__ == "__main__":
    unittest.main()
