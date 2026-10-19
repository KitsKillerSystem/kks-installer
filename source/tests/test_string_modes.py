"""Exercise all 312 profiles against synthetic archives, with exact restoration."""

import base64
from copy import deepcopy
from itertools import product
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from kks_installer._application import CONTENT_LANGUAGES, FONT_LANGUAGES
from kks_installer.ba2 import BA2
from kks_installer.engine import digest
from kks_installer.equipment import CAPABILITY as EQUIPMENT, FULL, VANILLA, reset_equipment
from kks_installer.perks import CAPABILITY as PERKS, ON, OFF, reset_perks
from kks_installer.packages import LOCALIZATION, archive_members, import_package, validate_manifest
from kks_installer.platforms import SafetyError
from kks_installer.string_tables import read_table
from kks_installer import string_modes as modes
from mode_catalog import build_modes
from package_fixture import PackageFixture
from test_equipment import table
from test_perks import dl_table
from test_installer import archive


def fixture(base, lang="en", loose=False):
    fx = PackageFixture(base, multilingual=True, loose=loose)
    native = [(3, b""), (1, (lang + " Native weapon").encode()), (2, (lang + " Native armor").encode()),
              (4, b"Tea"), (5, b"Scrap"), (6, b"Heavy junk"), (7, b"\x10\r\n<mag>%")]
    canonical = [(sid, {1: b"KKS weapon", 2: b"KKS armor", 3: b"KKS naming", 4: b"V2 Tea",
                       5: b"Scrap [glyph]", 6: b"Heavy [glyph, 0,25 wt]"}.get(sid, value)) for sid, value in native]
    fx.native, fx.canonical = table(native), table(canonical)
    fx.categories = {"WEAP:FULL": [1], "ARMO:FULL": [2], "INNR:WNAM": [3]}
    fx.perk_native = dl_table([(10, (lang + " <mag>%\r\n<dur>").encode()), (20, b"\x10native"), (40, b"Other")])
    fx.perk_canonical = dl_table([(10, b"KKS panel"), (20, b"KKS panel2"), (40, b"Other")])
    fx.perk_categories = {"PERK:DESC": [10, 20]}
    loc = fx.game / LOCALIZATION
    original = BA2(loc)
    members = [(name, original.extract(name), True) for name in original.by_name]
    members += [(f"strings/seventysix_{lang}.strings", fx.native, True),
                (f"strings/seventysix_{lang}.dlstrings", fx.perk_native, True),
                (f"strings/seventysix_{lang}.ilstrings", fx.loose[f"Data/strings/seventysix_{lang}.ilstrings"], True)]
    archive(loc, members)
    fx.raw_originals[LOCALIZATION] = loc.read_bytes()
    for ext, raw in (("strings", fx.native), ("dlstrings", fx.perk_native)):
        target = f"Data/strings/seventysix_{lang}.{ext}"
        fx.loose[target] = raw
        if loose:
            (fx.game / target).write_bytes(raw)
    fx.original = fx.snapshot()
    path, m, payloads = fx.build(10, language=lang, translation_localization=True)
    for ext, raw in (("strings", fx.canonical), ("dlstrings", fx.perk_canonical)):
        p = f"payload/strings/seventysix_{lang}.{ext}"
        payloads[p] = raw
        next(f for f in m["files"] if f["path"] == p).update(sha256=digest(raw), size=len(raw))
        next(t for t in m["targets"] if t["kind"] == "loose" and t["payload"] == p).update(after_sha256=digest(raw), after_size=len(raw))
    # An old schema-1 package exercises upgrades into the new manager state.
    old = deepcopy(m)
    old.update(release_sequence=9, package_revision=1)
    fx.old_zip = fx.write(fx.base / "old.zip", old, payloads)
    m.update(schema=4, package_revision=2)
    m["required_capabilities"] = m["required_capabilities"] + [EQUIPMENT, PERKS]
    if lang == "ru":
        m["required_capabilities"].append("optional-features-ru-v1")
    if lang in ("de", "fr"):
        m["required_capabilities"].append("optional-features-fr-de-v1")
    if lang == "ptbr":
        m["required_capabilities"].append("optional-features-ptbr-v1")
    for key, algorithm, categories, derived in (
        ("equipment_naming", EQUIPMENT, fx.categories, reset_equipment(fx.canonical, fx.native, fx.categories)),
        ("perk_cards", PERKS, fx.perk_categories, reset_perks(fx.perk_canonical, fx.perk_native, fx.perk_categories))):
        m[key] = dict(algorithm=algorithm, categories=categories, sha256=digest(derived), size=len(derived))
    tables = {}
    for food, junk in product(modes.FOOD_PROFILES, modes.JUNK_PROFILES):
        changes = {}
        if food == "family-food":
            changes[4] = b"Family Tea"
        if junk == "text":
            changes.update({5: b"Scrap [Steel]", 6: b"Heavy [Steel, 0,25 wt]"})
        if junk == "none":
            changes.update({5: b"Scrap", 6: b"Heavy [0,25 wt]"})
        output = fx.base / (food + "-" + junk + ".strings")
        output.write_bytes(table([(sid, changes.get(sid, value)) for sid, value in canonical]))
        tables[(food, junk)] = output
    fx.tables = tables
    patch, option = build_modes(fx.canonical, fx.native, fx.categories, tables)
    m["string_modes"] = option
    m["required_capabilities"].append(modes.CAPABILITY)
    payloads[modes.PAYLOAD] = patch
    m["files"].append(dict(path=modes.PAYLOAD, sha256=digest(patch), size=len(patch)))
    fx.option_zip = fx.write(path, m, payloads)
    fx.option_manifest, fx.option_payloads = m, payloads
    return fx


class StringModesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)

    def test_all_312_profiles_switch_repair_restore_and_preserve_baseline(self):
        count = 0
        for lang in CONTENT_LANGUAGES:
            with self.subTest(language=lang):
                fx = fixture(self.base / lang, lang, loose=lang in ("fr", "ko"))
                manager = fx.manager()
                release = manager.select(fx.option_zip)
                baseline = None
                for naming, perks, food, junk in product((FULL, VANILLA), (ON, OFF), modes.FOOD_PROFILES, modes.JUNK_PROFILES):
                    before = fx.snapshot()
                    checked = manager.inspect(release, naming=naming, perks=perks, food=food, junk=junk)
                    self.assertEqual(before, fx.snapshot())
                    manager.run("install", release, naming=naming, perks=perks, food=food, junk=junk)
                    selected = release.with_features(naming=naming, perks=perks, food=food, junk=junk)
                    for ext in ("strings", "dlstrings"):
                        target = selected.by_path[f"Data/strings/seventysix_{lang}.{ext}"]
                        self.assertEqual(digest((fx.game / target["path"]).read_bytes()), target["after_sha256"])
                    rows = dict(read_table((fx.game / f"Data/strings/seventysix_{lang}.strings").read_bytes(), "strings"))
                    self.assertEqual(rows[7], b"\x10\r\n<mag>%")
                    self.assertEqual(rows[4], b"Family Tea" if food == "family-food" else b"V2 Tea")
                    self.assertEqual(rows[5], {"glyph": b"Scrap [glyph]", "text": b"Scrap [Steel]", "none": b"Scrap"}[junk])
                    self.assertIn(b"0,25", rows[6])
                    state = manager._read_state()
                    self.assertEqual(state["schema"], 8)
                    baseline = baseline or state["active"]["baseline"]
                    self.assertEqual(state["active"]["baseline"], baseline)
                    self.assertEqual((state["active"]["food"], state["active"]["junk"]), (food, junk))
                    count += 1
                for target in (f"Data/strings/seventysix_{lang}.strings", f"Data/strings/seventysix_{lang}.dlstrings"):
                    (fx.game / target).unlink()
                for path in release.folder.glob("derived/*"):
                    path.unlink()
                manager.run("repair")
                status = manager.inspect()
                self.assertEqual((status["installed_food"], status["installed_junk"]), ("family-food", "none"))
                # Baseline restoration does not depend on any cached content file.
                for item in release.files:
                    (release.folder / item).unlink()
                manager.run("restore")
                self.assertEqual(fx.snapshot(), fx.original)
                print(f"Validated 24 profiles, Repair and cacheless Restore: {lang}", flush=True)
        self.assertEqual(count, 312)

    def test_publisher_build_roundtrip_uses_signed_sparse_payload(self):
        from build_content import build
        fx = fixture(self.base, "zhhant")
        payload = self.base / "publisher-payload"
        for name, raw in fx.option_payloads.items():
            if name == modes.PAYLOAD:
                continue
            path = payload / name.removeprefix("payload/")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        with patch("build_content.load_key", return_value=(fx.key, "fixture")), \
             patch("equipment_catalog.equipment_categories", return_value=fx.categories), \
             patch("equipment_catalog.perk_categories", return_value=fx.perk_categories):
            result = build(fx.game, payload, self.base / "publisher.zip", self.base / "not-a-real-key",
                content_version="1.3.0", revision=1, sequence=20, baseline_id="matrix-fixture",
                build_label="fixture", report_id="unit", translation_localization=True,
                language="zhhant", equipment_naming=True, perk_cards=True, string_mode_tables=fx.tables)
        imported = import_package(result["package"], self.base / "roundtrip", fx.keys)
        self.assertEqual(imported.manifest["schema"], 4)
        self.assertEqual(len(imported.files), 7)
        self.assertEqual(len(imported.manifest["string_modes"]["outputs"]), 12)
        before = fx.snapshot()
        for food, junk in product(modes.FOOD_PROFILES, modes.JUNK_PROFILES):
            view = imported.with_features(food=food, junk=junk, naming=VANILLA, perks=OFF)
            view.prepare_features(fx.game)
            for ext in ("strings", "dlstrings"):
                item = view.files[f"payload/strings/seventysix_zhhant.{ext}"]
                self.assertEqual(digest(view.payload(item["path"], item["sha256"]).read_bytes()), item["sha256"])
        self.assertEqual(before, fx.snapshot())

    def test_upgrade_old_package_and_language_switch_requires_restore(self):
        fx = fixture(self.base, "ja")
        manager = fx.manager()
        old = manager.select(fx.old_zip)
        manager.run("install", old)
        baseline = manager._read_state()["active"]["baseline"]
        new = manager.select(fx.option_zip)
        manager.run("install", new, food="family-food", junk="text", perks=OFF)
        self.assertEqual(manager._read_state()["active"]["baseline"], baseline)
        english = manager.select(fx.build(2, language="en", translation_localization=True)[0])
        with self.assertRaisesRegex(SafetyError, "Restore Baseline before switching"):
            manager.run("install", english)
        manager.run("restore")
        self.assertEqual(fx.snapshot(), fx.original)

    def test_adverse_matrix_and_patch_cases_rejected(self):
        fx = fixture(self.base)
        for mutation in (lambda m: m["string_modes"]["outputs"].pop(),
                         lambda m: m["string_modes"]["outputs"].__setitem__(1, m["string_modes"]["outputs"][0]),
                         lambda m: m["string_modes"].__setitem__("payload", "../patch"),
                         lambda m: m.__setitem__("minimum_installer_version", "1.8.0")):
            candidate = deepcopy(fx.option_manifest)
            mutation(candidate)
            with self.assertRaises(SafetyError):
                validate_manifest(candidate)
        doc = json.loads(fx.option_payloads[modes.PAYLOAD])
        for mutation in (lambda d: d["food"]["family-food"].append(d["food"]["family-food"][0]),
                         lambda d: d["food"]["family-food"][0].__setitem__("id", 5),
                         lambda d: d["food"]["family-food"][0].__setitem__("id", 1),
                         lambda d: d["food"]["family-food"][0].__setitem__("value", "AA==")):
            candidate = deepcopy(doc)
            mutation(candidate)
            with self.assertRaises(SafetyError):
                modes.decode_patch(candidate, {1, 2, 3})

    def test_unsigned_or_tampered_output_is_blocked_before_game_writes(self):
        fx = fixture(self.base)
        m = deepcopy(fx.option_manifest)
        selected = next(o for o in m["string_modes"]["outputs"] if o["food"] == "family-food" and o["junk"] == "text" and o["naming"] == FULL)
        selected["sha256"] = "0" * 64
        candidate = fx.write(fx.base / "bad-output.zip", m, fx.option_payloads)
        manager = fx.manager()
        release = manager.select(candidate)
        before = fx.snapshot()
        with self.assertRaisesRegex(SafetyError, "signed checksum"):
            manager.run("install", release, food="family-food", junk="text")
        self.assertEqual(before, fx.snapshot())

    def test_interruption_recovers_valid_profile_and_exact_baseline(self):
        for checkpoint in ("after_restore_pending", "after_vanilla_committed", "file_replaced",
                           "engine_receipt_saved", "before_state_publish", "after_state_publish"):
            with self.subTest(checkpoint=checkpoint):
                fx = fixture(self.base / checkpoint)
                manager = fx.manager()
                release = manager.select(fx.option_zip)
                manager.run("install", release, food="family-food", junk="text")
                def interrupt(event, *args):
                    if event == checkpoint:
                        raise SystemExit("simulated termination")
                disrupted = fx.manager(event=interrupt)
                with self.assertRaises(SystemExit):
                    disrupted.run("install", release, food="food-v2", junk="none", naming=VANILLA, perks=OFF)
                manager.recover()
                active = manager._read_state()["active"]
                if active:
                    self.assertEqual(manager.inspect()["status"], "installed")
                    current = manager._release(active)
                    self.assertIn((current.food, current.junk), (("family-food", "text"), ("food-v2", "none")))
                    target = current.by_path["Data/strings/seventysix_en.strings"]
                    self.assertEqual(digest((fx.game / target["path"]).read_bytes()), target["after_sha256"])
                    manager.run("restore")
                self.assertEqual(fx.snapshot(), fx.original)

    def test_native_font_catalogs_are_fixed_by_application(self):
        fx = fixture(self.base, "ko")
        catalog = archive_members(fx.option_manifest["profile"])
        self.assertEqual(catalog["Data/SeventySix - Interface_ko.ba2"], ("interface/fonts_ko.swf",))
        self.assertNotIn("Data/SeventySix - Interface_en.ba2", catalog)

    def test_overlap_confirmation_is_bound_to_all_choices(self):
        from kks_installer.migration import consent_token
        fx = fixture(self.base)
        release = fx.manager().select(fx.option_zip)
        tokens = {consent_token(fx.game, release.with_features(naming=n, perks=p, food=f, junk=j), {})
                  for n, p, f, j in product((FULL, VANILLA), (ON, OFF), modes.FOOD_PROFILES, modes.JUNK_PROFILES)}
        self.assertEqual(len(tokens), 24)

    def test_missing_patch_id_is_rejected_during_package_import(self):
        fx = fixture(self.base)
        doc = json.loads(fx.option_payloads[modes.PAYLOAD])
        doc["food"]["family-food"][0]["id"] = 99999
        raw = json.dumps(doc).encode()
        m, payloads = deepcopy(fx.option_manifest), dict(fx.option_payloads)
        payloads[modes.PAYLOAD] = raw
        next(f for f in m["files"] if f["path"] == modes.PAYLOAD).update(sha256=digest(raw), size=len(raw))
        bad = fx.write(fx.base / "missing-id.zip", m, payloads)
        with self.assertRaisesRegex(SafetyError, "IDs are missing"):
            fx.manager().select(bad)

    def test_modified_cjk_font_requires_profile_bound_consent_and_restores(self):
        import os
        from certify_archives import certificate
        from kks_installer.migration import CATALOG
        fx = fixture(self.base, "ja")
        manager = fx.manager()
        release = manager.select(fx.option_zip)
        target = release.by_path["Data/SeventySix - Interface_ja.ba2"]
        original = fx.game / target["path"]
        cert = certificate(original, target)
        replacement = original.with_suffix(".new")
        BA2(original).replace_to(replacement, {"interface/fonts_ja.swf": b"previous font mod"})
        os.replace(replacement, original)
        before = fx.snapshot()
        with patch.dict(CATALOG, {target["vanilla_sha256"]: cert}):
            checked = manager.inspect(release, food="family-food", junk="text")
            self.assertIn("interface/fonts_ja.swf", checked["existing_modifications"])
            with self.assertRaisesRegex(SafetyError, "confirm the exact baseline"):
                manager.run("install", release, food="family-food", junk="none",
                            accept_modifications=checked["confirmation_token"])
            self.assertEqual(before, fx.snapshot())
            manager.run("install", release, food="family-food", junk="text",
                        accept_modifications=checked["confirmation_token"])
            manager.run("restore")
        self.assertEqual(before, fx.snapshot())


if __name__ == "__main__":
    unittest.main()
