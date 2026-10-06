"""Independent perk/equipment combinations, upgrade, restoration and trust boundaries."""

from copy import deepcopy
from pathlib import Path
import json
import struct
import tempfile
import unittest
import zlib

from equipment_catalog import perk_categories
from kks_installer.ba2 import BA2
from kks_installer.engine import digest
from kks_installer.equipment import FULL, VANILLA
from kks_installer.perks import ON, OFF, CAPABILITY, reset_perks
from kks_installer.string_tables import read_table
from kks_installer.packages import LOCALIZATION, TRANSLATION, validate_manifest
from kks_installer.platforms import SafetyError
from test_installer import archive
from test_equipment import fixture as equipment_fixture, TARGET as EQUIPMENT, PAYLOAD as EQUIPMENT_PAYLOAD

TARGET = "Data/strings/seventysix_en.dlstrings"
PAYLOAD = "payload/strings/seventysix_en.dlstrings"


def dl_table(rows):
    pool, directory = b"", b""
    for sid, value in rows:
        directory += struct.pack("<II", sid, len(pool))
        pool += struct.pack("<I", len(value) + 1) + value + b"\0"
    return struct.pack("<II", len(rows), len(pool)) + directory + pool


def fixture(base, loose=False):
    fx = equipment_fixture(base, loose=loose)
    native = [(50, b"Native armor"), (10, b"Deal <mag>%\r\n<dur> seconds"),
              (20, b"\x10Native perk"), (30, b""), (40, b"Keep native")]
    canonical = [(50, b"KKS armor description"), (10, b"KKS panel 1"),
                 (20, b"KKS panel 2"), (30, b""), (40, b"Keep native")]
    expected = [(sid, dict(native)[sid] if sid in (10, 20, 30) else value)
                for sid, value in canonical]
    fx.perk_native, fx.perk_canonical, fx.perk_expected = map(dl_table, (native, canonical, expected))
    loc = fx.game / LOCALIZATION
    translation = BA2(loc).extract(TRANSLATION)
    archive(loc, [(TRANSLATION, translation, True),
                  ("strings/seventysix_en.strings", fx.native, True),
                  ("strings/seventysix_en.dlstrings", fx.perk_native, True),
                  ("untouched.bin", b"unrelated archive bytes", True)])
    fx.raw_originals[LOCALIZATION] = loc.read_bytes()
    fx.loose[TARGET] = fx.perk_native
    if loose:
        (fx.game / TARGET).write_bytes(fx.perk_native)
    fx.original = fx.snapshot()
    path, m, payloads = fx.build(3, translation_localization=True)
    for target, payload, raw in ((EQUIPMENT, EQUIPMENT_PAYLOAD, fx.canonical),
                                 (TARGET, PAYLOAD, fx.perk_canonical)):
        payloads[payload] = raw
        next(f for f in m["files"] if f["path"] == payload).update(sha256=digest(raw), size=len(raw))
        next(t for t in m["targets"] if t["path"] == target).update(after_sha256=digest(raw), after_size=len(raw))
    m["schema"] = 3
    m["equipment_naming"] = deepcopy(fx.option_manifest["equipment_naming"])
    m["required_capabilities"] = m["required_capabilities"] + [m["equipment_naming"]["algorithm"], CAPABILITY]
    m["perk_cards"] = dict(algorithm=CAPABILITY, categories={"PERK:DESC": [10, 20, 30]},
                            sha256=digest(fx.perk_expected), size=len(fx.perk_expected))
    fx.write(path, m, payloads)
    old = deepcopy(m)
    old.update(schema=2, release_sequence=2, content_version="1.1.0")
    del old["perk_cards"]
    old["required_capabilities"].remove(CAPABILITY)
    fx.equipment_zip = fx.write(fx.base / "equipment-only.zip", old, payloads)
    fx.option_zip, fx.option_manifest, fx.option_payloads = path, m, payloads
    return fx


class PerkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.fx = fixture(self.base)
        self.manager = self.fx.manager()
        self.release = self.manager.select(self.fx.option_zip)

    def assert_installed(self, naming, perks):
        self.assertEqual((self.fx.game / EQUIPMENT).read_bytes(),
                         self.fx.canonical if naming == FULL else self.fx.expected)
        self.assertEqual((self.fx.game / TARGET).read_bytes(),
                         self.fx.perk_canonical if perks == ON else self.fx.perk_expected)
        current = self.manager.inspect()
        self.assertEqual((current["installed_naming"], current["installed_perks"]), (naming, perks))
        self.assertEqual(current["status"], "installed")

    def test_exact_category_scope_raw_placeholders_and_noop(self):
        categories = self.release.manifest["perk_cards"]["categories"]
        result = reset_perks(self.fx.perk_canonical, self.fx.perk_native, categories)
        self.assertEqual(result, self.fx.perk_expected)
        rows = dict(read_table(result, "dlstrings"))
        self.assertEqual(rows[10], b"Deal <mag>%\r\n<dur> seconds")
        self.assertEqual(rows[20], b"\x10Native perk")
        self.assertEqual(rows[50], b"KKS armor description")
        self.assertEqual(reset_perks(result, self.fx.perk_native, categories), result)

    def test_all_four_choices_are_independent_and_same_package_switchable(self):
        for naming, perks in ((FULL, ON), (FULL, OFF), (VANILLA, OFF), (VANILLA, ON), (FULL, ON)):
            self.manager.run("install", self.release, naming=naming, perks=perks)
            self.assert_installed(naming, perks)
            state = self.manager._read_state()
            self.assertEqual(state["schema"], 6)
            self.assertEqual(state["highest_sequence"], 3)
            self.assertEqual(state["active"]["manifest"], self.release.manifest_digest)
            self.assertEqual((self.release.folder / PAYLOAD).read_bytes(), self.fx.perk_canonical)
            self.assertEqual((self.release.folder / EQUIPMENT_PAYLOAD).read_bytes(), self.fx.canonical)
        self.manager.run("restore")
        self.assertEqual(self.fx.snapshot(), self.fx.original)

    def test_upgrade_equipment_only_history_and_views_retain_other_choice(self):
        previous = self.manager.select(self.fx.equipment_zip)
        self.manager.run("install", previous, naming=VANILLA)
        self.assertEqual(self.manager._read_state()["schema"], 5)
        alternate = self.release.with_perks(OFF).with_naming(VANILLA)
        self.assertEqual(alternate.with_naming(FULL).perks, OFF)
        self.assertEqual(alternate.with_perks(ON).naming, VANILLA)
        self.manager.run("install", alternate)
        self.assert_installed(VANILLA, OFF)
        self.manager.run("restore")
        self.assertEqual(self.fx.snapshot(), self.fx.original)

    def test_check_is_read_only_and_counts_independent_changed_files(self):
        self.manager.run("install", self.release)
        before = {str(p): digest(p.read_bytes()) for p in self.fx.game.rglob("*") if p.is_file()}
        for naming, perks, count in ((FULL, OFF, 1), (VANILLA, ON, 1), (VANILLA, OFF, 2)):
            result = self.manager.inspect(self.release, naming=naming, perks=perks)
            self.assertEqual(result["status"], "update_available")
            self.assertEqual(result["changed_payload_files"], count)
        after = {str(p): digest(p.read_bytes()) for p in self.fx.game.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_repair_retains_both_choices_and_regenerates_both_tables(self):
        self.manager.run("install", self.release, naming=VANILLA, perks=OFF)
        for target in (TARGET, EQUIPMENT):
            (self.fx.game / target).unlink()
        for path in ("derived/vanilla-equipment.strings", "derived/vanilla-perks.dlstrings"):
            (self.release.folder / path).write_bytes(b"damaged cache")
        self.manager.run("repair", naming=FULL, perks=ON)
        self.assert_installed(VANILLA, OFF)
        (self.release.folder / PAYLOAD).write_bytes(b"damaged canonical")
        before = self.fx.snapshot()
        with self.assertRaises(SafetyError):
            self.manager.run("repair")
        self.assertEqual(self.fx.snapshot(), before)
        self.manager.select(self.fx.option_zip)
        self.manager.run("repair")
        self.assert_installed(VANILLA, OFF)

    def test_cache_free_restore_preserves_absence_and_existing_loose_files(self):
        for loose in (False, True):
            sub = self.base / str(loose)
            sub.mkdir()
            fx = fixture(sub, loose=loose)
            manager = fx.manager()
            release = manager.select(fx.option_zip)
            manager.run("install", release, naming=VANILLA, perks=OFF)
            for path in release.files:
                (release.folder / path).unlink()
            for path in ("derived/vanilla-equipment.strings", "derived/vanilla-perks.dlstrings"):
                (release.folder / path).unlink()
            fx.option_zip.unlink()
            self.assertFalse(manager.inspect()["repair_available"])
            manager.run("restore")
            self.assertEqual(fx.snapshot(), fx.original)

    def test_bad_signed_perk_hash_fails_before_game_transaction(self):
        self.manager.run("install", self.release)
        m = deepcopy(self.fx.option_manifest)
        m.update(release_sequence=4, package_revision=2)
        m["perk_cards"]["sha256"] = "0" * 64
        bad = self.manager.select(self.fx.write(self.base / "bad.zip", m, self.fx.option_payloads))
        before = self.fx.snapshot()
        with self.assertRaises(SafetyError):
            self.manager.run("install", bad, naming=VANILLA, perks=OFF)
        self.assertEqual(self.fx.snapshot(), before)
        self.assertFalse(self.manager.saved("pending.json").exists())

    def test_invalid_metadata_and_unsupported_packages_are_rejected(self):
        for mutate in (
            lambda m: m["perk_cards"].update(algorithm="other"),
            lambda m: m["perk_cards"]["categories"].update({"PERK:DESC": [0]}),
            lambda m: m["perk_cards"]["categories"].update({"PERK:DESC": [20, 10]}),
            lambda m: m["perk_cards"]["categories"].update({"PERK:DESC": [10, 10]}),
            lambda m: m["perk_cards"]["categories"].update({"PERK:DESC": []}),
            lambda m: m["perk_cards"]["categories"].update({"PERK:FULL": [10]}),
            lambda m: m.update(minimum_installer_version="1.4.0"),
            lambda m: m.update(schema=2),
        ):
            value = deepcopy(self.fx.option_manifest)
            mutate(value)
            with self.assertRaises(SafetyError):
                validate_manifest(value)
        with self.assertRaises(SafetyError):
            self.release.with_perks("unknown")
        with self.assertRaises(SafetyError):
            self.manager.select(self.fx.equipment_zip).with_perks(OFF)

    def test_saved_choice_tampering_is_not_accepted(self):
        self.manager.run("install", self.release, perks=OFF)
        path = self.manager.saved("installation.json")
        original = json.loads(path.read_bytes())
        for mutate in (lambda ref: ref.update(perks=ON), lambda ref: ref.pop("perks"),
                       lambda ref: ref.update(perks="unknown")):
            state = deepcopy(original)
            mutate(state["active"])
            path.write_text(json.dumps(state))
            with self.assertRaises(SafetyError):
                self.manager.run("restore")
        path.write_text(json.dumps(original))
        self.manager.run("restore")

    def test_interrupted_switches_recover_both_feature_choices(self):
        for previous, following in (((FULL, ON), (VANILLA, OFF)), ((VANILLA, OFF), (FULL, ON))):
            for checkpoint in ("after_restore_pending", "after_vanilla_committed", "file_replaced",
                               "engine_receipt_saved", "before_state_publish", "after_state_publish"):
                with self.subTest(previous=previous, checkpoint=checkpoint):
                    sub = self.base / ("interrupt" + str(len(list(self.base.iterdir()))))
                    sub.mkdir()
                    fx = fixture(sub)
                    manager = fx.manager()
                    release = manager.select(fx.option_zip)
                    manager.run("install", release, naming=previous[0], perks=previous[1])
                    def stop(name, data):
                        if name == checkpoint:
                            raise SystemExit("interrupted feature switch")
                    manager.event = stop
                    with self.assertRaises(SystemExit):
                        manager.run("install", release, naming=following[0], perks=following[1])
                    fresh = fx.manager()
                    fresh.recover()
                    if fresh._read_state()["active"]:
                        self.assertEqual(fresh.inspect()["status"], "installed")
                        fresh.run("restore")
                    self.assertEqual(fx.snapshot(), fx.original)

    def test_malformed_dlstrings_and_missing_ids(self):
        malformed = [b"", struct.pack("<II", 1, 1), dl_table([(1, b"a"), (1, b"b")]),
                     dl_table([(1, b"a\0b")])]
        valid = dl_table([(1, b"abc")])
        for length in (0, 2, 99):
            raw = bytearray(valid)
            struct.pack_into("<I", raw, 16, length)
            malformed.append(bytes(raw))
        for raw in malformed:
            with self.assertRaises(SafetyError):
                read_table(raw, "dlstrings")
        with self.assertRaises(SafetyError):
            reset_perks(self.fx.perk_canonical, dl_table([(10, b"native")]),
                        self.release.manifest["perk_cards"]["categories"])

    def test_esm_discovers_all_desc_ignores_full_epf2_and_zero(self):
        raw = b"".join(name + struct.pack("<HI", 4, sid) for name, sid in
                       ((b"FULL", 1), (b"DESC", 10), (b"DESC", 20), (b"DESC", 0), (b"EPF2", 2)))
        packed = struct.pack("<I", len(raw)) + zlib.compress(raw)
        record = struct.pack("<4sIIIIHH", b"PERK", len(packed), 0x40000, 1, 0, 0, 0) + packed
        group = struct.pack("<4sI4sIII", b"GRUP", len(record) + 24, b"PERK", 0, 0, 0) + record
        path = self.base / "perks.esm"
        path.write_bytes(group)
        self.assertEqual(perk_categories(path), {"PERK:DESC": [10, 20]})


if __name__ == "__main__":
    unittest.main()
