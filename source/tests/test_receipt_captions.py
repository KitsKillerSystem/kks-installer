"""Persisted pre-1.10 captions remain bound to exact signed feature identities."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from kks_installer.ba2 import BA2, hash_file
from kks_installer.engine import digest
from kks_installer.platforms import SafetyError
from kks_installer import string_modes as modes
from test_installer import archive
from test_string_modes import fixture


class ReceiptCaptionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.fx = fixture(Path(self.temp.name))
        self.manager = self.fx.manager()
        self.release = self.manager.select(self.fx.option_zip)

    def install_historical(self, **options):
        # This is the exact FOOD_LABELS value at shipped source 13539b0.
        with patch.dict(modes.FOOD_LABELS, {"family-food": "Family Food"}):
            self.manager.run("install", self.release, food="family-food", **options)
        self.old_ref = self.manager._read_state()["active"]
        self.receipt_path = self.manager._engine(self.old_ref).receipt_path
        self.old_receipt = self.receipt_path.read_bytes()
        self.assertIn(b"Family Food", self.old_receipt)

    def updated_game(self):
        """A signed next baseline, including changed Localization/EXE/ESM."""
        fx = self.fx
        manifest = deepcopy(fx.option_manifest)
        manifest.update(release_sequence=11, package_revision=3)
        manifest["game"]["baseline_id"] = "next-native-baseline"
        for i, target in enumerate(manifest["targets"]):
            if target["kind"] != "archive":
                continue
            native = fx.base / ("new-native-" + str(i) + ".ba2")
            original = fx.base / ("old-native-" + str(i) + ".ba2")
            original.write_bytes(fx.raw_originals[target["path"]])
            source = BA2(original)
            archive(native, [(n, source.extract(n), True) for n in source.by_name]
                    + [("new-build-marker.bin", b"new build", False)])
            current = fx.game / target["path"]
            current.write_bytes(native.read_bytes())
            output = fx.base / ("new-output-" + str(i) + ".ba2")
            BA2(native).replace_to(output, {
                a["name"]: fx.option_payloads[a["payload"]] for a in target["assets"]})
            target.update(vanilla_sha256=hash_file(native), vanilla_size=native.stat().st_size,
                          after_sha256=hash_file(output), after_size=output.stat().st_size)
        for relative in ("Fallout76.exe", "Data/SeventySix.esm"):
            (fx.game / relative).write_bytes(("updated " + relative).encode())
        for item in manifest["game"]["identity"]:
            path = fx.game / item["path"]
            item.update(sha256=hash_file(path), size=path.stat().st_size)
        path = fx.write(fx.base / "next.zip", manifest, fx.option_payloads)
        return self.manager.select(path)

    def test_historical_caption_inspect_repair_cacheless_restore(self):
        self.install_historical(naming="vanilla-equipment", perks="off", junk="text")
        self.assertEqual(self.manager.inspect()["status"], "installed")
        self.assertEqual(self.receipt_path.read_bytes(), self.old_receipt)
        (self.fx.game / "Data/strings/seventysix_en.strings").unlink()
        self.manager.run("repair")
        self.assertEqual(self.manager.inspect()["installed_food"], "family-food")
        for relative in self.release.files:
            (self.release.folder / relative).unlink()
        self.manager.run("restore")
        self.assertEqual(self.fx.snapshot(), self.fx.original)

    def test_new_caption_still_accepted(self):
        self.manager.run("install", self.release, food="family-food", junk="none")
        engine = self.manager._engine(self.manager._read_state()["active"])
        self.assertIn("Abby's Style", engine._receipt()["release"])
        self.assertEqual(self.manager.inspect()["status"], "installed")

    def test_arbitrary_caption_and_wrong_food_view_fail_closed(self):
        self.install_historical()
        engine = self.manager._engine(self.old_ref)
        receipt = json.loads(self.old_receipt)
        for label in (None, [], "KKS 1.3.0", receipt["release"] + " extra",
                      receipt["release"].replace("Family Food", "Food V2"),
                      receipt["release"].replace("Family Food", "family food")):
            with self.subTest(label=label):
                changed = dict(receipt, release=label)
                with self.assertRaisesRegex(SafetyError, "content identity"):
                    engine._validate_receipt(changed)
        wrong = dict(self.old_ref, food="food-v2")
        with self.assertRaisesRegex(SafetyError, "content identity"):
            self.manager._engine(wrong)._validate_receipt(receipt)
        default = self.manager._engine(wrong)
        with self.assertRaises(SafetyError):
            default._validate_receipt(dict(receipt, release=default.release.name))
        changed = deepcopy(receipt)
        changed["files"]["Data/strings/seventysix_en.strings"]["after"] = "0" * 64
        with self.assertRaises(SafetyError):
            engine._validate_receipt(changed)
        self.assertEqual(self.receipt_path.read_bytes(), self.old_receipt)

    def test_historical_caption_in_interrupted_repair_journal_recovers(self):
        self.install_historical()
        installed = self.fx.snapshot()
        (self.fx.game / "Data/strings/seventysix_en.strings").unlink()

        def crash(event, data):
            if event == "file_replaced":
                raise SystemExit("interrupted repair")

        with self.assertRaises(SystemExit):
            self.fx.manager(event=crash).run("repair")
        self.fx.manager().recover()
        self.fx.manager().run("repair")
        self.assertEqual(self.fx.snapshot(), installed)
        self.fx.manager().run("restore")
        self.assertEqual(self.fx.snapshot(), self.fx.original)

    def test_real_sequence_new_baseline_recovery_repair_and_restore(self):
        self.install_historical()
        new = self.updated_game()
        expected = {p: h for p, h in self.fx.snapshot().items()
                    if p not in self.release.by_path or self.release.by_path[p]["kind"] != "loose"}
        with self.assertRaisesRegex(SafetyError, "Unsupported or changed game build"):
            self.manager.inspect()
        before = self.fx.snapshot()
        self.assertEqual(self.manager.inspect(new)["status"], "update_available")
        self.assertEqual(before, self.fx.snapshot())
        self.assertEqual(self.receipt_path.read_bytes(), self.old_receipt)

        def crash(event, data):
            if event == "override_retired":
                raise SystemExit("interrupted cleanup")

        with self.assertRaises(SystemExit):
            self.fx.manager(event=crash).run("install", new, food="family-food")
        self.fx.manager().recover()
        self.assertEqual(self.fx.snapshot(), expected)
        self.assertEqual(self.receipt_path.read_bytes(), self.old_receipt)
        self.fx.manager().run("install", new, food="family-food", junk="none")
        (self.fx.game / "Data/strings/seventysix_en.strings").unlink()
        self.fx.manager().run("repair")
        self.assertEqual(self.fx.manager().inspect()["installed_food"], "family-food")
        for relative in new.files:
            (new.folder / relative).unlink()
        self.fx.manager().run("restore")
        self.assertEqual(self.fx.snapshot(), expected)
        self.assertEqual(self.receipt_path.read_bytes(), self.old_receipt)

    def test_unknown_baseline_is_not_admitted_by_caption_compatibility(self):
        self.install_historical()
        new = self.updated_game()
        (self.fx.game / "Data/SeventySix - Localization.ba2").write_bytes(b"unknown archive")
        before = self.fx.snapshot()
        for operation in (lambda: self.manager.inspect(new),
                          lambda: self.manager.run("install", new),
                          lambda: self.manager.run("repair"),
                          lambda: self.manager.run("restore")):
            with self.assertRaises(SafetyError):
                operation()
            self.assertEqual(self.fx.snapshot(), before)
            self.assertEqual(self.receipt_path.read_bytes(), self.old_receipt)


if __name__ == "__main__":
    unittest.main()
