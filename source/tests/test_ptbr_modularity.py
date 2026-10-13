"""Brazilian Portuguese optional profiles restore their native bytes, never English."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from package_fixture import PackageFixture
from test_installer import archive
from test_equipment import table
from test_perks import dl_table
from kks_installer.ba2 import BA2
from kks_installer.engine import digest
from kks_installer.equipment import CAPABILITY, FULL, VANILLA
from kks_installer.perks import CAPABILITY as PERK_CAPABILITY, ON, OFF
from kks_installer._application import PORTUGUESE_OPTIONAL_CAPABILITY
from kks_installer.packages import LOCALIZATION, validate_manifest
from kks_installer.platforms import SafetyError

def fixture(base, lang):
    fx = PackageFixture(base, multilingual=True, loose=True)
    names = ('Espada', 'Armadura', 'Sorte')
    native = table([(1, names[0].encode()), (2, names[1].encode()), (3, b''), (4, names[2].encode())])
    canonical = table([(1, ('KKS '+names[0]).encode()), (2, ('KKS '+names[1]).encode()), (3, b'KKS'), (4, names[2].encode())])
    desc = ('Dano <mag>%\r\n<dur> s').encode()
    perk_native = dl_table([(10, desc), (20, b'\x10control'), (30, b''), (40, b'unrelated')])
    perk_canonical = dl_table([(10, '\uea00\uea01'.encode()), (20, '\uea02'.encode()), (30, b''), (40, b'unrelated')])
    loc = fx.game / LOCALIZATION
    orig = BA2(loc)
    members = [(n, orig.extract(n), True) for n in orig.by_name]
    for language in ('en', lang):
        members += [(f'strings/seventysix_{language}.strings', native if language == lang else table([(1,b'EN'),(2,b'EN'),(3,b'EN'),(4,b'EN')]), True),
                    (f'strings/seventysix_{language}.dlstrings', perk_native if language == lang else dl_table([(10,b'EN'),(20,b'EN'),(30,b'EN'),(40,b'EN')]), True)]
    archive(loc, members); fx.raw_originals[LOCALIZATION] = loc.read_bytes()
    equip_path=f'Data/strings/seventysix_{lang}.strings'; perk_path=f'Data/strings/seventysix_{lang}.dlstrings'
    for path,raw in ((equip_path,native),(perk_path,perk_native)):
        fx.loose[path]=raw; (fx.game/path).write_bytes(raw)
    before=fx.snapshot(); path,m,payloads=fx.build(10,language=lang)
    for target,raw in ((equip_path,canonical),(perk_path,perk_canonical)):
        payload='payload/'+target[5:];payloads[payload]=raw
        next(f for f in m['files'] if f['path']==payload).update(sha256=digest(raw),size=len(raw))
        next(t for t in m['targets'] if t['path']==target).update(after_sha256=digest(raw),after_size=len(raw))
    m.update(schema=3)
    m['required_capabilities'] += [CAPABILITY,PERK_CAPABILITY,PORTUGUESE_OPTIONAL_CAPABILITY]
    m['equipment_naming']=dict(algorithm=CAPABILITY,categories={'WEAP:FULL':[1],'ARMO:FULL':[2],'INNR:WNAM':[3]},sha256=digest(native),size=len(native))
    m['perk_cards']=dict(algorithm=PERK_CAPABILITY,categories={'PERK:DESC':[10,20,30]},sha256=digest(perk_native),size=len(perk_native))
    return fx,fx.write(path,m,payloads),m,before,[(equip_path,canonical,native),(perk_path,perk_canonical,perk_native)]

class PortugueseModularityTests(unittest.TestCase):
    def test_historical_state_and_independent_portuguese_sequence(self):
        import json
        from kks_installer.manager import STATE
        with tempfile.TemporaryDirectory() as d:
            fx,path,manifest,before,files=fixture(Path(d),'ptbr')
            manager=fx.manager()
            # Real schema-6 history from Installer 1.5–1.7 has exactly four keys.
            old=manager._empty()
            old.update(schema=6, highest_sequence=80,
                       language_sequences=dict(en=80,de=4,ru=9,fr=4))
            manager._validate_state(old)
            manager.state.mkdir(exist_ok=True)
            manager.saved('installation.json').write_text(json.dumps(old))
            release=manager.select(path)
            manager.run('install',release,naming=VANILLA,perks=OFF)
            saved=manager._read_state()
            self.assertEqual(saved['schema'],7)
            self.assertEqual(saved['language_sequences'],dict(en=80,de=4,ru=9,fr=4,ptbr=10))
            manager.run('repair')
            manager.run('restore')
            self.assertEqual(fx.snapshot(),before)
            # Old signed EN content still works and cannot drop Portuguese history.
            newer,_,_=fx.build(81)
            manager.run('install',manager.select(newer))
            self.assertEqual(manager._read_state()['language_sequences']['ptbr'],10)
            self.assertEqual(manager._read_state()['schema'],7)
            manager.run('restore')
            older,_,_=fx.build(9,language='ptbr')
            with self.assertRaises(SafetyError):
                manager.run('install',manager.select(older))

    def test_legacy_schema_validation_stays_strict(self):
        with tempfile.TemporaryDirectory() as d:
            fx=PackageFixture(Path(d),multilingual=True);manager=fx.manager()
            for schema in (3,4,5,6,7):
                state=manager._empty();state['schema']=schema
                codes=('en','de') if schema==3 else ('en','de','ru','fr') if schema<7 else ('en','de','ru','fr','ptbr')
                state['language_sequences']=dict.fromkeys(codes,0)
                manager._validate_state(state)
                state['language_sequences']['unexpected']=0
                with self.assertRaises(SafetyError):manager._validate_state(state)

    def test_both_languages_all_profiles_repair_and_cacheless_restore(self):
        for lang in ('ptbr',):
            with self.subTest(lang=lang), tempfile.TemporaryDirectory() as d:
                fx,path,manifest,before,files=fixture(Path(d),lang);manager=fx.manager();release=manager.select(path);baseline=None
                for naming,perks in ((FULL,ON),(VANILLA,ON),(FULL,OFF),(VANILLA,OFF)):
                    manager.run('install',release,naming=naming,perks=perks)
                    current=manager._read_state()['active']['baseline'];baseline=baseline or current;self.assertEqual(baseline,current)
                    for (target,custom,native),use_native in zip(files,(naming==VANILLA,perks==OFF)):
                        self.assertEqual((fx.game/target).read_bytes(),native if use_native else custom)
                        (fx.game/target).unlink()
                    manager.run('repair',naming=FULL,perks=ON)
                    for (target,custom,native),use_native in zip(files,(naming==VANILLA,perks==OFF)):
                        self.assertEqual((fx.game/target).read_bytes(),native if use_native else custom)
                for relative in release.files:(release.folder/relative).unlink()
                for p in (release.folder/'derived').glob('*'):p.unlink()
                path.unlink();manager.run('restore');self.assertEqual(fx.snapshot(),before)
    def test_capability_version_and_language_are_bound(self):
        for lang in ('ptbr',):
            with self.subTest(lang=lang), tempfile.TemporaryDirectory() as d:
                _,_,manifest,_,_=fixture(Path(d),lang);validate_manifest(manifest)
                for mutate in (lambda m:m['required_capabilities'].remove(PORTUGUESE_OPTIONAL_CAPABILITY),lambda m:m.update(minimum_installer_version='1.7.0'),lambda m:m['game'].update(language='en')):
                    bad=deepcopy(manifest);mutate(bad)
                    with self.assertRaises(SafetyError):validate_manifest(bad)
