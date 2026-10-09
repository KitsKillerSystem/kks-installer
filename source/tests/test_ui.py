"""Exercise bounded status display and profile counts without game operations."""

import os
import unittest
from unittest.mock import patch


@unittest.skipUnless(os.name == "nt", "Windows installer UI")
class UiTests(unittest.TestCase):
    def setUp(self):
        from kks_installer.ui import App

        self.enterContext(patch.object(App, "start"))
        self.app = App(game=r"C:\KKS fixture only", language="en")
        self.app.root.geometry("900x700")
        self.app.root.update()

    def tearDown(self):
        self.app.close()

    def test_long_error_remains_readable_without_hiding_actions(self):
        message = "A long compatibility failure. " * 60
        self.app.events.put(("error", message))
        self.app.pump()
        self.app.root.update()
        self.assertEqual(self.app.status_message.get("1.0", "end-1c"), message)
        self.assertLess(self.app.status_message.yview()[1], 1)
        bottom = self.app.root.winfo_rooty() + self.app.root.winfo_height()
        for widget in (self.app.primary, self.app.repair, self.app.restore, self.app.play, self.app.log):
            self.assertTrue(widget.winfo_ismapped())
            self.assertLessEqual(widget.winfo_rooty() + widget.winfo_height(), bottom)
        self.assertGreaterEqual(self.app.log.winfo_height(), 30)
        self.assertEqual(str(self.app.primary["state"]), "disabled")

    def test_play_only_enables_after_verified_status_and_resets_on_error_or_path_change(self):
        self.assertEqual(str(self.app.play["state"]), "disabled")
        self.app.events.put(("success", {"status": "installed", "play_available": True}))
        self.app.pump()
        self.assertEqual(str(self.app.play["state"]), "normal")
        self.app.events.put(("error", "Unverified change"))
        self.app.pump()
        self.assertEqual(str(self.app.play["state"]), "disabled")
        self.app.events.put(("success", {"status": "installed", "play_available": True}))
        self.app.pump()
        self.app.path.set("C:\\Another game")
        self.assertEqual(str(self.app.play["state"]), "disabled")

    def test_confirmation_is_on_ui_thread_and_cancel_is_default(self):
        import threading
        signal, answer = threading.Event(), {}
        self.app.busy = True
        self.app.events.put(("confirm", (["interface/fontconfig_en.txt"], signal, answer)))
        with patch.object(self.app, "confirm_modifications", return_value=False) as dialog:
            self.app.pump()
            dialog.assert_called_once()
        self.assertTrue(signal.is_set())
        self.assertFalse(answer["accepted"])
        self.app.busy = False

    def test_new_controls_and_help_are_translated_in_all_supported_languages(self):
        from kks_installer.i18n import translate
        from kks_installer.i18n_baseline import HELP, WARNING
        for lang in ("de", "fr", "ru"):
            for key in ("Restore Baseline", "Play Fallout 76", "Continue", "Cancel", HELP, WARNING):
                self.assertNotEqual(translate(key, lang), key)

    def test_six_payload_selection_and_update_count(self):
        self.app.events.put(("selected", ("digest", "Candidate", 6, "en")))
        self.app.events.put(
            (
                "success",
                {"status": "update_available", "changed_payload_files": 3, "payload_file_count": 6},
            )
        )
        self.app.pump()
        self.assertIn("all 6 files verified", self.app.package_text.get())
        self.assertIn("3 of 6", self.app.status_message.get("1.0", "end-1c"))
        self.assertEqual(str(self.app.primary["state"]), "normal")
        self.assertEqual(self.app.primary["text"], "Install update")

    def test_equipment_choice_requires_support_and_defaults_to_full(self):
        from kks_installer.equipment import FULL, VANILLA, LABELS

        self.app.events.put(("selected", ("digest", "Candidate", 6, "en", True)))
        self.app.events.put(("success", {"status": "ready"}))
        self.app.pump()
        self.assertEqual(self.app.naming_value.get(), LABELS[FULL])
        self.assertEqual(str(self.app.naming_box["state"]), "readonly")
        self.app.naming_value.set(LABELS[VANILLA])
        self.app.events.put(("selected", ("old", "Old content", 6, "en", False)))
        self.app.events.put(("success", {"status": "ready"}))
        self.app.pump()
        self.assertEqual(self.app.naming_value.get(), LABELS[FULL])
        self.assertEqual(str(self.app.naming_box["state"]), "disabled")

    def test_german_switch_preserves_selected_package_and_restore_visibility(self):
        self.app.events.put(("selected", ("digest", "KKS 1.1.0 Deutsch", 6, "de")))
        self.app.events.put(
            (
                "success",
                {
                    "status": "installed",
                    "restore_available": True,
                    "repair_available": True,
                    "message": "KKS is installed and verified.",
                },
            )
        )
        self.app.pump()
        with patch("kks_installer.ui.save_language"):
            self.app.language_value.set("Deutsch")
            self.app.change_language()
        self.app.root.update()
        self.assertEqual(self.app.selected, "digest")
        self.assertIn("Inhaltssprache: Deutsch", self.app.package_text.get())
        self.assertEqual(self.app.restore["text"], "Ausgangszustand wiederherstellen")
        self.assertEqual(self.app.status_title["text"], "KKS ist installiert.")
        self.assertEqual(str(self.app.restore["state"]), "normal")
        bottom = self.app.root.winfo_rooty() + self.app.root.winfo_height()
        for w in (self.app.primary, self.app.repair, self.app.restore, self.app.log):
            self.assertLessEqual(w.winfo_rooty() + w.winfo_height(), bottom)
        self.assertGreaterEqual(self.app.log.winfo_height(), 30)
        with patch("kks_installer.ui.save_language"):
            self.app.language_value.set("English")
            self.app.change_language()
        self.assertEqual(self.app.restore["text"], "Restore Baseline")
        self.assertEqual(self.app.selected, "digest")

    def test_perk_choice_requires_supported_package_and_is_independent(self):
        from kks_installer.perks import ON, OFF, LABELS
        from kks_installer.equipment import VANILLA, LABELS as EQUIPMENT_LABELS

        self.assertEqual(str(self.app.perks_box["state"]), "disabled")
        self.app.events.put(("selected", ("digest", "Optional features", 6, "en", True, True)))
        self.app.events.put(("success", {"status": "ready"}))
        self.app.pump()
        self.assertEqual(str(self.app.perks_box["state"]), "readonly")
        self.assertEqual(self.app.perks_value.get(), LABELS[ON])
        self.app.perks_value.set(LABELS[OFF])
        self.app.naming_value.set(EQUIPMENT_LABELS[VANILLA])
        self.app.events.put(("success", {"status": "update_available"}))
        self.app.pump()
        self.assertEqual(self.app.perks_value.get(), LABELS[OFF])
        self.assertEqual(self.app.naming_value.get(), EQUIPMENT_LABELS[VANILLA])
        self.app.events.put(("selected", ("equipment", "Equipment only", 6, "en", True)))
        self.app.events.put(("success", {"status": "ready"}))
        self.app.pump()
        self.assertEqual(str(self.app.perks_box["state"]), "disabled")
        self.assertEqual(str(self.app.naming_box["state"]), "readonly")
        self.assertEqual(self.app.perks_value.get(), LABELS[ON])

if __name__ == "__main__":
    unittest.main()
