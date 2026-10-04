"""Exercise bounded status display and profile counts without game operations."""

import os
import unittest
from unittest.mock import patch


@unittest.skipUnless(os.name == "nt", "Windows installer UI")
class UiTests(unittest.TestCase):
    def setUp(self):
        from kks_installer.ui import App

        with patch.object(App, "start"):
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
        for widget in (self.app.primary, self.app.repair, self.app.restore, self.app.log):
            self.assertTrue(widget.winfo_ismapped())
            self.assertLessEqual(widget.winfo_rooty() + widget.winfo_height(), bottom)
        self.assertGreaterEqual(self.app.log.winfo_height(), 30)
        self.assertEqual(str(self.app.primary["state"]), "disabled")

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
        self.assertEqual(self.app.restore["text"], "Original wiederherstellen")
        self.assertEqual(self.app.status_title["text"], "KKS ist installiert.")
        self.assertEqual(str(self.app.restore["state"]), "normal")
        bottom = self.app.root.winfo_rooty() + self.app.root.winfo_height()
        for w in (self.app.primary, self.app.repair, self.app.restore, self.app.log):
            self.assertLessEqual(w.winfo_rooty() + w.winfo_height(), bottom)
        self.assertGreaterEqual(self.app.log.winfo_height(), 30)
        with patch("kks_installer.ui.save_language"):
            self.app.language_value.set("English")
            self.app.change_language()
        self.assertEqual(self.app.restore["text"], "Restore vanilla")
        self.assertEqual(self.app.selected, "digest")


if __name__ == "__main__":
    unittest.main()
