"""Compatibility proof, not a shipped upgrade feature.

A future installer can carry a trusted old manifest and restoration code,
without the old EXE or payload. The old receipt is never the trust anchor.
This adapter is deliberately limited to restoring the existing release.
"""

import json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from kks_installer.engine import Release, Installer, SafetyError, STATE, demand
from kks_installer.ba2 import hash_file
from test_installer import Fixture, BA2


class DescriptorOnlyRelease(Release):
    def verify_payloads(self):
        # Only RestoreOnlyInstaller may use this descriptor. Original bytes
        # come from individually verified backups, never release payloads.
        pass


class RestoreOnlyInstaller(Installer):
    def run(self, operation):
        demand(operation == "restore", "This compatibility proof permits restoration only")
        return super().run(operation)


class FutureRestoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.fx = Fixture(self.base)
        self.fx.engine.run("install")
        # Represents the descriptor and digest shipped by a trusted future
        # installer. Do not take expected_manifest from a user-editable receipt.
        self.catalog = self.base / "future-catalog"
        self.catalog.mkdir()
        (self.catalog / "manifest.json").write_bytes(
            (self.fx.release / "manifest.json").read_bytes()
        )
        self.trusted_pin = self.fx.spec.manifest_digest
        # No old payload directory is available to the compatibility reader.
        for p in self.fx.release.iterdir():
            p.unlink()
        self.fx.release.rmdir()
        self.old = RestoreOnlyInstaller(
            self.fx.root, DescriptorOnlyRelease(self.catalog, self.trusted_pin)
        )

    def tearDown(self):
        self.tmp.cleanup()

    def snapshot(self):
        return {
            p.relative_to(self.fx.root).as_posix(): hash_file(p)
            for p in self.fx.root.rglob("*")
            if p.is_file() and STATE not in p.parts
        }

    def refuses_without_game_writes(self, action=None):
        before = self.snapshot()
        with self.assertRaises(SafetyError):
            (action or (lambda: self.old.run("restore")))()
        self.assertEqual(before, self.snapshot())

    def test_restore_without_old_executable_or_payload_and_then_new_install(self):
        self.assertFalse(self.fx.release.exists())
        self.assertEqual(self.old.inspect()["status"], "installed")
        self.old.run("restore")
        self.assertEqual(self.fx.archive.read_bytes(), self.fx.original)
        self.assertFalse(self.fx.loose.exists())
        receipt = self.old.receipt_path.read_bytes()
        # A distinct new release is then certified against the restored baseline.
        release = self.base / "new-release"
        release.mkdir()
        m = json.loads((self.catalog / "manifest.json").read_bytes())
        m["release"] = "future test fixture"
        (release / "font.bin").write_bytes(b"future font fixture")
        (release / "strings.bin").write_bytes(b"future string fixture")
        staged = self.base / "future.ba2"
        BA2(self.fx.archive).replace_to(
            staged, {"interface/fonts_en.swf": (release / "font.bin").read_bytes()}
        )
        m["targets"][0]["after_sha256"] = hash_file(staged)
        m["targets"][0]["assets"][0]["sha256"] = hash_file(release / "font.bin")
        m["targets"][1]["after_sha256"] = hash_file(release / "strings.bin")
        (release / "manifest.json").write_text(json.dumps(m), "utf8")
        spec = Release(release, hash_file(release / "manifest.json"))
        with patch("kks_installer.engine.STATE", ".kks-future-test-only"):
            newer = Installer(self.fx.root, spec)
            self.assertEqual(newer.inspect()["status"], "ready")
            newer.run("install")
            self.assertEqual(newer.inspect()["status"], "installed")
            newer.run("restore")
        self.assertEqual(self.fx.archive.read_bytes(), self.fx.original)
        self.assertEqual(receipt, self.old.receipt_path.read_bytes())

    def test_updated_executable_blocks_stale_restore(self):
        (self.fx.root / "Fallout76.exe").write_bytes(b"new Bethesda executable")
        self.refuses_without_game_writes()

    def test_updated_esm_blocks_stale_restore(self):
        (self.fx.root / "Data/SeventySix.esm").write_bytes(b"new Bethesda ESM")
        self.refuses_without_game_writes()

    def test_updated_target_archive_blocks_stale_restore(self):
        self.fx.archive.write_bytes(self.fx.original + b"new Bethesda archive")
        self.refuses_without_game_writes()

    def test_damaged_backup_blocks_restore(self):
        backup = (
            self.fx.root / STATE / "backups" / f"{self.fx.spec.targets[0]['vanilla_sha256']}.bin"
        )
        backup.write_bytes(b"damaged")
        self.refuses_without_game_writes()

    def test_missing_backup_blocks_restore(self):
        backup = (
            self.fx.root / STATE / "backups" / f"{self.fx.spec.targets[0]['vanilla_sha256']}.bin"
        )
        backup.unlink()
        self.refuses_without_game_writes()

    def test_unknown_receipt_manifest_blocks_restore(self):
        p = self.old.receipt_path
        m = json.loads(p.read_bytes())
        m["manifest"] = "0" * 64
        p.write_text(json.dumps(m))
        self.refuses_without_game_writes()

    def test_receipt_cannot_select_arbitrary_backup(self):
        p = self.old.receipt_path
        m = json.loads(p.read_bytes())
        m["files"][self.fx.spec.targets[0]["path"]]["before"] = "0" * 64
        p.write_text(json.dumps(m))
        self.refuses_without_game_writes()

    def test_tampered_catalog_rejected_against_trusted_pin(self):
        (self.catalog / "manifest.json").write_text("{}")
        self.refuses_without_game_writes(
            lambda: DescriptorOnlyRelease(self.catalog, self.trusted_pin)
        )

    def test_restore_only_adapter_rejects_install_and_repair(self):
        for op in ["install", "repair"]:
            self.refuses_without_game_writes(lambda: self.old.run(op))

    def test_interrupted_restore_recovers_without_payload(self):
        before = self.snapshot()

        def crash(index, entry):
            raise SystemExit("interrupted restore")

        self.old._after_replace = crash
        with self.assertRaises(SystemExit):
            self.old.run("restore")
        self.assertEqual(self.old.recover()["status"], "recovered")
        self.assertEqual(before, self.snapshot())
        self.old._after_replace = lambda *args: None
        self.old.run("restore")
        self.assertEqual(self.fx.archive.read_bytes(), self.fx.original)


if __name__ == "__main__":
    unittest.main(verbosity=2)
