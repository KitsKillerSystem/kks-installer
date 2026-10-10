"""Russian options use native RU bytes and retain the original installation baseline."""
from copy import deepcopy
from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch

from certify_archives import certificate
from kks_installer._application import RUSSIAN_OPTIONAL_CAPABILITY
from kks_installer.ba2 import BA2
from kks_installer.engine import digest
from kks_installer.equipment import CAPABILITY, FULL, VANILLA
from kks_installer.perks import CAPABILITY as PERK_CAPABILITY, ON, OFF
from kks_installer.migration import CATALOG
from kks_installer.packages import CONFIG, LOCALIZATION, validate_manifest
from kks_installer.platforms import SafetyError
from kks_installer.string_tables import read_table
from package_fixture import PackageFixture
from test_installer import archive
from test_equipment import table
from test_perks import dl_table

EQUIPMENT = 'Data/strings/seventysix_ru.strings'
PERKS = 'Data/strings/seventysix_ru.dlstrings'


def fixture(base, loose=False):
    fx = PackageFixture(base, multilingual=True, loose=loose)
    ru = lambda value: value.encode('utf-8')
    native = [(3, b''), (1, ru('Топор')), (2, ru('Броня')), (4, ru('Название карты'))]
    canonical = [(3, b'KKS rule'), (1, ru('KKS Топор')), (2, ru('KKS Броня')),
                 (4, ru('KKS Название карты'))]
    fx.native = table(native)
    fx.canonical = table(canonical)
    fx.expected = table([(sid, dict(native)[sid] if sid in (1, 2, 3) else value)
                         for sid, value in canonical])
    native_perks = [(10, ru('Урон <mag>%\r\n<dur> сек.')), (20, b'\x10' + ru('Условие')),
                    (30, b''), (40, ru('Другой эффект'))]
    canonical_perks = [(10, ru('\uea00\uea01')), (20, ru('\uea02')), (30, b''),
                       (40, ru('KKS Другой эффект'))]
    fx.perk_native = dl_table(native_perks)
    fx.perk_canonical = dl_table(canonical_perks)
    fx.perk_expected = dl_table([(sid, dict(native_perks)[sid] if sid in (10, 20, 30) else value)
                               for sid, value in canonical_perks])
    loc = fx.game / LOCALIZATION
    original = BA2(loc)
    members = [(name, original.extract(name), True) for name in original.by_name]
    # Valid English tables with the SAME IDs expose any accidental English lookup.
    members += [('strings/seventysix_en.strings', table([(i, b'EN') for i, _ in native]), True),
                ('strings/seventysix_en.dlstrings', dl_table([(i, b'EN') for i, _ in native_perks]), True),
                ('strings/seventysix_ru.strings', fx.native, True),
                ('strings/seventysix_ru.dlstrings', fx.perk_native, True)]
    archive(loc, members)
    fx.raw_originals[LOCALIZATION] = loc.read_bytes()
    for target, raw in ((EQUIPMENT, fx.native), (PERKS, fx.perk_native)):
        fx.loose[target] = raw
        if loose:
            (fx.game / target).write_bytes(raw)
    fx.original = fx.snapshot()
    path, m, payloads = fx.build(10, language='ru')
    for target, raw in ((EQUIPMENT, fx.canonical), (PERKS, fx.perk_canonical)):
        payload = 'payload/' + target[5:]
        payloads[payload] = raw
        next(f for f in m['files'] if f['path'] == payload).update(sha256=digest(raw), size=len(raw))
        next(t for t in m['targets'] if t['path'] == target).update(after_sha256=digest(raw), after_size=len(raw))
    old = deepcopy(m)
    old.update(release_sequence=9, package_revision=1)
    fx.old_zip = fx.write(fx.base / 'b008.zip', old, payloads)
    m.update(schema=3, package_revision=2)
    m['required_capabilities'] += [CAPABILITY, PERK_CAPABILITY, RUSSIAN_OPTIONAL_CAPABILITY]
    m['equipment_naming'] = dict(algorithm=CAPABILITY,
        categories={'WEAP:FULL': [1], 'ARMO:FULL': [2], 'INNR:WNAM': [3]},
        sha256=digest(fx.expected), size=len(fx.expected))
    m['perk_cards'] = dict(algorithm=PERK_CAPABILITY, categories={'PERK:DESC': [10, 20, 30]},
                         sha256=digest(fx.perk_expected), size=len(fx.perk_expected))
    fx.option_zip = fx.write(path, m, payloads)
    fx.option_manifest, fx.option_payloads = m, payloads
    return fx


class RussianModularityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)

    def modified(self, fx, release):
        certs = {t['vanilla_sha256']: certificate(fx.game / t['path'], t)
                 for t in release.targets if t['kind'] == 'archive' and t['path'] != LOCALIZATION}
        self.enterContext(patch.dict(CATALOG, certs))
        src = fx.game / CONFIG
        dst = src.with_suffix('.new')
        BA2(src).replace_to(dst, {'interface/fontconfig_ru.txt': b'prior RU config',
                                 'untouched.dat': b'prior unrelated mod'})
        os.replace(dst, src)

    def assert_choices(self, fx, manager, naming, perks):
        self.assertEqual((fx.game / EQUIPMENT).read_bytes(), fx.canonical if naming == FULL else fx.expected)
        self.assertEqual((fx.game / PERKS).read_bytes(), fx.perk_canonical if perks == ON else fx.perk_expected)
        status = manager.inspect()
        self.assertEqual((status['installed_naming'], status['installed_perks']), (naming, perks))
        self.assertEqual(status['status'], 'installed')

    def test_all_combinations_repair_and_cacheless_restore_native_and_modified(self):
        for modified, loose in ((False, False), (False, True), (True, True)):
            with self.subTest(modified=modified, loose=loose):
                fx = fixture(self.base / f'{modified}-{loose}', loose)
                m = fx.manager()
                r = m.select(fx.option_zip)
                if modified:
                    self.modified(fx, r)
                    (fx.game / EQUIPMENT).write_bytes(table([(1, b'prior custom loose table')]))
                before = fx.snapshot()
                baseline = None
                for naming, perks in ((FULL, ON), (VANILLA, ON), (FULL, OFF), (VANILLA, OFF), (FULL, ON)):
                    snapshot = fx.snapshot()
                    checked = m.inspect(r, naming=naming, perks=perks)
                    self.assertEqual(fx.snapshot(), snapshot)
                    m.run('install', r, naming=naming, perks=perks,
                          accept_modifications=checked.get('confirmation_token'))
                    self.assert_choices(fx, m, naming, perks)
                    active = m._read_state()['active']
                    baseline = baseline or active['baseline']
                    self.assertEqual(active['baseline'], baseline)
                    self.assertIn('Русский', r.with_features(naming=naming, perks=perks).name)
                    # Repair must retain BOTH selected options, regardless of caller defaults.
                    (fx.game / EQUIPMENT).unlink()
                    (fx.game / PERKS).unlink()
                    for cache in (r.folder / 'derived').glob('*'):
                        cache.write_bytes(b'corrupt derived cache')
                    m.run('repair', naming=FULL, perks=ON)
                    self.assert_choices(fx, m, naming, perks)
                    for target, value in before.items():
                        if target not in r.by_path:
                            self.assertEqual(fx.snapshot()[target], value)
                # Restore does not need downloaded content or either type of payload cache.
                for relative in r.files:
                    (r.folder / relative).unlink()
                for cache in (r.folder / 'derived').glob('*'):
                    cache.unlink()
                fx.option_zip.unlink()
                m.run('restore')
                self.assertEqual(fx.snapshot(), before)

    def test_upgrade_preserves_prior_language_history_and_baseline(self):
        fx = fixture(self.base)
        m = fx.manager()
        en, _, _ = fx.build(20, translation_localization=True)
        m.run('install', m.select(en))
        m.run('restore')
        old = m.select(fx.old_zip)
        m.run('install', old)
        baseline = m._read_state()['active']['baseline']
        r = m.select(fx.option_zip)
        self.assertEqual(m.inspect(r)['changed_payload_files'], 0)
        m.run('install', r, naming=VANILLA, perks=OFF)
        self.assert_choices(fx, m, VANILLA, OFF)
        state = m._read_state()
        self.assertEqual(state['language_sequences'], dict(en=20, de=0, ru=10, fr=0))
        self.assertEqual(state['schema'], 6)
        self.assertEqual(state['active']['baseline'], baseline)
        m.run('restore')
        self.assertEqual(fx.snapshot(), fx.original)

    def test_ru_blanks_controls_and_placeholders_are_preserved(self):
        fx = fixture(self.base)
        m = fx.manager()
        m.run('install', m.select(fx.option_zip), naming=VANILLA, perks=OFF)
        self.assert_choices(fx, m, VANILLA, OFF)
        equipment = dict(read_table((fx.game / EQUIPMENT).read_bytes(), 'strings'))
        perks = dict(read_table((fx.game / PERKS).read_bytes(), 'dlstrings'))
        self.assertEqual(equipment[3], b'')
        self.assertEqual(perks[10], 'Урон <mag>%\r\n<dur> сек.'.encode())
        self.assertEqual(perks[20], b'\x10' + 'Условие'.encode())
        self.assertEqual(perks[30], b'')
        self.assertEqual(perks[40], 'KKS Другой эффект'.encode())

    def test_new_capability_minimum_version_and_locale_are_mandatory(self):
        fx = fixture(self.base)
        validate_manifest(fx.option_manifest)
        for mutate in (
            lambda m: m['required_capabilities'].remove(RUSSIAN_OPTIONAL_CAPABILITY),
            lambda m: m.update(minimum_installer_version='1.5.0'),
            lambda m: m['game'].update(language='en'),
            lambda m: m['files'][0].update(path='payload/interface/fonts_en.swf'),
        ):
            bad = deepcopy(fx.option_manifest)
            mutate(bad)
            with self.assertRaises(SafetyError):
                validate_manifest(bad)
        for lang in ('de', 'fr'):
            _, m, _ = fx.build(11, language=lang)
            m.update(schema=3, equipment_naming=fx.option_manifest['equipment_naming'],
                     perk_cards=fx.option_manifest['perk_cards'])
            m['required_capabilities'] += [CAPABILITY, PERK_CAPABILITY]
            with self.assertRaises(SafetyError):
                validate_manifest(m)

    def test_wrong_signed_derived_hash_refuses_before_transaction(self):
        fx = fixture(self.base)
        m = fx.manager()
        m.run('install', m.select(fx.old_zip))
        for key in ('equipment_naming', 'perk_cards'):
            bad = deepcopy(fx.option_manifest)
            bad[key]['sha256'] = '0' * 64
            r = m.select(fx.write(self.base / (key + '.zip'), bad, fx.option_payloads))
            before = fx.snapshot()
            with self.assertRaises(SafetyError):
                m.run('install', r, naming=VANILLA, perks=OFF)
            self.assertEqual(fx.snapshot(), before)
            self.assertFalse(m.saved('pending.json').exists())

    def test_overlap_consent_is_bound_to_both_options_and_input_bytes(self):
        fx = fixture(self.base)
        m = fx.manager()
        r = m.select(fx.option_zip)
        self.modified(fx, r)
        token = m.inspect(r)['confirmation_token']
        before = fx.snapshot()
        for naming, perks in ((FULL, OFF), (VANILLA, ON), (VANILLA, OFF)):
            with self.assertRaises(SafetyError):
                m.run('install', r, naming=naming, perks=perks, accept_modifications=token)
            self.assertEqual(fx.snapshot(), before)
        path = fx.game / EQUIPMENT
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(fx.native)
        before = fx.snapshot()
        with self.assertRaises(SafetyError):
            m.run('install', r, accept_modifications=token)
        self.assertEqual(fx.snapshot(), before)
        fresh = m.inspect(r, naming=VANILLA, perks=OFF)['confirmation_token']
        m.run('install', r, naming=VANILLA, perks=OFF, accept_modifications=fresh)
        m.run('restore')
        self.assertEqual(fx.snapshot(), before)

    def test_interrupted_profile_switch_keeps_modified_baseline(self):
        for checkpoint in ('after_restore_pending', 'after_vanilla_committed', 'file_replaced',
                           'engine_receipt_saved', 'before_state_publish', 'after_state_publish'):
            with self.subTest(checkpoint=checkpoint):
                fx = fixture(self.base / checkpoint)
                m = fx.manager()
                r = m.select(fx.option_zip)
                self.modified(fx, r)
                before = fx.snapshot()
                m.run('install', r, accept_modifications=m.inspect(r)['confirmation_token'])
                def stop(name, data):
                    if name == checkpoint:
                        raise SystemExit('interrupted Russian switch')
                m.event = stop
                with self.assertRaises(SystemExit):
                    m.run('install', r, naming=VANILLA, perks=OFF)
                fresh = fx.manager()
                fresh.recover()
                if fresh._read_state()['active']:
                    self.assertEqual(fresh.inspect()['status'], 'installed')
                    fresh.run('restore')
                self.assertEqual(fx.snapshot(), before)


if __name__ == '__main__':
    unittest.main()
