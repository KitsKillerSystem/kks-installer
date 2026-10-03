import json, tempfile, unittest
from pathlib import Path
from kks_installer.ba2 import BA2, hash_file
from kks_installer.engine import Release, digest, STATE, SafetyError
from kks_installer.profile import Installer, FONT_ARCHIVE, CONFIG_ARCHIVE, STRINGS, PRIOR_STATES
from test_installer import archive


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.game = self.base / "game"
        self.release = self.base / "release"
        (self.game / "Data").mkdir(parents=True)
        self.release.mkdir()
        arc = self.game / FONT_ARCHIVE
        archive(
            arc,
            [
                ("interface/fonts_en.swf", b"vanilla font", False),
                ("unrelated.bin", b"unchanged", True),
            ],
        )
        (self.release / "font.swf").write_bytes(b"RC2.1 font")
        BA2(arc).replace_to(self.base / "patched.ba2", {"interface/fonts_en.swf": b"RC2.1 font"})
        identities = {
            "Fallout76.exe": b"known executable",
            "Data/SeventySix.esm": b"ESM identity",
            "Data/SeventySix - Localization.ba2": b"localization archive identity",
        }
        for name, data in identities.items():
            (self.game / name).write_bytes(data)
        (self.game / "Fallout76.ini").write_bytes(b"INI sentinel")
        config = self.game / CONFIG_ARCHIVE
        archive(
            config,
            [
                ("interface/fontconfig_en.txt", b"original config", False),
                ("other.bin", b"untouched", True),
            ],
        )
        (self.release / "config.txt").write_bytes(b"UTF8 config fixture")
        BA2(config).replace_to(
            self.base / "config.ba2", {"interface/fontconfig_en.txt": b"UTF8 config fixture"}
        )
        targets = [
            {
                "path": FONT_ARCHIVE,
                "kind": "archive",
                "version": 1,
                "type": "GNRL",
                "vanilla_sha256": hash_file(arc),
                "after_sha256": hash_file(self.base / "patched.ba2"),
                "assets": [
                    {
                        "name": "interface/fonts_en.swf",
                        "payload": "font.swf",
                        "vanilla_sha256": digest(b"vanilla font"),
                        "sha256": hash_file(self.release / "font.swf"),
                    }
                ],
            }
        ]
        targets.append(
            {
                "path": CONFIG_ARCHIVE,
                "kind": "archive",
                "version": 1,
                "type": "GNRL",
                "vanilla_sha256": hash_file(config),
                "after_sha256": hash_file(self.base / "config.ba2"),
                "assets": [
                    {
                        "name": "interface/fontconfig_en.txt",
                        "payload": "config.txt",
                        "vanilla_sha256": digest(b"original config"),
                        "sha256": hash_file(self.release / "config.txt"),
                    }
                ],
            }
        )
        for path in sorted(STRINGS):
            payload = Path(path).name
            (self.release / payload).write_bytes(("compiled " + payload).encode())
            targets.append(
                {
                    "path": path,
                    "kind": "loose",
                    "payload": payload,
                    "vanilla_sha256": digest(("vanilla " + payload).encode()),
                    "after_sha256": hash_file(self.release / payload),
                }
            )
        self.manifest = {
            "schema": 1,
            "release": "0.1.2 fixture",
            "supported_build": "fixture",
            "identity": [{"path": p, "sha256": hash_file(self.game / p)} for p in identities],
            "targets": targets,
        }
        self.engine = self.make_engine()
        self.original = self.snapshot()

    def tearDown(self):
        self.temp.cleanup()

    def make_engine(self):
        p = self.release / "manifest.json"
        p.write_text(json.dumps(self.manifest), "utf8")
        return Installer(self.game, Release(self.release, hash_file(p)))

    def snapshot(self):
        return {
            p.relative_to(self.game).as_posix(): hash_file(p)
            for p in self.game.rglob("*")
            if p.is_file() and STATE not in p.parts
        }

    def test_install_changes_only_two_archives_and_three_tables(self):
        self.engine.run("install")
        after = self.snapshot()
        changed = {
            p for p in set(after) | set(self.original) if after.get(p) != self.original.get(p)
        }
        self.assertEqual(changed, {FONT_ARCHIVE, CONFIG_ARCHIVE} | STRINGS)
        self.assertFalse((self.game / "Data/interface").exists())
        self.engine.run("restore")
        self.assertEqual(self.snapshot(), self.original)

    def test_check_is_readonly(self):
        self.assertFalse(self.engine.inspect()["qa_candidate"])
        self.assertFalse((self.game / STATE).exists())

    def test_modified_fontconfig_blocks_all_game_writes(self):
        (self.game / CONFIG_ARCHIVE).write_bytes(b"modified fontconfig")
        before = self.snapshot()
        with self.assertRaises(SafetyError):
            self.engine.run("install")
        self.assertEqual(before, self.snapshot())

    def test_configuration_target_is_required(self):
        self.manifest["targets"] = [
            i for i in self.manifest["targets"] if i["path"] != CONFIG_ARCHIVE
        ]
        with self.assertRaises(SafetyError):
            self.make_engine()

    def test_extra_fontconfig_write_target_is_forbidden(self):
        t = dict(self.manifest["targets"][1])
        t["path"] = "Data/interface/fontconfig_en.txt"
        self.manifest["targets"].append(t)
        with self.assertRaises(SafetyError):
            self.make_engine()

    def test_other_embedded_font_asset_is_forbidden(self):
        self.manifest["targets"][0]["assets"][0]["name"] = "interface/translate_en.txt"
        with self.assertRaises(SafetyError):
            self.make_engine()

    def test_loose_font_overrides_are_preserved_and_blocked(self):
        for name in ["fonts_en.swf", "fontconfig_en.txt", "fontconfig.txt"]:
            with self.subTest(name=name):
                p = self.game / "Data/interface" / name
                p.parent.mkdir(exist_ok=True)
                p.write_bytes(b"user override")
                with self.assertRaises(SafetyError):
                    self.engine.run("install")
                self.assertEqual(p.read_bytes(), b"user override")
                p.unlink()

    def test_prior_active_installations_block(self):
        for state in PRIOR_STATES:
            with self.subTest(state=state):
                p = self.game / state / "receipt.json"
                p.parent.mkdir()
                p.write_text('{"status":"installed"}')
                with self.assertRaises(SafetyError):
                    self.engine.run("install")
                p.write_text('{"status":"restored"}')

    def test_prior_pending_transactions_block(self):
        for state in PRIOR_STATES:
            with self.subTest(state=state):
                p = self.game / state / "pending.json"
                p.parent.mkdir()
                p.write_text("{}")
                with self.assertRaises(SafetyError):
                    self.engine.run("install")
                p.unlink()

    def test_prior_restored_receipts_retained(self):
        receipts = []
        for state in PRIOR_STATES:
            p = self.game / state / "receipt.json"
            p.parent.mkdir()
            p.write_text('{"status":"restored"}')
            receipts.append(p)
        before = {p: p.read_bytes() for p in receipts}
        self.engine.run("install")
        self.engine.run("restore")
        self.assertTrue(all(p.read_bytes() == b for p, b in before.items()))

    def test_repair_restores_missing_string_and_retains_installed_config(self):
        self.engine.run("install")
        p = self.game / sorted(STRINGS)[0]
        expected = p.read_bytes()
        p.unlink()
        self.assertEqual(self.engine.inspect()["status"], "repairable")
        self.engine.run("repair")
        self.assertEqual(p.read_bytes(), expected)
        self.assertEqual(
            hash_file(self.game / CONFIG_ARCHIVE),
            self.engine.release.by_path[CONFIG_ARCHIVE]["after_sha256"],
        )

    def test_existing_vanilla_tables_are_restored_exactly(self):
        for path in STRINGS:
            p = self.game / path
            p.parent.mkdir(exist_ok=True)
            p.write_bytes(("vanilla " + p.name).encode())
        before = self.snapshot()
        self.engine.run("install")
        self.engine.run("restore")
        self.assertEqual(self.snapshot(), before)

    def test_interruption_between_archives_recovers_both(self):
        def crash(index, entry):
            if index == 1:
                raise SystemExit("simulated crash")

        self.engine._after_replace = crash
        with self.assertRaises(SystemExit):
            self.engine.run("install")
        self.engine.recover()
        self.assertEqual(self.snapshot(), self.original)


if __name__ == "__main__":
    unittest.main(verbosity=2)
