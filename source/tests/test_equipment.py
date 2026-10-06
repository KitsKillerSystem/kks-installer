"""Profile transitions, exact scope, trust failures and interrupted recovery."""

from copy import deepcopy
from pathlib import Path
import json
import struct
import tempfile
import unittest
import zlib

from equipment_catalog import equipment_categories
from kks_installer.ba2 import BA2, hash_file
from kks_installer.engine import digest
from kks_installer.equipment import FULL, VANILLA, CAPABILITY, CATEGORIES, read_strings, reset_equipment
from kks_installer.packages import LOCALIZATION, TRANSLATION, validate_manifest
from kks_installer.platforms import SafetyError
from package_fixture import PackageFixture
from test_installer import archive

TARGET = "Data/strings/seventysix_en.strings"
PAYLOAD = "payload/strings/seventysix_en.strings"


def table(rows):
    pool = b""
    directory = b""
    for sid, value in rows:
        directory += struct.pack("<II", sid, len(pool))
        pool += value + b"\0"
    return struct.pack("<II", len(rows), len(pool)) + directory + pool


def fixture(base, loose=False):
    fx = PackageFixture(base, loose=loose)
    native = [(3, b""), (1, b"Axe"), (2, b"Armor"), (4, b"Perk"), (5, b"\x10\r\nuntouched")]
    canonical = [(3, b"KKS rule"), (1, b"KKS Axe"), (2, b"KKS Armor"),
                 (4, b"KKS Perk"), (5, b"\x10\r\nuntouched")]
    fx.native, fx.canonical = table(native), table(canonical)
    fx.expected = table([(sid, dict(native)[sid] if sid in (1, 2, 3) else value)
                         for sid, value in canonical])
    loc = fx.game / LOCALIZATION
    translation = BA2(loc).extract(TRANSLATION)
    archive(loc, [(TRANSLATION, translation, True),
                  ("strings/seventysix_en.strings", fx.native, True),
                  ("untouched.bin", b"keep every unrelated archive member", True)])
    fx.raw_originals[LOCALIZATION] = loc.read_bytes()
    fx.loose[TARGET] = fx.native
    if loose:
        (fx.game / TARGET).write_bytes(fx.native)
    fx.original = fx.snapshot()
    path, manifest, payloads = fx.build(2, translation_localization=True)
    payloads[PAYLOAD] = fx.canonical
    next(f for f in manifest["files"] if f["path"] == PAYLOAD).update(
        sha256=digest(fx.canonical), size=len(fx.canonical))
    next(t for t in manifest["targets"] if t["path"] == TARGET).update(
        after_sha256=digest(fx.canonical), after_size=len(fx.canonical))
    manifest["schema"] = 2
    manifest["required_capabilities"] = manifest["required_capabilities"] + [CAPABILITY]
    manifest["equipment_naming"] = dict(algorithm=CAPABILITY,
        categories=dict(zip(CATEGORIES, [[1], [2], [3]])),
        sha256=digest(fx.expected), size=len(fx.expected))
    fx.write(path, manifest, payloads)
    fx.option_zip, fx.option_manifest, fx.option_payloads = path, manifest, payloads
    return fx


class EquipmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.fx = fixture(self.base)
        self.manager = self.fx.manager()
        self.release = self.manager.select(self.fx.option_zip)

    def test_exact_scope_and_raw_bytes(self):
        result = reset_equipment(self.fx.canonical, self.fx.native,
                                 self.release.manifest["equipment_naming"]["categories"])
        self.assertEqual(result, self.fx.expected)
        self.assertEqual(dict(read_strings(result))[5], b"\x10\r\nuntouched")
        self.assertEqual(dict(read_strings(result))[4], b"KKS Perk")

    def test_full_alternate_full_and_restore_without_new_sequence(self):
        for naming, expected in ((FULL, self.fx.canonical), (VANILLA, self.fx.expected),
                                 (FULL, self.fx.canonical), (VANILLA, self.fx.expected)):
            state = self.manager.inspect(self.release, naming=naming)
            self.assertIn(state["status"], ("ready", "update_available"))
            self.manager.run("install", self.release, naming=naming)
            self.assertEqual((self.fx.game / TARGET).read_bytes(), expected)
            self.assertEqual(self.manager.inspect()["installed_naming"], naming)
            self.assertEqual(self.manager._read_state()["highest_sequence"], 2)
            self.assertEqual((self.release.folder / PAYLOAD).read_bytes(), self.fx.canonical)
        self.assertEqual(self.manager._read_state()["schema"], 5)
        self.manager.run("restore")
        self.assertEqual(self.fx.snapshot(), self.fx.original)

    def test_restore_preserves_original_presence(self):
        sub = self.base / "present"
        sub.mkdir()
        fx = fixture(sub, loose=True)
        manager = fx.manager()
        manager.run("install", manager.select(fx.option_zip), naming=VANILLA)
        manager.run("restore")
        self.assertEqual(fx.snapshot(), fx.original)

    def test_restore_without_any_payload_or_derived_cache(self):
        self.manager.run("install", self.release, naming=VANILLA)
        for relative in self.release.files:
            (self.release.folder / relative).unlink()
        (self.release.folder / "derived/vanilla-equipment.strings").unlink()
        self.fx.option_zip.unlink()
        self.assertFalse(self.manager.inspect()["repair_available"])
        self.assertTrue(self.manager.inspect()["restore_available"])
        self.manager.run("restore")
        self.assertEqual(self.fx.snapshot(), self.fx.original)

    def test_repair_retains_profile_and_rebuilds_derived_cache(self):
        self.manager.run("install", self.release, naming=VANILLA)
        (self.fx.game / TARGET).unlink()
        (self.release.folder / "derived/vanilla-equipment.strings").write_bytes(b"damaged")
        self.manager.run("repair", naming=FULL)
        self.assertEqual((self.fx.game / TARGET).read_bytes(), self.fx.expected)
        (self.release.folder / PAYLOAD).write_bytes(b"damaged canonical")
        before = self.fx.snapshot()
        with self.assertRaises(SafetyError):
            self.manager.run("repair")
        self.assertEqual(self.fx.snapshot(), before)
        self.manager.select(self.fx.option_zip)
        self.manager.run("repair")

    def test_inspect_is_read_only_and_compares_effective_payloads(self):
        self.manager.run("install", self.release)
        before = {str(p): digest(p.read_bytes()) for p in self.fx.game.rglob("*") if p.is_file()}
        result = self.manager.inspect(self.release, naming=VANILLA)
        self.assertEqual(result["status"], "update_available")
        self.assertEqual(result["changed_payload_files"], 1)
        after = {str(p): digest(p.read_bytes()) for p in self.fx.game.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_wrong_signed_output_stops_before_removing_installed_content(self):
        self.manager.run("install", self.release)
        bad = deepcopy(self.fx.option_manifest)
        bad["release_sequence"] = 3
        bad["package_revision"] = 2
        bad["equipment_naming"]["sha256"] = "0" * 64
        path = self.fx.write(self.base / "bad.zip", bad, self.fx.option_payloads)
        selected = self.manager.select(path)
        before = self.fx.snapshot()
        with self.assertRaises(SafetyError):
            self.manager.run("install", selected, naming=VANILLA)
        self.assertEqual(self.fx.snapshot(), before)
        self.assertFalse(self.manager.saved("pending.json").exists())

    def test_invalid_profile_or_category_metadata_refused(self):
        for change in (
            lambda m: m["equipment_naming"].update(algorithm="other"),
            lambda m: m["equipment_naming"]["categories"].update({"ARMO:FULL": [1]}),
            lambda m: m["equipment_naming"]["categories"].update({"WEAP:FULL": [0]}),
            lambda m: m["equipment_naming"]["categories"].update({"WEAP:FULL": []}),
            lambda m: m.update(minimum_installer_version="1.3.1"),
        ):
            value = deepcopy(self.fx.option_manifest)
            change(value)
            with self.assertRaises(SafetyError):
                validate_manifest(value)
        with self.assertRaises(SafetyError):
            self.release.with_naming("unknown")
        old = self.manager.select(self.fx.a)
        with self.assertRaises(SafetyError):
            old.with_naming(VANILLA)

    def test_tampered_saved_profile_is_not_accepted_as_full(self):
        self.manager.run("install", self.release, naming=VANILLA)
        path = self.manager.saved("installation.json")
        state = json.loads(path.read_bytes())
        state["active"]["naming"] = FULL
        path.write_text(json.dumps(state))
        with self.assertRaises(SafetyError):
            self.manager.run("restore")

    def test_foreign_file_and_updated_game_refuse_switch_and_restore(self):
        self.manager.run("install", self.release, naming=VANILLA)
        for path in (TARGET, "Data/SeventySix.esm"):
            original = (self.fx.game / path).read_bytes()
            (self.fx.game / path).write_bytes(b"foreign bytes")
            before = self.fx.snapshot()
            for action in ("install", "restore"):
                with self.assertRaises(SafetyError):
                    self.manager.run(action, self.release)
                self.assertEqual(self.fx.snapshot(), before)
            (self.fx.game / path).write_bytes(original)

    def test_interrupted_switches_recover_with_profile_bound_hashes(self):
        for previous, following in ((FULL, VANILLA), (VANILLA, FULL)):
            for checkpoint in ("after_restore_pending", "after_vanilla_committed", "file_replaced",
                               "engine_receipt_saved", "before_state_publish", "after_state_publish"):
                with self.subTest(previous=previous, checkpoint=checkpoint):
                    sub = self.base / ("c" + str(len(list(self.base.iterdir()))))
                    sub.mkdir()
                    fx = fixture(sub)
                    manager = fx.manager()
                    release = manager.select(fx.option_zip)
                    manager.run("install", release, naming=previous)
                    def stop(name, data):
                        if name == checkpoint:
                            raise SystemExit("interrupted profile switch")
                    manager.event = stop
                    with self.assertRaises(SystemExit):
                        manager.run("install", release, naming=following)
                    fresh = fx.manager()
                    fresh.recover()
                    if fresh._read_state()["active"]:
                        self.assertEqual(fresh.inspect()["status"], "installed")
                        fresh.run("restore")
                    self.assertEqual(fx.snapshot(), fx.original)

    def test_malformed_and_missing_string_entries_refused(self):
        categories = self.fx.option_manifest["equipment_naming"]["categories"]
        for raw in (b"", struct.pack("<II", 1, 1), table([(1, b"a"), (1, b"b")])):
            with self.assertRaises(SafetyError):
                read_strings(raw)
        with self.assertRaises(SafetyError):
            reset_equipment(self.fx.canonical, table([(1, b"Axe")]), categories)

    def test_esm_discovery_includes_nested_fulls_rules_and_compressed_records(self):
        def field(name, value):
            return name + struct.pack("<H", len(value)) + value
        def record(sig, values, compressed=False):
            raw = b"".join(field(name, struct.pack("<I", sid)) for name, sid in values)
            if compressed:
                raw = struct.pack("<I", len(raw)) + zlib.compress(raw)
            return struct.pack("<4sIIIIHH", sig, len(raw), 0x40000 if compressed else 0, 1, 0, 0, 0) + raw
        def group(sig, body):
            return struct.pack("<4sI4sIII", b"GRUP", 24 + len(body), sig, 0, 0, 0) + body
        raw = group(b"WEAP", record(b"WEAP", [(b"FULL", 1), (b"DESC", 99), (b"FULL", 11)], True))
        raw += group(b"ARMO", record(b"ARMO", [(b"FULL", 2)]))
        raw += group(b"INNR", record(b"INNR", [(b"WNAM", 3), (b"WNAM", 0), (b"WNAM", 3)]))
        path = self.base / "source.esm"
        path.write_bytes(raw)
        self.assertEqual(equipment_categories(path), dict(zip(CATEGORIES, [[1, 11], [2], [3]])))
        path.write_bytes(raw[:-1])
        with self.assertRaises(SafetyError):
            equipment_categories(path)


if __name__ == "__main__":
    unittest.main()
