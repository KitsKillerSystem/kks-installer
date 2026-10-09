"""Migration behavior, consent, exact preservation, and transaction failures."""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from certify_archives import certificate
from kks_installer.ba2 import BA2, ArchiveError
from kks_installer.engine import digest
from kks_installer.migration import CATALOG
from kks_installer.packages import CONFIG, FONT, LOCALIZATION
from kks_installer.platforms import SafetyError
from package_fixture import PackageFixture
from test_equipment import table


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.fx = PackageFixture(self.base)
        self.m = self.fx.manager()
        self.r = self.m.select(self.fx.a)
        self.certify(self.fx, self.r)

    def certify(self, fx, release):
        certs = {t["vanilla_sha256"]: certificate(fx.game / t["path"], t)
                 for t in release.targets if t["kind"] == "archive" and t["path"] != LOCALIZATION}
        self.enterContext(patch.dict(CATALOG, certs))

    def change(self, replacements, path=CONFIG, fx=None):
        fx = fx or self.fx
        src = fx.game / path
        dst = src.with_suffix(".new")
        BA2(src).replace_to(dst, replacements)
        os.replace(dst, src)

    def install(self, release=None):
        release = release or self.r
        checked = self.m.inspect(release)
        return self.m.run("install", release, accept_modifications=checked["confirmation_token"])

    def test_unrelated_mod_needs_no_confirmation_and_restores_exact_archive(self):
        self.change({"untouched.dat": b"third-party interface customization"})
        before = self.fx.snapshot()
        checked = self.m.inspect(self.r)
        self.assertTrue(checked["baseline_modified"])
        self.assertEqual(checked["existing_modifications"], [])
        self.m.run("install", self.r)
        self.assertEqual(BA2(self.fx.game / CONFIG).extract("untouched.dat"), b"third-party interface customization")
        self.m.run("restore")
        self.assertEqual(self.fx.snapshot(), before)

    def test_overlap_requires_exact_consent_and_cancellation_changes_no_game_files(self):
        self.change({"interface/fontconfig_en.txt": b"other mod font configuration"})
        before = self.fx.snapshot()
        checked = self.m.inspect(self.r)
        self.assertEqual(checked["existing_modifications"], ["interface/fontconfig_en.txt"])
        for consent in (None, True, "stale-token"):
            with self.assertRaises(SafetyError):
                self.m.run("install", self.r, accept_modifications=consent)
            self.assertEqual(self.fx.snapshot(), before)
            self.assertIsNone(self.m._read_state()["active"])
        self.install()
        self.m.run("restore")
        self.assertEqual(self.fx.snapshot(), before)

    def test_consent_expires_when_any_target_changes(self):
        self.change({"interface/fontconfig_en.txt": b"first mod"})
        token = self.m.inspect(self.r)["confirmation_token"]
        self.change({"untouched.dat": b"second mod"})
        before = self.fx.snapshot()
        with self.assertRaises(SafetyError):
            self.m.run("install", self.r, accept_modifications=token)
        self.assertEqual(self.fx.snapshot(), before)

    def test_upgrade_repair_and_cacheless_restore_preserve_original_mods(self):
        self.change({"interface/fontconfig_en.txt": b"old fontconfig", "untouched.dat": b"unrelated mod"})
        self.change({"interface/fonts_en.swf": b"old icon mod"}, FONT)
        path = self.fx.game / "Data/strings/seventysix_en.strings"
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(table([(1, b"custom sorting name")]))
        before = self.fx.snapshot()
        self.install()
        first_baseline = self.m._read_state()["active"]["baseline"]
        package, _, _ = self.fx.build(5)
        later = self.m.select(package)
        self.m.run("install", later)
        self.assertEqual(self.m._read_state()["active"]["baseline"], first_baseline)
        after = self.fx.snapshot()
        (self.fx.game / CONFIG).write_bytes(self.fx.raw_originals[CONFIG])
        path.unlink()
        self.assertEqual(self.m.inspect()["status"], "repairable")
        self.m.run("repair")
        self.assertEqual(self.fx.snapshot(), after)
        for file in later.files:
            (later.folder / file).unlink()
        self.assertTrue(self.m.inspect()["restore_available"])
        self.assertFalse(self.m.inspect()["repair_available"])
        self.m.run("restore")
        self.assertEqual(self.fx.snapshot(), before)

    def test_missing_or_damaged_baseline_and_output_backups_refuse_all_writes(self):
        self.change({"interface/fontconfig_en.txt": b"old mod"})
        self.install()
        engine = self.m._engine(self.m._read_state()["active"])
        before = self.fx.snapshot()
        for key in ("before", "after"):
            path = engine._backup_path(engine.baseline_context["files"][CONFIG][key])
            saved = path.read_bytes()
            path.write_bytes(b"damaged")
            for operation in ("restore", "repair"):
                with self.assertRaises(SafetyError):
                    self.m.run(operation)
                self.assertEqual(self.fx.snapshot(), before)
            path.write_bytes(saved)

    def test_external_post_install_mod_is_not_overwritten(self):
        self.change({"interface/fontconfig_en.txt": b"old mod"})
        self.install()
        self.change({"untouched.dat": b"new external change"})
        before = self.fx.snapshot()
        for op in ("restore", "repair"):
            with self.assertRaises(SafetyError):
                self.m.run(op)
            self.assertEqual(self.fx.snapshot(), before)

    def test_catalogue_or_build_mismatch_and_corrupt_unowned_stream_refused(self):
        src = self.fx.game / CONFIG
        native = src.read_bytes()
        self.change({"interface/fontconfig_en.txt": b"mod"})
        target = self.r.by_path[CONFIG]
        cert = deepcopy(CATALOG[target["vanilla_sha256"]])
        for mutation in ("missing", "metadata", "obsolete", "anchor"):
            with self.subTest(mutation=mutation):
                bad = deepcopy(cert)
                if mutation == "missing":
                    del bad["members"]["untouched.dat"]
                elif mutation == "metadata":
                    bad["members"]["untouched.dat"]["metadata"][0] ^= 1
                elif mutation == "obsolete":
                    bad["members"]["interface/fontconfig_en.txt"]["obsolete"] = [digest(b"mod")]
                else:
                    bad["anchors"] = ["interface/fontconfig_en.txt"]
                with patch.dict(CATALOG, {target["vanilla_sha256"]: bad}):
                    with self.assertRaises(SafetyError):
                        self.m.inspect(self.r)
        src.write_bytes(native)
        member = BA2(src).by_name["interface/translate_en.txt"]
        corrupt = bytearray(native)
        corrupt[member.offset] ^= 0xff
        src.write_bytes(corrupt)
        with self.assertRaises((SafetyError, ArchiveError)):
            self.m.run("install", self.r)
        self.assertEqual(src.read_bytes(), corrupt)

    def test_uncertified_modified_archive_is_not_accepted_by_structure_alone(self):
        self.change({"interface/fontconfig_en.txt": b"mod"})
        with patch.dict(CATALOG, {}, clear=True):
            with self.assertRaises(SafetyError):
                self.m.inspect(self.r)

    def test_interruption_at_every_file_and_commit_boundary(self):
        checkpoints = ["outputs_verified", "after_install_pending", "engine_journal_saved",
                       "file_replaced", "engine_before_receipt", "engine_receipt_saved",
                       "before_state_publish", "after_state_publish", "before_plan_retirement"]
        for point in checkpoints:
            with self.subTest(point=point):
                base = self.base / point
                base.mkdir()
                fx = PackageFixture(base)
                manager = fx.manager()
                release = manager.select(fx.a)
                self.certify(fx, release)
                self.change({"interface/fontconfig_en.txt": b"old mod", "untouched.dat": b"other mod"}, fx=fx)
                before = fx.snapshot()
                checked = manager.inspect(release)
                def stop(name, data):
                    if name == point:
                        raise SystemExit("interrupted")
                manager.event = stop
                with self.assertRaises(SystemExit):
                    manager.run("install", release, accept_modifications=checked["confirmation_token"])
                fresh = fx.manager()
                fresh.recover()
                if fresh._read_state()["active"]:
                    fresh.run("restore")
                self.assertEqual(fx.snapshot(), before)

    def test_all_optional_profiles_reuse_same_captured_baseline(self):
        from test_perks import fixture
        base = self.base / "options"
        base.mkdir()
        fx = fixture(base)
        manager = fx.manager()
        release = manager.select(fx.option_zip)
        self.certify(fx, release)
        self.change({"interface/fontconfig_en.txt": b"prior fontconfig"}, fx=fx)
        before = fx.snapshot()
        baseline = None
        for naming, perks in (("full-kks", "on"), ("vanilla-equipment", "on"),
                              ("full-kks", "off"), ("vanilla-equipment", "off")):
            checked = manager.inspect(release, naming=naming, perks=perks)
            manager.run("install", release, naming=naming, perks=perks,
                        accept_modifications=checked.get("confirmation_token"))
            active = manager._read_state()["active"]
            baseline = baseline or active["baseline"]
            self.assertEqual(active["baseline"], baseline)
            self.assertEqual((active["naming"], active["perks"]), (naming, perks))
        manager.run("repair")
        manager.run("restore")
        self.assertEqual(fx.snapshot(), before)

    def test_migrated_upgrade_interruption_keeps_the_first_baseline(self):
        for checkpoint in ("after_restore_pending", "after_vanilla_committed", "after_install_pending",
                           "file_replaced", "engine_receipt_saved", "after_state_publish"):
            with self.subTest(checkpoint=checkpoint):
                base = self.base / checkpoint
                base.mkdir()
                fx = PackageFixture(base)
                manager = fx.manager()
                first = manager.select(fx.a)
                self.certify(fx, first)
                self.change({"interface/fontconfig_en.txt": b"pre-KKS config", "untouched.dat": b"other mod"}, fx=fx)
                before = fx.snapshot()
                manager.run("install", first, accept_modifications=manager.inspect(first)["confirmation_token"])
                package, _, _ = fx.build(5, translation_localization=True)
                later = manager.select(package)
                def stop(name, data):
                    if name == checkpoint:
                        raise SystemExit("upgrade interrupted")
                manager.event = stop
                with self.assertRaises(SystemExit):
                    manager.run("install", later)
                fresh = fx.manager()
                fresh.recover()
                if fresh._read_state()["active"]:
                    fresh.run("restore")
                self.assertEqual(fx.snapshot(), before)

    def test_each_migrated_file_boundary_recovers_exact_original(self):
        for index in range(len(self.r.targets)):
            with self.subTest(index=index):
                base = self.base / str(index)
                base.mkdir()
                fx = PackageFixture(base)
                manager = fx.manager()
                release = manager.select(fx.a)
                self.certify(fx, release)
                self.change({"interface/fontconfig_en.txt": b"pre-KKS config"}, fx=fx)
                before = fx.snapshot()
                def stop(name, data):
                    if name == "file_replaced" and data["index"] == index:
                        raise SystemExit("interrupted file")
                manager.event = stop
                with self.assertRaises(SystemExit):
                    manager.run("install", release, accept_modifications=manager.inspect(release)["confirmation_token"])
                fx.manager().recover()
                self.assertEqual(fx.snapshot(), before)

    def test_context_cannot_authorize_unrelated_output_changes(self):
        self.change({"interface/fontconfig_en.txt": b"pre-KKS config"})
        self.install()
        engine = self.m._engine(self.m._read_state()["active"])
        record = deepcopy(engine.baseline_context)
        original_output = engine._backup_path(record["files"][CONFIG]["after"])
        altered = self.base / "altered.ba2"
        BA2(original_output).replace_to(altered, {"untouched.dat": b"unauthorized change"})
        h = digest(altered.read_bytes())
        engine._backup(altered, h)
        record["files"][CONFIG]["after"] = h
        engine.state_path("baseline-context.json").write_text(json.dumps(record))
        before = self.fx.snapshot()
        with self.assertRaises((SafetyError, ArchiveError)):
            self.m.run("restore")
        self.assertEqual(self.fx.snapshot(), before)

    def test_updated_game_can_capture_current_modifications_after_old_kks_cleanup(self):
        from test_reconciliation import steam_update
        self.m.run("install", self.r)
        new = self.m.select(steam_update(self.fx))
        self.certify(self.fx, new)
        self.change({"interface/fontconfig_en.txt": b"current build interface mod"})
        before = self.fx.snapshot()
        expected = {p: h for p, h in before.items() if not p.startswith("Data/strings/")}
        checked = self.m.inspect(new)
        with self.assertRaises(SafetyError):
            self.m.run("install", new)
        self.assertEqual(self.fx.snapshot(), before)
        self.m.run("install", new, accept_modifications=checked["confirmation_token"])
        self.m.run("restore")
        self.assertEqual(self.fx.snapshot(), expected)

    def test_interrupted_new_build_migration_recovers_forward_without_old_archives(self):
        from test_reconciliation import steam_update
        self.m.run("install", self.r)
        new = self.m.select(steam_update(self.fx))
        self.certify(self.fx, new)
        self.change({"interface/fontconfig_en.txt": b"current build interface mod"})
        expected = {p: h for p, h in self.fx.snapshot().items() if not p.startswith("Data/strings/")}
        def stop(name, data):
            if name == "override_retired":
                raise SystemExit("cleanup interrupted")
        self.m.event = stop
        with self.assertRaises(SystemExit):
            self.m.run("install", new, accept_modifications=self.m.inspect(new)["confirmation_token"])
        self.fx.manager().recover()
        self.assertEqual(self.fx.snapshot(), expected)

    def test_play_requires_verified_install_and_never_launches_during_recovery(self):
        with patch("kks_installer.manager.can_launch", return_value=True), patch("kks_installer.manager.launch_game") as launch:
            with self.assertRaises(SafetyError):
                self.m.play()
            self.m.run("install", self.r)
            self.m.play()
            launch.assert_called_once_with(self.fx.game)
            with patch("kks_installer.manager.game_running", return_value=True):
                with self.assertRaises(SafetyError):
                    self.m.play()
            self.change({"untouched.dat": b"unrecognized edit"})
            with self.assertRaises(SafetyError):
                self.m.play()
            self.assertEqual(launch.call_count, 1)

    @unittest.skipUnless(os.name == "nt", "Windows Steam launch")
    def test_launch_uses_fixed_steam_uri_and_validates_selected_library(self):
        from kks_installer.platforms import can_launch, launch_game
        root = self.base / "steamapps/common/Fallout76"
        root.mkdir(parents=True)
        manifest = root.parent.parent / "appmanifest_1151340.acf"
        manifest.write_text('"appid" "1151340"\n"installdir" "Fallout76"')
        with patch("kks_installer.platforms.discover", return_value=[str(root)]), \
             patch("kks_installer.platforms.game_running", return_value=False), \
             patch("kks_installer.platforms.os.startfile") as launch:
            self.assertTrue(can_launch(root))
            launch_game(root)
            launch.assert_called_once_with("steam://rungameid/1151340")
            manifest.write_text('"appid" "1151340"\n"installdir" "OtherCopy"')
            with self.assertRaises(SafetyError):
                launch_game(root)
            self.assertEqual(launch.call_count, 1)
