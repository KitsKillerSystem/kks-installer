import hashlib,json,os,shutil,struct,tempfile,unittest,zlib
from pathlib import Path
from unittest.mock import patch
from kks_installer.ba2 import BA2,ArchiveError,hash_file
from kks_installer.engine import Release,Installer,SafetyError,STATE,digest
from kks_installer.platforms import operation_lock

def archive(path,assets,version=1):
    """Independent fixture encoder, including preserved opaque metadata/tail."""
    records=[];body=bytearray();offset=24+36*len(assets)+7
    for i,(name,plain,packed) in enumerate(assets):
        data=zlib.compress(plain) if packed else plain
        records.append(struct.pack('<I4sIIQIII',i+31,b'swf\0',i+90,0x100,offset,len(data) if packed else 0,len(plain),0xBAADF00D))
        body.extend(data);offset+=len(data)
    names=b''.join(struct.pack('<H',len(n.encode()))+n.encode() for n,_,_ in assets)+b'TAIL'
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(struct.pack('<4sI4sIQ',b'BTDX',version,b'GNRL',len(assets),offset)+b''.join(records)+b'PADDING'+body+names)

class Fixture:
    def __init__(self,base,loose=False):
        self.root=base/'game';self.root.mkdir();self.release=base/'release';self.release.mkdir()
        (self.root/'Fallout76.exe').write_bytes(b'verified executable fixture')
        (self.root/'Data').mkdir();(self.root/'Data/SeventySix.esm').write_bytes(b'game esm identity fixture')
        self.archive=self.root/'Data/SeventySix - Interface_en.ba2'
        archive(self.archive,[('interface/fonts_en.swf',b'original font',True),('unrelated.txt',b'untouched data'*200,False)])
        self.original=self.archive.read_bytes()
        payload=self.release/'font.bin';payload.write_bytes(b'KKS replacement font'*150)
        strings=self.release/'strings.bin';strings.write_bytes(b'KKS string table fixture')
        staged=base/'patched.ba2';BA2(self.archive).replace_to(staged,{'interface/fonts_en.swf':payload.read_bytes()})
        self.loose=self.root/'Data/strings/seventysix_en.strings'
        if loose:self.loose.parent.mkdir();self.loose.write_bytes(b'vanilla string fixture')
        targets=[{'path':'Data/SeventySix - Interface_en.ba2','kind':'archive','version':1,'type':'GNRL','vanilla_sha256':hash_file(self.archive),'after_sha256':hash_file(staged),
                  'assets':[{'name':'interface/fonts_en.swf','payload':'font.bin','vanilla_sha256':digest(b'original font'),'sha256':hash_file(payload)}]},
                 {'path':'Data/strings/seventysix_en.strings','kind':'loose','payload':'strings.bin','vanilla_sha256':digest(b'vanilla string fixture'),'after_sha256':hash_file(strings)}]
        manifest={'schema':1,'release':'test fixture','supported_build':'test build only','targets':targets,
                  'identity':[{'path':p,'sha256':hash_file(self.root/p)} for p in ['Fallout76.exe','Data/SeventySix.esm']]}
        p=self.release/'manifest.json';p.write_text(json.dumps(manifest),'utf8');self.spec=Release(self.release,hash_file(p));self.engine=Installer(self.root,self.spec)

class ArchiveTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def make(self,assets=None):
        p=self.root/'original.ba2';archive(p,assets or [('Interface\\Fonts_en.swf',b'old'*100,True),('other.bin',b'no change',False)]);return p
    def test_replace_preserves_unrelated_metadata_and_payload(self):
        p=self.make();before=p.read_bytes();out=self.root/'out.ba2';BA2(p).replace_to(out,{'interface/fonts_en.swf':b'new'*700})
        self.assertEqual(p.read_bytes(),before);self.assertEqual(BA2(out).extract('interface/fonts_en.swf'),b'new'*700)
        self.assertEqual(BA2(out).extract('other.bin'),b'no change');self.assertEqual(out.read_bytes()[-4:],b'TAIL')
    def test_uncompressed_replacement_stays_uncompressed(self):
        p=self.make([('a',b'old',False)]);out=self.root/'new.ba2';BA2(p).replace_to(out,{'a':b'longer'})
        self.assertEqual(BA2(out).by_name['a'].packed,0)
    def test_reject_unknown_version(self):
        p=self.make();b=bytearray(p.read_bytes());struct.pack_into('<I',b,4,8);p.write_bytes(b)
        with self.assertRaises(ArchiveError):BA2(p)
    def test_reject_texture_archive(self):
        p=self.make();b=bytearray(p.read_bytes());b[8:12]=b'DX10';p.write_bytes(b)
        with self.assertRaises(ArchiveError):BA2(p)
    def test_duplicate_normalized_names(self):
        p=self.make([('A/B',b'1',False),('a\\b',b'2',False)])
        with self.assertRaises(ArchiveError):BA2(p)
    def test_bad_names_offset(self):
        p=self.make();b=bytearray(p.read_bytes());struct.pack_into('<Q',b,16,20);p.write_bytes(b)
        with self.assertRaises(ArchiveError):BA2(p)
    def test_overlapping_payloads(self):
        p=self.make();b=bytearray(p.read_bytes());struct.pack_into('<Q',b,24+36+16,struct.unpack_from('<Q',b,24+16)[0]);p.write_bytes(b)
        with self.assertRaises(ArchiveError):BA2(p)
    def test_truncated_archive(self):
        p=self.make();p.write_bytes(p.read_bytes()[:40])
        with self.assertRaises(ArchiveError):BA2(p)
    def test_corrupt_compressed_asset(self):
        p=self.make();entry=BA2(p).entries[0];b=bytearray(p.read_bytes());b[entry.offset]=0;p.write_bytes(b)
        with self.assertRaises(ArchiveError):BA2(p).extract(entry.name)
    def test_unpacked_size_lie(self):
        p=self.make();b=bytearray(p.read_bytes());struct.pack_into('<I',b,24+28,1);p.write_bytes(b)
        with self.assertRaises(ArchiveError):BA2(p).extract('interface/fonts_en.swf')
    def test_reject_insertion(self):
        p=self.make()
        with self.assertRaises(ArchiveError):BA2(p).replace_to(self.root/'out.ba2',{'missing':b'X'})
    def test_never_overwrite_source(self):
        p=self.make();raw=p.read_bytes()
        with self.assertRaises(ArchiveError):BA2(p).replace_to(p,{'other.bin':b'X'})
        self.assertEqual(p.read_bytes(),raw)
    def test_reject_path_traversal(self):
        p=self.make([('../outside',b'X',False)])
        with self.assertRaises(ArchiveError):BA2(p)

class TransactionTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.base=Path(self.tmp.name);self.fx=Fixture(self.base)
    def tearDown(self):self.tmp.cleanup()
    def check_original(self):
        self.assertEqual(self.fx.archive.read_bytes(),self.fx.original);self.assertFalse(self.fx.loose.exists())
    def test_check_is_read_only(self):
        self.assertEqual(self.fx.engine.inspect()['status'],'ready');self.assertFalse((self.fx.root/STATE).exists())
    def test_conflict_arriving_between_validation_and_backup_is_not_overwritten(self):
        real_usage=shutil.disk_usage
        def external_change(path):
            self.fx.archive.write_bytes(b'another mod arrived after compatibility check')
            return real_usage(path)
        with patch('kks_installer.engine.shutil.disk_usage',side_effect=external_change):
            with self.assertRaises(SafetyError):self.fx.engine.run('install')
        self.assertEqual(self.fx.archive.read_bytes(),b'another mod arrived after compatibility check')
        self.assertFalse((self.fx.root/STATE/'pending.json').exists())
        self.assertFalse(self.fx.loose.exists())
    def test_install_idempotent_and_exact_restore(self):
        e=self.fx.engine;self.assertEqual(e.run('install')['status'],'installed');self.assertEqual(e.inspect()['status'],'installed')
        patched=self.fx.archive.read_bytes();e.run('install');self.assertEqual(self.fx.archive.read_bytes(),patched)
        e.run('restore');self.check_original();self.assertEqual(e.inspect()['status'],'ready')
        self.assertGreater(len(list((self.fx.root/STATE/'backups').glob('*.bin'))),0)
    def test_preserve_preexisting_vanilla_loose_file(self):
        self.fx.loose.parent.mkdir();self.fx.loose.write_bytes(b'vanilla string fixture');e=self.fx.engine;e.run('install');e.run('restore')
        self.assertEqual(self.fx.loose.read_bytes(),b'vanilla string fixture')
    def test_repair_missing_loose_and_reset_archive(self):
        e=self.fx.engine;e.run('install');self.fx.loose.unlink();self.fx.archive.write_bytes(self.fx.original)
        self.assertEqual(e.inspect()['status'],'repairable');e.run('repair');self.assertEqual(e.inspect()['status'],'installed');e.run('restore');self.check_original()
    def test_unknown_archive_fails_before_writes(self):
        self.fx.archive.write_bytes(self.fx.original+b'other mod');before=self.fx.archive.read_bytes()
        with self.assertRaises(SafetyError):self.fx.engine.run('install')
        self.assertEqual(self.fx.archive.read_bytes(),before);self.assertFalse(self.fx.loose.exists())
    def test_unknown_game_update_blocks_restore(self):
        e=self.fx.engine;e.run('install');installed=self.fx.archive.read_bytes();(self.fx.root/'Data/SeventySix.esm').write_bytes(b'new patch')
        with self.assertRaises(SafetyError):e.run('restore')
        self.assertEqual(self.fx.archive.read_bytes(),installed)
    def test_payload_tamper_fails(self):
        (self.fx.release/'font.bin').write_bytes(b'bad')
        with self.assertRaises(SafetyError):self.fx.engine.run('install')
        self.check_original()
    def test_manifest_tamper_fails(self):
        (self.fx.release/'manifest.json').write_text('{}')
        with self.assertRaises(SafetyError):Release(self.fx.release,self.fx.spec.manifest_digest)
    def test_external_loose_mod_fails(self):
        self.fx.loose.parent.mkdir();self.fx.loose.write_bytes(b'another user mod')
        with self.assertRaises(SafetyError):self.fx.engine.run('install')
        self.assertEqual(self.fx.loose.read_bytes(),b'another user mod')
    def test_io_failure_rolls_back(self):
        def fail(index,entry):raise OSError('simulated write failure')
        self.fx.engine._after_replace=fail
        with self.assertRaisesRegex(SafetyError,'rolled back'):self.fx.engine.run('install')
        self.check_original();self.assertFalse(self.fx.engine.journal_path.exists())
    def test_crash_recovery_after_each_write(self):
        for cutoff in [0,1]:
            with self.subTest(cutoff=cutoff):
                def crash(index,entry):
                    if index==cutoff:raise SystemExit('simulated power loss')
                self.fx.engine._after_replace=crash
                with self.assertRaises(SystemExit):self.fx.engine.run('install')
                self.assertTrue(self.fx.engine.journal_path.exists());self.fx.engine.recover();self.check_original()
    def test_crash_during_restore_recovers_installed_state(self):
        e=self.fx.engine;e.run('install');before=self.fx.archive.read_bytes()
        def crash(index,entry):raise SystemExit('restore crash')
        e._after_replace=crash
        with self.assertRaises(SystemExit):e.run('restore')
        e.recover();self.assertEqual(self.fx.archive.read_bytes(),before);self.assertEqual(e.inspect()['status'],'installed')
    def test_recovery_conflict_changes_nothing(self):
        def crash(index,entry):raise SystemExit('crash')
        e=self.fx.engine;e._after_replace=crash
        with self.assertRaises(SystemExit):e.run('install')
        patched=self.fx.archive.read_bytes();self.fx.loose.parent.mkdir(exist_ok=True);self.fx.loose.write_bytes(b'external change')
        with self.assertRaises(SafetyError):e.recover()
        self.assertEqual(self.fx.archive.read_bytes(),patched);self.assertEqual(self.fx.loose.read_bytes(),b'external change');self.assertTrue(e.journal_path.exists())
    def test_damaged_backup_stops_restore(self):
        e=self.fx.engine;e.run('install');patched=self.fx.archive.read_bytes();h=self.fx.spec.targets[0]['vanilla_sha256'];(self.fx.root/STATE/'backups'/f'{h}.bin').write_bytes(b'bad backup')
        with self.assertRaises(SafetyError):e.run('restore')
        self.assertEqual(self.fx.archive.read_bytes(),patched)
    def test_insufficient_space(self):
        with patch('kks_installer.engine.shutil.disk_usage',return_value=shutil._ntuple_diskusage(1,1,0)):
            with self.assertRaises(SafetyError):self.fx.engine.run('install')
        self.check_original()
    def test_game_running_blocks_changes(self):
        with patch('kks_installer.platforms.game_running',return_value=True):
            with self.assertRaises(SafetyError):self.fx.engine.run('install')
        self.check_original()
    def test_simultaneous_operation_lock(self):
        lock=self.fx.root/STATE/'operation.lock'
        with operation_lock(lock):
            with self.assertRaises(SafetyError):self.fx.engine.run('install')
        self.check_original()
    def test_hardlinked_target_rejected(self):
        os.link(self.fx.archive,self.base/'linked.ba2')
        with self.assertRaises(SafetyError):self.fx.engine.run('install')
        self.check_original()
    def test_journal_path_traversal_rejected(self):
        e=self.fx.engine
        def crash(index,entry):raise SystemExit('crash')
        e._after_replace=crash
        with self.assertRaises(SystemExit):e.run('install')
        j=json.loads(e.journal_path.read_bytes());j['entries'][0]['path']='../outside';e.journal_path.write_text(json.dumps(j))
        before=self.fx.archive.read_bytes()
        with self.assertRaises(SafetyError):e.recover()
        self.assertEqual(self.fx.archive.read_bytes(),before)
    def test_corrupt_receipt_rejected(self):
        e=self.fx.engine;e.run('install');r=json.loads(e.receipt_path.read_bytes());r['files']['../outside']={};e.receipt_path.write_text(json.dumps(r))
        with self.assertRaises(SafetyError):e.run('restore')
    def test_restore_without_install_does_not_remove_files(self):
        with self.assertRaises(SafetyError):self.fx.engine.run('restore')
        self.check_original()

if __name__=='__main__':unittest.main(verbosity=2)
