"""Staged GUI choices must not perform any backend work until explicit Apply."""
from contextlib import ExitStack
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from kks_installer.equipment import FULL, VANILLA
from kks_installer.perks import ON, OFF
from kks_installer.ui import App, Configuration

DEFAULT = Configuration(FULL, ON, "food-v2", "glyph")
ALTERNATE = Configuration(VANILLA, OFF, "family-food", "none")


def installed(configuration=DEFAULT, manifest="installed", **overrides):
    result = dict(
        status="installed", installed_content="KKS fixture", installed_manifest=manifest,
        installed_verified=True, installed_equipment_naming_available=True,
        installed_perk_cards_available=True, installed_string_modes_available=True,
        repair_available=True, restore_available=True, play_available=True,
        installed_play_available=True,
    )
    result.update({"installed_" + key: value
                   for key, value in zip(Configuration._fields, configuration)})
    result.update(overrides)
    return result


@unittest.skipUnless(os.name == "nt", "Windows installer UI")
class StagedApplyTests(unittest.TestCase):
    def setUp(self):
        self.manager_factory = self.enterContext(patch("kks_installer.ui.Manager"))
        self.manager = self.manager_factory.return_value
        self.thread = self.enterContext(patch("kks_installer.ui.threading.Thread"))
        with patch.object(App, "start"):
            self.app = App(game=r"C:\KKS staged UI fixture only", language="en")
            self.app.root.attributes("-alpha", 0)
            self.app.root.geometry("900x700")
            self.app.root.update()
            for timer in self.app.root.tk.call("after", "info"):
                self.app.root.after_cancel(timer)
        self.manager.run.return_value = {"status": "installed"}
        self.manager.recover.return_value = {"status": "recovered"}

    def tearDown(self):
        self.app.busy = False
        self.app.close()

    def deliver(self, data, kind="success"):
        self.app.events.put((kind, data))
        self.app.pump()

    def draft(self, configuration):
        self.app.set_pending_configuration(configuration)
        self.app.configuration_changed()

    def finish_worker(self):
        self.thread.call_args.kwargs["target"]()
        self.app.pump()

    def test_startup_loads_nondefault_verified_configuration_and_cached_identity(self):
        self.deliver(installed(ALTERNATE))
        self.assertEqual(self.app.installed_verified_configuration, ALTERNATE)
        self.assertEqual(self.app.pending_selected_configuration, ALTERNATE)
        self.assertEqual(self.app.read_configuration(), ALTERNATE)
        self.assertEqual(self.app.selected, "installed")
        self.assertEqual(str(self.app.apply["state"]), "disabled")
        for box in (self.app.naming_box, self.app.perks_box, self.app.food_box, self.app.junk_box):
            self.assertEqual(str(box["state"]), "readonly")
        self.manager_factory.assert_not_called()

    def test_every_selector_change_and_revert_has_zero_work_or_filesystem_access(self):
        self.deliver(installed())
        logs = list(self.app.log_lines)
        with ExitStack() as stack:
            for target in ("builtins.open", "os.open", "os.stat", "os.scandir",
                           "os.mkdir", "os.replace", "os.remove", "shutil.copy2"):
                stack.enter_context(patch(target, side_effect=AssertionError(target)))
            for method in ("open", "read_bytes", "write_bytes", "read_text", "write_text"):
                stack.enter_context(patch.object(Path, method, side_effect=AssertionError(method)))
            boxes = (self.app.naming_box, self.app.perks_box, self.app.food_box, self.app.junk_box)
            for box in boxes:
                box.current(1)
                box.event_generate("<<ComboboxSelected>>")
                self.assertFalse(self.app.busy)
                self.assertEqual(str(self.app.apply["state"]), "normal")
                self.assertTrue(all(str(b["state"]) == "readonly" for b in boxes))
                self.assertEqual(self.app.installed_verified_configuration, DEFAULT)
            for box in boxes:
                box.current(0)
                box.event_generate("<<ComboboxSelected>>")
            self.assertEqual(self.app.pending_selected_configuration, DEFAULT)
            self.assertEqual(str(self.app.apply["state"]), "disabled")
            self.assertEqual(self.app.log_lines, logs)
            # Defend the handler too, even though the actual button is disabled.
            self.app.start("apply")
            self.app.primary_action()
            self.assertEqual(self.app.log_lines[-1], "No changes to apply.")
        self.thread.assert_not_called()
        self.manager_factory.assert_not_called()

    def test_apply_captures_all_four_choices_once_and_only_commits_verified_result(self):
        self.deliver(installed())
        self.draft(ALTERNATE)
        self.manager.inspect.side_effect = [installed(), installed(ALTERNATE)]
        self.app.apply.invoke()
        self.assertTrue(self.app.busy)
        self.assertEqual(self.app.installed_verified_configuration, DEFAULT)
        self.assertEqual(str(self.app.apply["state"]), "disabled")
        self.finish_worker()
        self.manager.package.assert_called_once_with("installed")
        self.manager.run.assert_called_once_with(
            "install", self.manager.package.return_value,
            **ALTERNATE._asdict(), accept_modifications=None,
        )
        self.assertEqual(self.app.installed_verified_configuration, ALTERNATE)
        self.assertEqual(self.app.pending_selected_configuration, ALTERNATE)
        self.assertEqual(str(self.app.apply["state"]), "disabled")

    def test_apply_failure_keeps_verified_snapshot_and_draft_and_blocks_retry_until_check(self):
        self.deliver(installed())
        self.draft(ALTERNATE)
        self.manager.inspect.return_value = installed()
        self.manager.run.side_effect = RuntimeError("Interrupted transaction")
        self.app.start("apply")
        self.finish_worker()
        self.assertEqual(self.app.installed_verified_configuration, DEFAULT)
        self.assertEqual(self.app.pending_selected_configuration, ALTERNATE)
        self.assertEqual(str(self.app.apply["state"]), "disabled")
        self.thread.reset_mock()
        self.app.start("apply")
        self.thread.assert_not_called()
        self.deliver({"status": "recovery_required"})
        self.assertEqual(self.app.primary_key, "Recover previous state")
        self.assertEqual(str(self.app.apply["state"]), "disabled")
        self.manager.inspect.return_value = installed()
        self.app.primary_action()
        self.finish_worker()
        self.manager.recover.assert_called_once_with()
        self.assertEqual(self.app.read_configuration(), DEFAULT)

    def test_post_transaction_inspection_failure_does_not_mark_draft_installed(self):
        self.deliver(installed())
        self.draft(ALTERNATE)
        self.manager.inspect.side_effect = [installed(), RuntimeError("Verification failed")]
        self.app.start("apply")
        self.finish_worker()
        self.assertEqual(self.app.installed_verified_configuration, DEFAULT)
        self.assertEqual(self.app.pending_selected_configuration, ALTERNATE)
        self.assertFalse(self.app.can_apply())
        # A later explicit successful Check is the authority, not the prior run's return.
        self.manager.inspect.side_effect = None
        self.manager.inspect.return_value = installed(ALTERNATE)
        self.app.start("check")
        self.finish_worker()
        self.assertEqual(self.app.installed_verified_configuration, ALTERNATE)
        self.assertEqual(str(self.app.apply["state"]), "disabled")

    def test_cancelled_consent_does_not_run_or_commit_pending_configuration(self):
        self.deliver(installed())
        self.draft(ALTERNATE)
        self.manager.inspect.return_value = installed(existing_modifications=["fontconfig"])
        with patch("kks_installer.ui.threading.Event") as event, patch.object(
            self.app, "confirm_modifications", return_value=False
        ):
            event.return_value.wait.side_effect = self.app.pump
            self.app.start("apply")
            self.finish_worker()
        self.manager.run.assert_not_called()
        self.assertEqual(self.app.installed_verified_configuration, DEFAULT)
        self.assertEqual(self.app.pending_selected_configuration, ALTERNATE)
        self.assertTrue(self.app.can_apply())

    def test_explicit_check_with_draft_does_not_enable_install_update_for_same_package(self):
        self.deliver(installed())
        self.draft(ALTERNATE)
        self.manager.inspect.return_value = installed(
            status="update_available", selected_manifest="installed", play_available=False
        )
        self.app.start("check")
        self.finish_worker()
        self.assertEqual(str(self.app.primary["state"]), "disabled")
        self.assertEqual(str(self.app.apply["state"]), "normal")
        self.assertEqual(self.app.pending_selected_configuration, ALTERNATE)
        self.assertEqual(str(self.app.play["state"]), "normal")
        self.draft(DEFAULT)
        self.assertEqual(str(self.app.apply["state"]), "disabled")
        self.assertEqual(str(self.app.play["state"]), "normal")
        self.manager.run.assert_not_called()

    def test_newer_package_with_equal_choices_remains_an_explicit_package_update(self):
        self.deliver(installed())
        release = SimpleNamespace(
            manifest_digest="newer", name="KKS update", files={},
            manifest={"game": {"language": "en"}, "equipment_naming": {},
                      "perk_cards": {}, "string_modes": {}},
        )
        self.manager.select.return_value = release
        self.manager.inspect.return_value = installed(
            status="update_available", selected_manifest="newer", play_available=False
        )
        self.app.dropped(["newer.zip"])
        self.finish_worker()
        self.manager.select.assert_called_once_with("newer.zip")
        self.manager.run.assert_not_called()
        self.assertEqual(self.app.pending_selected_configuration, DEFAULT)
        self.assertEqual(str(self.app.apply["state"]), "disabled")
        self.assertEqual(str(self.app.primary["state"]), "normal")
        self.assertEqual(str(self.app.play["state"]), "disabled")
        self.manager.inspect.side_effect = [
            installed(status="update_available", selected_manifest="newer"),
            installed(manifest="newer"),
        ]
        self.app.primary_action()
        self.finish_worker()
        self.manager.package.assert_called_once_with("newer")
        self.manager.run.assert_called_once()
        self.assertEqual(self.app.installed_manifest, "newer")

    def test_reselecting_same_package_loads_installed_nondefault_choices_without_update(self):
        self.deliver(installed(ALTERNATE))
        self.app.events.put(("selected", ("installed", "Same package", 7, "en", True, True, True)))
        self.app.active_action = "select"
        self.deliver(installed(ALTERNATE, status="update_available",
                               selected_manifest="installed", play_available=False))
        self.assertEqual(self.app.read_configuration(), ALTERNATE)
        self.assertFalse(self.app.can_apply())
        self.assertEqual(str(self.app.primary["state"]), "disabled")
        self.assertEqual(str(self.app.play["state"]), "normal")

    def test_play_uses_installed_configuration_without_applying_pending_choices(self):
        self.deliver(installed())
        self.draft(ALTERNATE)
        self.manager.play.return_value = {"message": "Launched"}
        self.manager.inspect.return_value = installed()
        self.app.play.invoke()
        self.finish_worker()
        self.manager.play.assert_called_once_with()
        self.manager.run.assert_not_called()
        self.assertEqual(self.app.installed_verified_configuration, DEFAULT)
        self.assertEqual(self.app.pending_selected_configuration, ALTERNATE)
        self.assertEqual(str(self.app.play["state"]), "disabled")

    def test_repair_uses_installed_state_and_preserves_unapplied_draft(self):
        self.deliver(installed())
        self.draft(ALTERNATE)
        self.manager.inspect.return_value = installed()
        self.app.repair.invoke()
        self.finish_worker()
        self.manager.run.assert_called_once_with("repair")
        self.assertEqual(self.app.installed_verified_configuration, DEFAULT)
        self.assertEqual(self.app.pending_selected_configuration, ALTERNATE)
        self.assertTrue(self.app.can_apply())

    def test_restore_clears_installed_configuration_without_applying_draft(self):
        self.deliver(installed())
        self.draft(ALTERNATE)
        self.manager.inspect.return_value = {"status": "package_required"}
        self.app.restore.invoke()
        self.finish_worker()
        self.manager.run.assert_called_once_with("restore")
        self.assertIsNone(self.app.installed_verified_configuration)
        self.assertIsNone(self.app.installed_manifest)
        self.assertFalse(self.app.can_apply())
        self.assertEqual(self.app.pending_selected_configuration, ALTERNATE)

    def test_unverified_or_changed_root_cannot_apply_retained_draft(self):
        for result in (
            {"status": "recovery_required"},
            installed(status="repairable", installed_verified=False),
            {"status": "update_available", "selected_manifest": "new-baseline"},
        ):
            with self.subTest(status=result["status"]):
                self.deliver(installed())
                self.draft(ALTERNATE)
                self.deliver(result)
                self.app.start("apply")
                self.assertFalse(self.app.can_apply())
                self.thread.assert_not_called()
        self.app.path.set(r"C:\Different fixture")
        self.assertIsNone(self.app.installed_verified_configuration)
        self.assertIsNone(self.app.installed_manifest)

    def test_missing_cache_disables_apply_until_package_is_reimported(self):
        self.deliver(installed(repair_available=False))
        self.draft(ALTERNATE)
        self.assertFalse(self.app.can_apply())
        self.app.start("apply")
        self.thread.assert_not_called()

    def test_pending_ids_survive_language_changes_and_apply_fits_existing_window(self):
        self.deliver(installed())
        self.draft(ALTERNATE)
        for language in ("de", "fr", "ru", "ptbr", "en"):
            self.app.language = language
            self.app.render_language()
            self.app.root.update()
            self.assertEqual(self.app.read_configuration(), ALTERNATE)
            self.assertTrue(self.app.can_apply())
            if language != "en":
                self.assertNotEqual(self.app.apply["text"], "Apply Changes")
            bottom = self.app.root.winfo_rooty() + self.app.root.winfo_height()
            right = self.app.root.winfo_rootx() + self.app.root.winfo_width()
            for widget in (self.app.apply, self.app.play, self.app.log):
                self.assertTrue(widget.winfo_ismapped())
                self.assertLessEqual(widget.winfo_rooty() + widget.winfo_height(), bottom)
                self.assertLessEqual(widget.winfo_rootx() + widget.winfo_width(), right)
            self.assertLessEqual(
                self.app.apply.winfo_rootx() + self.app.apply.winfo_width(),
                self.app.play.winfo_rootx(),
            )


if __name__ == "__main__":
    unittest.main()
