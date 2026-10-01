import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from kks_installer.manager import STATE
from kks_installer.platforms import SafetyError
from kks_installer.engine import Release, Installer, digest
from kks_installer.managed_engine import LEGACY_STATE
from kks_installer.packages import STRINGS, ARCHIVES
from package_fixture import PackageFixture


class ManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.fx = PackageFixture(self.base)
        self.m = self.fx.manager()
        self.a = self.m.select(self.fx.a)

    def tearDown(self):
        self.temp.cleanup()

    def install(self):
        return self.m.run("install", self.a)

    def state(self):
        return self.m._read_state()

    def test_fresh_install_restore(self):
        self.assertEqual(self.m.inspect(self.a)["status"], "ready")
        self.install()
        self.assertEqual(self.m.inspect()["status"], "installed")
        self.m.run("restore")
        self.assertEqual(self.fx.snapshot(), self.fx.original)

    def test_skip_versions_and_restore_original_absence(self):
        self.install()
        z, _, _ = self.fx.build(5)
        c = self.m.select(z)
        self.assertEqual(self.m.inspect(c)["status"], "update_available")
        self.m.run("install", c)
        self.m.run("restore")
        self.assertEqual(self.fx.snapshot(), self.fx.original)
        self.assertEqual(self.state()["highest_sequence"], 5)

    def test_a_b_c_only_one_asset_changes(self):
        self.install()
        for n in (2, 3):
            z, _, _ = self.fx.build(n, one_change=True)
            release = self.m.select(z)
            self.m.run("install", release)
        self.m.run("restore")
        self.assertEqual(self.fx.snapshot(), self.fx.original)

    def test_payload_cache_not_needed_for_restore(self):
        self.install()
        self.fx.a.unlink()
        for p in self.a.files:
            (self.a.folder / p).unlink()
        result = self.m.inspect()
        self.assertFalse(result["repair_available"])
        self.assertTrue(result["restore_available"])
        self.m.run("restore")
        self.assertEqual(self.fx.snapshot(), self.fx.original)

    def test_repair_without_download_and_reimport_damaged_cache(self):
        self.install()
        path = self.fx.game / sorted(STRINGS)[0]
        expected = path.read_bytes()
        path.unlink()
        self.m.run("repair")
        self.assertEqual(path.read_bytes(), expected)
        payload = next(iter(self.a.files))
        (self.a.folder / payload).write_bytes(b"damaged")
        before = self.fx.snapshot()
        with self.assertRaises(SafetyError):
            self.m.run("repair")
        self.assertEqual(before, self.fx.snapshot())
        self.m.select(self.fx.a)
        self.m.run("repair")

    def test_reimport_repairs_corrupt_cached_descriptor(self):
        self.install()
        for name in ("manifest.json", "manifest.sig.json"):
            (self.a.folder / name).write_bytes(b"broken descriptor")
            with self.assertRaises(SafetyError):
                self.m.run("restore")
            self.m.select(self.fx.a)
            self.assertEqual(self.m.inspect()["status"], "installed")
        self.m.run("restore")
        self.assertEqual(self.fx.snapshot(), self.fx.original)

    def test_real_process_death_releases_locks_and_recovers(self):
        import subprocess, sys

        worker = self.base / "worker.py"
        worker.write_text("""import json, os, sys
from kks_installer.manager import Manager
game, package, keys, event = sys.argv[1:]
def die(name, data):
    if name == event: os._exit(97)
m = Manager(game, keys=json.loads(keys), event=die)
m.run('install', m.select(package))
""")
        # os._exit skips Python exception handlers and finally blocks entirely.
        for event in ("file_replaced", "engine_receipt_saved", "after_state_publish"):
            with self.subTest(event=event):
                sub = self.base / event
                sub.mkdir()
                fx = PackageFixture(sub)
                result = subprocess.run(
                    [
                        sys.executable,
                        "-c",
                        worker.read_text(),
                        str(fx.game),
                        str(fx.a),
                        json.dumps(fx.keys),
                        event,
                    ],
                    timeout=30,
                    capture_output=True,
                )
                self.assertEqual(result.returncode, 97, result.stderr.decode())
                fresh = fx.manager()
                fresh.recover()
                if fresh._read_state()["active"]:
                    fresh.run("restore")
                self.assertEqual(fx.snapshot(), fx.original)

    def test_recovery_itself_can_be_interrupted_and_retried(self):
        def stop(name, data):
            if name == "file_replaced":
                raise SystemExit("install interrupted")

        self.m.event = stop
        with self.assertRaises(SystemExit):
            self.install()
        fresh = self.fx.manager()

        def stop_recovery(name, data):
            if name == "phase_recovered":
                raise SystemExit("recovery interrupted")

        fresh.event = stop_recovery
        with self.assertRaises(SystemExit):
            fresh.recover()
        self.fx.manager().recover()
        self.assertEqual(self.fx.snapshot(), self.fx.original)

    def test_backup_write_failure_leaves_game_unchanged(self):
        before = self.fx.snapshot()
        with patch(
            "kks_installer.engine.verified_copy",
            side_effect=PermissionError("test denied backup write"),
        ):
            with self.assertRaises((SafetyError, PermissionError)):
                self.install()
        self.assertEqual(before, self.fx.snapshot())
        self.fx.manager().recover()
        self.assertEqual(before, self.fx.snapshot())

    def test_downgrade_and_reused_sequence_refused(self):
        self.install()
        z, _, _ = self.fx.build(3)
        self.m.run("install", self.m.select(z))
        before = self.fx.snapshot()
        with self.assertRaises(SafetyError):
            self.m.run("install", self.a)
        self.assertEqual(before, self.fx.snapshot())

    def test_bad_output_refused_before_removing_old(self):
        self.install()
        z, _, _ = self.fx.build(2, mutate=lambda m: m["targets"][0].update(after_sha256="0" * 64))
        b = self.m.select(z)
        before = self.fx.snapshot()
        with self.assertRaises(SafetyError):
            self.m.run("install", b)
        self.assertEqual(before, self.fx.snapshot())
        self.assertFalse(self.m.saved("pending.json").exists())

    def test_missing_backup_refuses_before_any_write(self):
        self.install()
        e = self.m._engine(self.state()["active"])
        r = e._receipt()
        e._backup_path(r["files"][next(iter(ARCHIVES))]["before"]).unlink()
        before = self.fx.snapshot()
        with self.assertRaises(SafetyError):
            self.m.run("restore")
        self.assertEqual(before, self.fx.snapshot())

    def test_new_game_identity_never_restores_stale_archives(self):
        self.install()
        (self.fx.game / "Data/SeventySix.esm").write_bytes(b"Bethesda update")
        before = self.fx.snapshot()
        for op in ("restore", "repair"):
            with self.assertRaises(SafetyError):
                self.m.run(op)
            self.assertEqual(before, self.fx.snapshot())

    def test_check_does_not_write(self):
        before = {p: p.read_bytes() for p in self.fx.game.rglob("*") if p.is_file()}
        self.m.inspect(self.a)
        self.assertEqual(
            before, {p: p.read_bytes() for p in self.fx.game.rglob("*") if p.is_file()}
        )

    def test_fresh_check_needs_package_and_creates_no_state(self):
        other = self.base / "other"
        other.mkdir()
        fx = PackageFixture(other)
        m = fx.manager()
        self.assertEqual(m.inspect()["status"], "package_required")
        self.assertFalse(m.state.exists())

    def test_low_disk_space_refuses_before_write(self):
        before = self.fx.snapshot()
        with patch(
            "kks_installer.manager.shutil.disk_usage", return_value=type("Space", (), {"free": 0})()
        ):
            with self.assertRaises(SafetyError):
                self.install()
        self.assertEqual(before, self.fx.snapshot())

    def test_unknown_active_state_refuses(self):
        p = self.fx.game / ".kks-unknown/receipt.json"
        p.parent.mkdir()
        p.write_text('{"status":"installed"}')
        with self.assertRaises(SafetyError):
            self.install()

    def test_interruption_each_upgrade_checkpoint(self):
        for checkpoint in (
            "after_restore_pending",
            "after_vanilla_committed",
            "after_install_pending",
            "before_state_publish",
            "after_state_publish",
            "before_plan_retirement",
        ):
            with self.subTest(checkpoint=checkpoint):
                sub = self.base / checkpoint
                sub.mkdir()
                fx = PackageFixture(sub)
                m = fx.manager()
                a = m.select(fx.a)
                m.run("install", a)
                z, _, _ = fx.build(2)
                b = m.select(z)

                def fail(event, data):
                    if event == checkpoint:
                        raise SystemExit("simulated process death")

                m.event = fail
                with self.assertRaises(SystemExit):
                    m.run("install", b)
                fresh = fx.manager()
                fresh.recover()
                self.assertFalse(fresh.saved("pending.json").exists())
                if fresh._read_state()["active"]:
                    fresh.run("restore")
                self.assertEqual(fx.snapshot(), fx.original)

    def test_interruption_each_file_in_fresh_install(self):
        for index in range(5):
            with self.subTest(index=index):
                sub = self.base / str(index)
                sub.mkdir()
                fx = PackageFixture(sub)
                m = fx.manager()
                a = m.select(fx.a)

                def fail(event, data):
                    if event == "file_replaced" and data["index"] == index:
                        raise SystemExit("process death")

                m.event = fail
                with self.assertRaises(SystemExit):
                    m.run("install", a)
                fx.manager().recover()
                self.assertEqual(fx.snapshot(), fx.original)

    def test_legacy_migration_without_old_payload_or_exe(self):
        legacy_folder = self.base / "legacy"
        legacy_folder.mkdir()
        (legacy_folder / "manifest.json").write_bytes(self.fx.legacy_raw)
        for p, b in self.fx.payloads.items():
            f = legacy_folder / p
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(b)
        e = Installer(
            self.fx.game,
            Release(legacy_folder, digest(self.fx.legacy_raw)),
            state_name=LEGACY_STATE,
        )
        e.run("install")
        for p in legacy_folder.rglob("*"):
            if p.is_file():
                p.unlink()
        self.assertEqual(self.m.inspect()["status"], "legacy_installed")
        self.install()
        self.m.run("restore")
        self.assertEqual(self.fx.snapshot(), self.fx.original)
        self.assertEqual(e._receipt()["status"], "restored")

    def test_reinstall_current_package_after_restore(self):
        self.install()
        self.m.run("restore")
        self.install()
        self.m.run("restore")
        self.assertEqual(self.fx.snapshot(), self.fx.original)

    def test_restore_preserves_originally_present_loose_tables_across_updates(self):
        sub = self.base / "present"
        sub.mkdir()
        fx = PackageFixture(sub, loose=True)
        m = fx.manager()
        a = m.select(fx.a)
        m.run("install", a)
        z, _, _ = fx.build(3)
        m.run("install", m.select(z))
        m.run("restore")
        self.assertEqual(fx.snapshot(), fx.original)

    def test_stable_and_legacy_operation_locks(self):
        from kks_installer.platforms import operation_lock

        for lock in (
            self.m.saved("operation.lock"),
            self.fx.game / LEGACY_STATE / "operation.lock",
        ):
            with self.subTest(lock=str(lock)):
                before = self.fx.snapshot()
                with operation_lock(lock):
                    with self.assertRaises(SafetyError):
                        self.install()
                self.assertEqual(before, self.fx.snapshot())

    def test_hardlinked_payload_cache_refused(self):
        import os

        payload = next(iter(self.a.files))
        os.link(self.a.folder / payload, self.base / "alias.bin")
        before = self.fx.snapshot()
        with self.assertRaises(SafetyError):
            self.install()
        self.assertEqual(before, self.fx.snapshot())

    def test_root_rebinding_and_unknown_receipt_targets_refused(self):
        self.install()
        engine = self.m._engine(self.state()["active"])
        original = engine.receipt_path.read_bytes()
        for mutate in (
            lambda r: r.update(root="C:\\other"),
            lambda r: r["files"].update({"Data/foreign.file": {"before": None, "after": "0" * 64}}),
            lambda r: r.update(schema=True),
            lambda r: r.update(extra=True),
        ):
            r = json.loads(original)
            mutate(r)
            engine.receipt_path.write_text(json.dumps(r))
            before = self.fx.snapshot()
            with self.assertRaises(SafetyError):
                self.m.run("restore")
            self.assertEqual(before, self.fx.snapshot())
        engine.receipt_path.write_bytes(original)

    def test_each_engine_commit_boundary_recovers(self):
        for checkpoint in (
            "engine_journal_saved",
            "engine_before_receipt",
            "engine_receipt_saved",
            "engine_journal_retired",
        ):
            with self.subTest(checkpoint=checkpoint):
                sub = self.base / checkpoint
                sub.mkdir()
                fx = PackageFixture(sub)
                m = fx.manager()
                a = m.select(fx.a)

                def crash(event, data):
                    if event == checkpoint:
                        raise SystemExit("commit boundary")

                m.event = crash
                with self.assertRaises(SystemExit):
                    m.run("install", a)
                fresh = fx.manager()
                fresh.recover()
                if fresh._read_state()["active"]:
                    fresh.run("restore")
                self.assertEqual(fx.snapshot(), fx.original)

    def test_each_upgrade_file_boundary_in_both_phases(self):
        for phase in ("restore", "install"):
            for index in range(5):
                with self.subTest(phase=phase, index=index):
                    sub = self.base / f"{phase}{index}"
                    sub.mkdir()
                    fx = PackageFixture(sub)
                    m = fx.manager()
                    a = m.select(fx.a)
                    m.run("install", a)
                    old_state = m._engine(m._read_state()["active"]).state_name
                    z, _, _ = fx.build(2)
                    b = m.select(z)

                    def crash(event, data):
                        if (
                            event == "file_replaced"
                            and data["index"] == index
                            and ((data["state"] == old_state) == (phase == "restore"))
                        ):
                            raise SystemExit("phase file boundary")

                    m.event = crash
                    with self.assertRaises(SystemExit):
                        m.run("install", b)
                    fresh = fx.manager()
                    fresh.recover()
                    if fresh._read_state()["active"]:
                        fresh.run("restore")
                    self.assertEqual(fx.snapshot(), fx.original)

    def test_interrupted_repair_returns_known_repairable_state(self):
        self.install()
        (self.fx.game / sorted(STRINGS)[0]).unlink()
        before = self.fx.snapshot()

        def crash(event, data):
            if event == "file_replaced":
                raise SystemExit("repair interrupted")

        self.m.event = crash
        with self.assertRaises(SystemExit):
            self.m.run("repair")
        fresh = self.fx.manager()
        fresh.recover()
        self.assertEqual(before, self.fx.snapshot())
        fresh.run("repair")
        fresh.run("restore")
        self.assertEqual(self.fx.snapshot(), self.fx.original)

    def test_modified_identity_during_recovery_never_rolls_back(self):
        def crash(event, data):
            if event == "file_replaced":
                raise SystemExit("interrupted")

        self.m.event = crash
        with self.assertRaises(SystemExit):
            self.install()
        (self.fx.game / "Data/SeventySix - Localization.ba2").write_bytes(
            b"new Bethesda localization"
        )
        before = self.fx.snapshot()
        with self.assertRaises(SafetyError):
            self.fx.manager().recover()
        self.assertEqual(before, self.fx.snapshot())

    def test_recovery_journal_cannot_choose_arbitrary_rollback(self):
        def crash(event, data):
            if event == "file_replaced":
                raise SystemExit("interrupted")

        self.m.event = crash
        with self.assertRaises(SystemExit):
            self.install()
        plan = json.loads(self.m.saved("pending.json").read_bytes())
        e = self.m._engine(plan["new"])
        j = json.loads(e.journal_path.read_bytes())
        j["entries"][0]["after"] = "0" * 64
        e.journal_path.write_text(json.dumps(j))
        before = self.fx.snapshot()
        with self.assertRaises(SafetyError):
            self.fx.manager().recover()
        self.assertEqual(before, self.fx.snapshot())


if __name__ == "__main__":
    unittest.main()
