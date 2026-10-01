import tempfile, unittest
from pathlib import Path
from kks_installer.packages import ARCHIVES, STRINGS, IDENTITIES
from kks_installer.platforms import SafetyError
from package_fixture import PackageFixture
from test_installer import archive


def steam_update(fx):
    for path in IDENTITIES: (fx.game/path).write_bytes(('updated identity '+path).encode())
    for path,name in ARCHIVES.items():
        archive(fx.game/path,[(name,('new vanilla '+name).encode(),True),('updated-other.bin',b'new game data',False)])
        fx.raw_originals[path]=(fx.game/path).read_bytes()
    fx.loose={p:('new vanilla '+p).encode() for p in STRINGS}
    return fx.build(5,mutate=lambda m:m['game'].update(baseline_id='updated-baseline'))[0]


class ReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.base=Path(self.tmp.name)
        self.fx=PackageFixture(self.base); self.m=self.fx.manager(); self.a=self.m.select(self.fx.a); self.m.run('install',self.a)
    def tearDown(self): self.tmp.cleanup()
    def latest(self): return self.m.select(steam_update(self.fx))
    def test_new_game_skips_versions_and_never_restores_old_archives(self):
        new=self.latest(); expected={p:h for p,h in self.fx.snapshot().items() if p not in STRINGS}
        self.assertEqual(self.m.inspect(new)['status'],'update_available')
        self.m.run('install',new); self.m.run('restore')
        self.assertEqual(self.fx.snapshot(),expected)
        self.assertEqual(len(self.m._read_state()['retired']),1)
    def test_old_originally_present_tables_not_copied_into_new_game(self):
        sub=self.base/'present'; sub.mkdir(); fx=PackageFixture(sub,loose=True); m=fx.manager(); a=m.select(fx.a); m.run('install',a)
        b=m.select(steam_update(fx)); expected={p:h for p,h in fx.snapshot().items() if p not in STRINGS}
        m.run('install',b); m.run('restore'); self.assertEqual(fx.snapshot(),expected)
    def test_new_vanilla_loose_table_is_preserved(self):
        new=self.latest(); p=sorted(STRINGS)[0]; (self.fx.game/p).write_bytes(self.fx.loose[p])
        self.m.run('install',new); self.m.run('restore')
        self.assertEqual((self.fx.game/p).read_bytes(),self.fx.loose[p])
        self.assertTrue(all(not (self.fx.game/x).exists() for x in STRINGS if x!=p))
    def test_foreign_loose_table_blocks_all_cleanup(self):
        new=self.latest(); (self.fx.game/sorted(STRINGS)[-1]).write_bytes(b'other mod')
        before=self.fx.snapshot()
        with self.assertRaises(SafetyError): self.m.run('install',new)
        self.assertEqual(before,self.fx.snapshot())
    def test_old_vanilla_loose_table_is_not_assumed_owned_override(self):
        old_vanilla=dict(self.fx.loose); new=self.latest(); p=sorted(STRINGS)[0]; (self.fx.game/p).write_bytes(old_vanilla[p])
        before=self.fx.snapshot()
        with self.assertRaises(SafetyError): self.m.run('install',new)
        self.assertEqual(before,self.fx.snapshot())
    def test_one_archive_not_updated_blocks_cleanup(self):
        p=next(iter(ARCHIVES)); old=(self.fx.game/p).read_bytes(); new=self.latest(); (self.fx.game/p).write_bytes(old)
        before=self.fx.snapshot()
        with self.assertRaises(SafetyError): self.m.run('install',new)
        self.assertEqual(before,self.fx.snapshot())
    def test_interruption_during_each_cleanup_file_recovers_new_vanilla(self):
        for index in range(3):
            with self.subTest(index=index):
                sub=self.base/str(index); sub.mkdir(); fx=PackageFixture(sub); m=fx.manager(); a=m.select(fx.a); m.run('install',a)
                b=m.select(steam_update(fx)); expected={p:h for p,h in fx.snapshot().items() if p not in STRINGS}
                def crash(event,data):
                    if event=='override_retired' and data['index']==index: raise SystemExit('crash')
                m.event=crash
                with self.assertRaises(SystemExit): m.run('install',b)
                fresh=fx.manager(); fresh.recover(); self.assertEqual(fx.snapshot(),expected)
                fresh.run('install',b); fresh.run('restore'); self.assertEqual(fx.snapshot(),expected)
    def test_new_game_install_failure_returns_new_vanilla(self):
        new=self.latest(); expected={p:h for p,h in self.fx.snapshot().items() if p not in STRINGS}
        def crash(event,data):
            if event=='file_replaced': raise SystemExit('new install crash')
        self.m.event=crash
        with self.assertRaises(SystemExit): self.m.run('install',new)
        self.fx.manager().recover(); self.assertEqual(self.fx.snapshot(),expected)
    def test_external_change_during_cleanup_recovery_is_preserved(self):
        new=self.latest()
        def crash(event,data):
            if event=='override_retired': raise SystemExit('crash')
        self.m.event=crash
        with self.assertRaises(SystemExit): self.m.run('install',new)
        (self.fx.game/sorted(STRINGS)[-1]).write_bytes(b'new foreign override'); before=self.fx.snapshot()
        with self.assertRaises(SafetyError): self.fx.manager().recover()
        self.assertEqual(before,self.fx.snapshot())


if __name__=='__main__': unittest.main()
