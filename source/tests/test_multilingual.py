"""Closed RU/FR catalogs and recovery across existing EN/DE history."""

from copy import deepcopy
from pathlib import Path
import tempfile, unittest
from unittest.mock import patch
from package_fixture import PackageFixture
from kks_installer.packages import (
    import_package,
    CONFIG,
    LOCALIZATION,
    FONT,
    RUSSIAN_FONT,
)
from kks_installer.platforms import SafetyError
from kks_installer.i18n import translate, LANGUAGE_NAMES, CONTENT_HINTS, DE, FR, RU


class MultilingualTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.fx = PackageFixture(self.base, multilingual=True, loose=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_four_languages_restore_and_independent_history(self):
        m = self.fx.manager()
        releases = {
            lang: m.select(
                self.fx.build(n, language=lang, version="1.1.0", translation_localization=True)[0]
            )
            for lang, n in (("en", 10), ("de", 1), ("ru", 1), ("fr", 1))
        }
        for lang in ("en", "de", "ru", "fr", "en", "de"):
            with self.subTest(language=lang):
                r = releases[lang]
                m.run("install", r)
                self.assertEqual(m.inspect(r)["status"], "installed")
                before = self.fx.snapshot()
                for other, other_r in releases.items():
                    if other == lang:
                        continue
                    for action in ("inspect", "install"):
                        with self.assertRaisesRegex(
                            SafetyError, "Restore vanilla before switching"
                        ):
                            (m.inspect(other_r) if action == "inspect" else m.run(action, other_r))
                        self.assertEqual(self.fx.snapshot(), before)
                m.run("restore")
                self.assertEqual(self.fx.snapshot(), self.fx.original)
        self.assertEqual(m._read_state()["schema"], 4)
        self.assertEqual(m._read_state()["language_sequences"], dict(en=10, de=1, ru=1, fr=1))
        for lang in ("ru", "fr"):
            r = m.select(self.fx.build(2, language=lang, revision=2)[0])
            m.run("install", r)
            m.run("restore")
            with self.assertRaises(SafetyError):
                m.run("install", releases[lang])

    def test_ru_fr_repair_and_restore_without_cached_payload(self):
        for lang in ("ru", "fr"):
            with self.subTest(language=lang):
                m = self.fx.manager()
                r = m.select(self.fx.build(1, language=lang)[0])
                m.run("install", r)
                (self.fx.game / f"Data/strings/seventysix_{lang}.strings").unlink()
                self.assertEqual(m.inspect(r)["status"], "repairable")
                m.run("repair")
                self.assertEqual(m.inspect(r)["status"], "installed")
                for f in r.files:
                    (r.folder / f).unlink()
                m.run("restore")
                self.assertEqual(self.fx.snapshot(), self.fx.original)

    def test_closed_profiles_reject_cross_language_and_capability_changes(self):
        for lang in ("ru", "fr"):
            p, manifest, payloads = self.fx.build(1, language=lang)
            other = "fr" if lang == "ru" else "ru"
            for change in (
                lambda m: m["game"].update(language=other),
                lambda m: m.update(minimum_installer_version="1.3.0"),
                lambda m: m["required_capabilities"].append("arbitrary-writer"),
                lambda m: next(t for t in m["targets"] if t["path"] == CONFIG)["assets"][0].update(
                    name=f"interface/fontconfig_{other}.txt"
                ),
                lambda m: next(t for t in m["targets"] if t["path"] == LOCALIZATION)["assets"][
                    0
                ].update(name=f"interface/translate_{other}.txt"),
                lambda m: next(t for t in m["targets"] if t["kind"] == "loose").update(
                    path=f"Data/strings/seventysix_{other}.strings"
                ),
                lambda m: next(t for t in m["targets"] if t["path"] in (FONT, RUSSIAN_FONT)).update(
                    path=FONT if lang == "ru" else RUSSIAN_FONT
                ),
            ):
                bad = deepcopy(manifest)
                change(bad)
                q = self.fx.write(self.base / "bad.zip", bad, payloads)
                with self.assertRaises(SafetyError):
                    import_package(q, self.base / "cache", self.fx.keys)

    def test_each_new_language_target_interruption_and_state_publish_recovers(self):
        for lang in ("ru", "fr"):
            for stop in range(8):
                with self.subTest(language=lang, stop=stop):
                    fx = PackageFixture(self.base / f"{lang}-{stop}", multilingual=True)
                    m = fx.manager()
                    de = m.select(fx.build(1, language="de")[0])
                    m.run("install", de)
                    m.run("restore")
                    old = deepcopy(m._read_state())
                    self.assertEqual(old["schema"], 3)
                    r = m.select(fx.build(1, language=lang)[0])

                    def fail(name, data):
                        if (
                            (name == "file_replaced" and data["index"] == stop)
                            or (stop == 6 and name == "before_state_publish")
                            or (stop == 7 and name == "after_state_publish")
                        ):
                            raise SystemExit("interrupted")

                    with self.assertRaises(SystemExit):
                        fx.manager(event=fail).run("install", r)
                    m = fx.manager()
                    m.recover()
                    if m.inspect().get("restore_available"):
                        m.run("restore")
                    m.run("install", r)
                    m.run("restore")
                    self.assertEqual(fx.snapshot(), fx.original)
                    self.assertEqual(m._read_state()["language_sequences"]["de"], 1)

    def test_malformed_schema4_histories_are_rejected(self):
        m = self.fx.manager()
        m.run("install", m.select(self.fx.build(1, language="fr")[0]))
        for change in (
            lambda s: s["language_sequences"].update(es=1),
            lambda s: s["language_sequences"].pop("ru"),
            lambda s: s["language_sequences"].update(fr=-1),
            lambda s: s["release_ids"].update({"es/1.1.0/1": "a" * 64}),
        ):
            s = deepcopy(m._read_state())
            change(s)
            with self.assertRaises(SafetyError):
                m._validate_state(s)

    def test_localized_override_blocks_without_game_changes(self):
        for lang in ("ru", "fr"):
            m = self.fx.manager()
            r = m.select(self.fx.build(1, language=lang)[0])
            q = self.fx.game / f"Data/interface/translate_{lang}.txt"
            q.parent.mkdir(exist_ok=True)
            q.write_bytes(b"foreign")
            before = self.fx.snapshot()
            with self.assertRaises(SafetyError):
                m.run("install", r)
            self.assertEqual(self.fx.snapshot(), before)
            q.unlink()

    def test_localized_catalogues_cover_german_scope_and_preserve_path_fragments(self):
        self.assertEqual(set(DE), set(FR))
        self.assertEqual(set(DE), set(RU))
        for lang in ("fr", "ru"):
            for hint in CONTENT_HINTS.values():
                self.assertNotEqual(translate(hint, lang), hint)
            self.assertIn(
                "C:/A/Русский Français.zip",
                translate("Foreign or unsupported file: C:/A/Русский Français.zip", lang),
            )
            self.assertNotIn(
                "files verified",
                translate("KKS 1.1.0 · signature and all 6 files verified", lang),
            )


class MultilingualUiTests(unittest.TestCase):
    def test_languages_keep_actions_and_selection_at_minimum_size(self):
        from kks_installer.ui import App

        with patch.object(App, "start"):
            a = App(game=r"C:\KKS fixture only", language="en")
        try:
            a.root.geometry("900x700")
            a.root.update()
            a.events.put(("selected", ("digest", "KKS 1.1.0 Русский", 6, "ru")))
            a.events.put(
                (
                    "success",
                    dict(
                        status="installed",
                        restore_available=True,
                        repair_available=True,
                        message="KKS is installed and verified.",
                    ),
                )
            )
            a.pump()
            for lang in ("fr", "ru", "de", "en"):
                with patch("kks_installer.ui.save_language"):
                    a.language_value.set(LANGUAGE_NAMES[lang])
                    a.change_language()
                a.root.update()
                self.assertEqual(a.selected, "digest")
                self.assertEqual(a.restore["text"], translate("Restore vanilla", lang))
                self.assertEqual(str(a.restore["state"]), "normal")
                bottom = a.root.winfo_rooty() + a.root.winfo_height()
                for w in (a.primary, a.repair, a.restore, a.log):
                    self.assertTrue(w.winfo_ismapped())
                    self.assertLessEqual(w.winfo_rooty() + w.winfo_height(), bottom)
                self.assertGreaterEqual(a.log.winfo_height(), 30)
        finally:
            a.close()
