"""Cross-language ownership, independent sequence histories, and closed DE targets."""

from copy import deepcopy
from pathlib import Path
import tempfile, unittest
from package_fixture import PackageFixture
from kks_installer.ba2 import BA2
from kks_installer.packages import import_package, LOCALIZATION, CONFIG, profile_strings
from kks_installer._application import GERMAN_PROFILE
from kks_installer.platforms import SafetyError


class GermanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.fx = PackageFixture(self.base, german=True)
        self.p, self.manifest, self.payloads = self.fx.build(1, version="1.1.0", language="de")

    def tearDown(self):
        self.tmp.cleanup()

    def test_fresh_german_install_repair_restore_preserves_other_languages(self):
        m = self.fx.manager()
        r = m.select(self.p)
        self.assertEqual(m.inspect(r)["status"], "ready")
        before = BA2(self.fx.game / LOCALIZATION).extract("interface/translate_en.txt")
        before_config = BA2(self.fx.game / CONFIG).extract("interface/fontconfig_en.txt")
        m.run("install", r)
        self.assertEqual(
            BA2(self.fx.game / LOCALIZATION).extract("interface/translate_en.txt"), before
        )
        self.assertEqual(
            BA2(self.fx.game / CONFIG).extract("interface/fontconfig_en.txt"), before_config
        )
        self.assertFalse(
            any(
                (self.fx.game / f"Data/strings/seventysix_en.{x}").exists()
                for x in ("strings", "dlstrings", "ilstrings")
            )
        )
        m.run("repair")
        m.run("restore")
        self.assertEqual(self.fx.snapshot(), self.fx.original)

    def test_english_german_english_uses_independent_sequences(self):
        en, _, _ = self.fx.build(10, version="1.1.0", revision=8, translation_localization=True)
        m = self.fx.manager()
        er = m.select(en)
        dr = m.select(self.p)
        m.run("install", er)
        before = self.fx.snapshot()
        for op in ("inspect", "install"):
            with self.assertRaisesRegex(SafetyError, "Restore vanilla before switching"):
                m.inspect(dr) if op == "inspect" else m.run("install", dr)
            self.assertEqual(self.fx.snapshot(), before)
        m.run("restore")
        m.run("install", dr)
        self.assertEqual(m._read_state()["language_sequences"], {"en": 10, "de": 1})
        m.run("restore")
        m.run("install", er)
        m.run("restore")
        self.assertEqual(self.fx.snapshot(), self.fx.original)
        newer, _, _ = self.fx.build(2, version="1.1.0", revision=2, language="de")
        m.run("install", m.select(newer))
        m.run("restore")
        with self.assertRaises(SafetyError):
            m.run("install", dr)
        m.run("install", er)
        m.run("restore")

    def test_restore_german_without_cached_payloads(self):
        m = self.fx.manager()
        r = m.select(self.p)
        m.run("install", r)
        for f in r.files:
            (r.folder / f).unlink()
        m.run("restore")
        self.assertEqual(self.fx.snapshot(), self.fx.original)

    def test_german_profile_rejects_language_and_member_substitutions(self):
        for change in (
            lambda m: m["game"].update(language="en"),
            lambda m: m.update(minimum_installer_version="1.2.1"),
            lambda m: next(t for t in m["targets"] if t["path"] == CONFIG)["assets"][0].update(
                name="interface/fontconfig_en.txt"
            ),
            lambda m: next(t for t in m["targets"] if t["kind"] == "loose").update(
                path="Data/strings/seventysix_ru.strings"
            ),
        ):
            bad = deepcopy(self.manifest)
            change(bad)
            p = self.fx.write(self.base / "bad.zip", bad, self.payloads)
            with self.assertRaises(SafetyError):
                import_package(p, self.base / "cache", self.fx.keys)

    def test_loose_german_override_blocks_without_writes(self):
        q = self.fx.game / "Data/interface/translate_de.txt"
        q.parent.mkdir()
        q.write_bytes(b"foreign")
        m = self.fx.manager()
        r = m.select(self.p)
        before = self.fx.snapshot()
        with self.assertRaises(SafetyError):
            m.run("install", r)
        self.assertEqual(self.fx.snapshot(), before)

    def test_each_german_target_interruption_recovers_and_restores(self):
        for index in range(6):
            fx = PackageFixture(self.base / f"crash-{index}", german=True)
            p, _, _ = fx.build(1, language="de")
            m = fx.manager()
            r = m.select(p)

            def fail(name, data):
                if name == "file_replaced" and data["index"] == index:
                    raise SystemExit("interrupted")

            with self.assertRaises(SystemExit):
                fx.manager(event=fail).run("install", r)
            m = fx.manager()
            m.recover()
            m.run("install", r)
            m.run("restore")
            self.assertEqual(fx.snapshot(), fx.original)

    def test_malformed_language_history_is_rejected(self):
        m = self.fx.manager()
        m.run("install", m.select(self.p))
        s = m._read_state()
        s["language_sequences"]["ru"] = 1
        with self.assertRaises(SafetyError):
            m._validate_state(s)
