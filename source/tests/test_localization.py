"""Localization-archive ownership, five-to-six target migration and recovery."""

from copy import deepcopy
from pathlib import Path
import tempfile, unittest
from package_fixture import PackageFixture
from test_installer import archive
from kks_installer.packages import (
    LOCALIZATION,
    CONFIG,
    TRANSLATION,
    TRANSLATION_PAYLOAD,
    import_package,
)
from kks_installer._application import TRANSLATION_PROFILE
from kks_installer.manager import fingerprint
from kks_installer.ba2 import BA2, hash_file
from kks_installer.platforms import SafetyError


class LocalizationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.fx = PackageFixture(self.base)
        self.path, self.manifest, self.payloads = self.fx.build(3, translation_localization=True)

    def tearDown(self):
        self.tmp.cleanup()

    def install_previous(self):
        path, _, _ = self.fx.build(2, include_translation=True)
        manager = self.fx.manager()
        previous = manager.select(path)
        manager.run("install", previous)
        return manager, previous

    def test_rc1_upgrade_preserves_old_baseline_and_restores_six_targets(self):
        manager, previous = self.install_previous()
        old_ref = deepcopy(manager._read_state()["active"])
        old_baseline_path = manager.saved("baselines/" + old_ref["baseline"] + ".json")
        frozen = old_baseline_path.read_bytes()
        current = manager.select(self.path)
        self.assertEqual(fingerprint(previous), fingerprint(current))
        self.assertEqual(manager.inspect(current)["status"], "update_available")
        manager.run("install", current)
        self.assertEqual(old_baseline_path.read_bytes(), frozen)
        self.assertNotEqual(manager._read_state()["active"]["baseline"], old_ref["baseline"])
        self.assertEqual(len(manager._baseline(manager._read_state()["active"])["originals"]), 6)
        self.assertEqual(
            BA2(self.fx.game / LOCALIZATION).extract(TRANSLATION),
            self.payloads[TRANSLATION_PAYLOAD],
        )
        self.assertIn("(Known)".encode("utf-16le"), BA2(self.fx.game / CONFIG).extract(TRANSLATION))
        self.assertEqual(
            BA2(self.fx.game / LOCALIZATION).extract("strings/other-language.strings"),
            b"untouched localization",
        )
        manager.run("repair")
        manager.run("restore")
        self.assertEqual(self.fx.snapshot(), self.fx.original)

    def test_fresh_install_and_translation_update(self):
        manager = self.fx.manager()
        current = manager.select(self.path)
        manager.run("install", current)
        self.assertEqual(manager.inspect()["status"], "installed")
        path, _, _ = self.fx.build(4, translation_localization=True)
        manager.run("install", manager.select(path))
        manager.run("restore")
        self.assertEqual(self.fx.snapshot(), self.fx.original)

    def test_old_no_translation_package_updates_directly(self):
        manager = self.fx.manager()
        manager.run("install", manager.select(self.fx.a))
        manager.run("install", manager.select(self.path))
        manager.run("restore")
        self.assertEqual(self.fx.snapshot(), self.fx.original)

    def test_foreign_localization_blocks_install_repair_restore(self):
        for installed in [False, True]:
            sub = self.base / str(installed)
            fx = PackageFixture(sub)
            p, _, _ = fx.build(3, translation_localization=True)
            m = fx.manager()
            r = m.select(p)
            if installed:
                m.run("install", r)
            (fx.game / LOCALIZATION).write_bytes(b"foreign archive")
            before = fx.snapshot()
            for op in (["repair", "restore"] if installed else ["install"]):
                with self.assertRaises(SafetyError):
                    m.run(op, r if op == "install" else None)
                self.assertEqual(fx.snapshot(), before)

    def test_signed_wrong_member_pin_blocks_before_previous_install_removed(self):
        manager, _ = self.install_previous()
        before = self.fx.snapshot()
        m = deepcopy(self.manifest)
        next(t for t in m["targets"] if t["path"] == LOCALIZATION)["assets"][0][
            "vanilla_sha256"
        ] = ("a" * 64)
        path = self.fx.write(self.base / "wrong-member.zip", m, self.payloads)
        with self.assertRaises(SafetyError):
            manager.run("install", manager.select(path))
        self.assertEqual(self.fx.snapshot(), before)

    def test_closed_profile_and_original_identity_binding(self):
        mutations = [
            lambda m: m.update(profile=TRANSLATION_PROFILE),
            lambda m: m.update(minimum_installer_version="1.2.0"),
            lambda m: next(t for t in m["targets"] if t["path"] == LOCALIZATION).update(
                vanilla_sha256="a" * 64
            ),
            lambda m: next(t for t in m["targets"] if t["path"] == LOCALIZATION).update(
                vanilla_size=17
            ),
            lambda m: next(t for t in m["targets"] if t["path"] == LOCALIZATION)["assets"][
                0
            ].update(name="interface/translate_fr.txt"),
            lambda m: m["targets"].pop(),
        ]
        for mutate in mutations:
            m = deepcopy(self.manifest)
            mutate(m)
            path = self.fx.write(self.base / "bad.zip", m, self.payloads)
            with self.assertRaises(SafetyError):
                import_package(path, self.base / "bad-cache", self.fx.keys)

    def test_each_new_target_interruption_recovers_certified_vanilla(self):
        for index in range(6):
            with self.subTest(index=index):
                fx = PackageFixture(self.base / ("crash" + str(index)))
                old, _, _ = fx.build(2, include_translation=True)
                new, _, _ = fx.build(3, translation_localization=True)
                manager = fx.manager()
                manager.run("install", manager.select(old))
                r = manager.select(new)

                def fail(name, data):
                    if name == "file_replaced" and data["index"] == index:
                        # Crash only in the new six-target installation phase.
                        pending = manager.saved("pending.json")
                        import json

                        if (
                            pending.exists()
                            and json.loads(pending.read_bytes())["phase"] == "install_pending"
                        ):
                            raise SystemExit("crash")

                with self.assertRaises(SystemExit):
                    fx.manager(event=fail).run("install", r)
                fresh = fx.manager()
                fresh.recover()
                self.assertEqual(fx.snapshot(), fx.original)
                fresh.run("install", r)
                fresh.run("restore")
                self.assertEqual(fx.snapshot(), fx.original)

    def test_restore_works_without_cached_payload(self):
        manager = self.fx.manager()
        r = manager.select(self.path)
        manager.run("install", r)
        (r.folder / TRANSLATION_PAYLOAD).unlink()
        manager.run("restore")
        self.assertEqual(self.fx.snapshot(), self.fx.original)

    def updated_game(self, fx):
        from test_reconciliation import steam_update

        steam_update(fx)
        archive(
            fx.game / LOCALIZATION,
            [
                (TRANSLATION, b"new vanilla translation", True),
                ("new-language.dat", b"new unrelated language", False),
            ],
        )
        fx.raw_originals[LOCALIZATION] = (fx.game / LOCALIZATION).read_bytes()
        return fx.build(
            6,
            translation_localization=True,
            mutate=lambda m: m["game"].update(baseline_id="updated-baseline"),
        )[0]

    def test_new_game_reconciliation_covers_localization(self):
        from kks_installer.packages import STRINGS

        manager = self.fx.manager()
        manager.run("install", manager.select(self.path))
        path = self.updated_game(self.fx)
        expected = {p: h for p, h in self.fx.snapshot().items() if p not in STRINGS}
        manager.run("install", manager.select(path))
        manager.run("restore")
        self.assertEqual(self.fx.snapshot(), expected)

    def test_incomplete_game_update_localization_blocks_all_cleanup(self):
        manager = self.fx.manager()
        manager.run("install", manager.select(self.path))
        old = (self.fx.game / LOCALIZATION).read_bytes()
        path = self.updated_game(self.fx)
        (self.fx.game / LOCALIZATION).write_bytes(old)
        before = self.fx.snapshot()
        with self.assertRaises(SafetyError):
            manager.run("install", manager.select(path))
        self.assertEqual(self.fx.snapshot(), before)

    def test_restore_interruption_at_localization_recovers_installed_state(self):
        manager = self.fx.manager()
        manager.run("install", manager.select(self.path))
        installed = self.fx.snapshot()

        def fail(name, data):
            if name == "file_replaced" and data["entry"]["path"] == LOCALIZATION:
                raise SystemExit("crash")

        with self.assertRaises(SystemExit):
            self.fx.manager(event=fail).run("restore")
        self.fx.manager().recover()
        self.assertEqual(self.fx.snapshot(), installed)
        self.fx.manager().run("restore")
        self.assertEqual(self.fx.snapshot(), self.fx.original)

    def test_shrinking_targets_requires_restore_first(self):
        manager = self.fx.manager()
        manager.run("install", manager.select(self.path))
        p, _, _ = self.fx.build(4)
        # Author the old-format package against the certified vanilla identity.
        import json, zipfile

        with zipfile.ZipFile(p) as z:
            m = json.loads(z.read("manifest.json"))
            payloads = {f["path"]: z.read(f["path"]) for f in m["files"]}
        identity = next(i for i in m["game"]["identity"] if i["path"] == LOCALIZATION)
        identity.update(
            sha256=hash_file(self.base / "vanilla-3-2.ba2"),
            size=len(self.fx.raw_originals[LOCALIZATION]),
        )
        self.fx.write(p, m, payloads)
        r = manager.select(p)
        before = self.fx.snapshot()
        with self.assertRaisesRegex(SafetyError, "Restore vanilla"):
            manager.run("install", r)
        self.assertEqual(self.fx.snapshot(), before)
        manager.run("restore")
        manager.run("install", r)
        manager.run("restore")
        self.assertEqual(self.fx.snapshot(), self.fx.original)


if __name__ == "__main__":
    unittest.main()
