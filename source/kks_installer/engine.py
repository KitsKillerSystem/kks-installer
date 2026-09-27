"""Fail-closed installation, durable backups, and recoverable transactions.

Each file replacement is atomic on the same volume. A set of file replacements
is NOT a filesystem-wide atomic transaction; the on-disk journal rolls a partial
operation back on error or the next run. Unknown/concurrently changed files are
never overwritten during recovery.
"""
from pathlib import Path
from contextlib import nullcontext
import hashlib, json, os, shutil, uuid
from .ba2 import BA2, hash_file
from .platforms import SafetyError, safe_path, operation_lock, game_guard, game_running

STATE = '.kks-installer-1.0.0'
DIGITS = set('0123456789abcdef')

def digest(data): return hashlib.sha256(data).hexdigest()
def is_digest(value): return isinstance(value,str) and len(value)==64 and set(value)<=DIGITS
def file_hash(path): return hash_file(path) if path.is_file() else None
def demand(condition, message):
    if not condition: raise SafetyError(message)

def sync_directory(path):
    if os.name != 'nt':
        fd=os.open(path,os.O_RDONLY)
        try:os.fsync(fd)
        finally:os.close(fd)

def durable_bytes(path, data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    with temporary.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
    os.replace(temporary,path);sync_directory(path.parent)

def durable_json(path, data):
    durable_bytes(path,(json.dumps(data,indent=2,sort_keys=True)+'\n').encode('utf8'))

def verified_copy(source, destination, expected):
    destination=Path(destination);destination.parent.mkdir(parents=True,exist_ok=True)
    with Path(source).open('rb') as a, destination.open('xb') as b:
        shutil.copyfileobj(a,b,1024*1024);b.flush();os.fsync(b.fileno())
    demand(hash_file(destination)==expected, 'A file changed during copying, or storage verification failed')

class Release:
    def __init__(self, folder, expected_manifest):
        self.folder=Path(folder).resolve()
        manifest_path=safe_path(self.folder,'manifest.json',regular=True)
        raw=manifest_path.read_bytes()
        demand(digest(raw)==expected_manifest,'The bundled release manifest failed its integrity check')
        self.manifest_digest=expected_manifest
        self.data=json.loads(raw)
        demand(self.data.get('schema')==1,'Unsupported release schema')
        self.name=self.data['release']
        self.targets=self.data['targets']
        self.by_path={t['path']:t for t in self.targets}
        demand(len(self.by_path)==len(self.targets)>0,'Duplicate managed paths')
        for t in self.targets:
            safe_path(self.folder,t['path'])
            demand(t['path'].startswith('Data/'),'All managed assets must be inside Data')
            demand(t['kind'] in ('archive','loose') and is_digest(t['after_sha256']) and is_digest(t['vanilla_sha256']),
                   'Invalid target specification')
            if t['kind']=='archive':
                demand(t.get('version')==1 and t.get('type')=='GNRL' and bool(t.get('assets')),'Unsupported target archive')
                for asset in t['assets']:
                    demand(is_digest(asset['vanilla_sha256']) and is_digest(asset['sha256']),'Invalid asset hashes')
            else:safe_path(self.folder,t['payload'])
        for identity in self.data['identity']:
            safe_path(self.folder,identity['path'])
            demand(is_digest(identity['sha256']),'Invalid game identity hash')

    def payload(self, relative, expected):
        path=safe_path(self.folder,relative,regular=True)
        demand(path.is_file() and hash_file(path)==expected,f'Bundled payload failed verification: {relative}')
        return path

    def verify_payloads(self):
        for t in self.targets:
            if t['kind']=='loose':self.payload(t['payload'],t['after_sha256'])
            else:
                for a in t['assets']:self.payload(a['payload'],a['sha256'])

class Installer:
    def __init__(self, game, release, log=None):
        self.root=Path(game).resolve()
        self.release=release
        self.log=log or (lambda message:None)
        self.state=safe_path(self.root,STATE)
        demand(not self.state.exists() or self.state.is_dir(),'Invalid KKS state directory')
        self.receipt_path=safe_path(self.root,STATE+'/receipt.json',regular=True)
        self.journal_path=safe_path(self.root,STATE+'/pending.json',regular=True)

    def target(self, relative):return safe_path(self.root,relative,regular=True)
    def executable_hash(self):return next(x['sha256'] for x in self.release.data['identity'] if x['path']=='Fallout76.exe')
    def state_path(self, relative):return safe_path(self.root,STATE+'/'+relative,regular=True)
    def current(self, relative):return file_hash(self.target(relative))

    def _identity(self, *, skip_exe=False):
        self.log('Verifying the supported game build…')
        for item in self.release.data['identity']:
            if skip_exe and item['path']=='Fallout76.exe':continue
            p=self.target(item['path'])
            demand(p.is_file() and hash_file(p)==item['sha256'],
                   f'Unsupported or changed game build: {item["path"]}. This release supports {self.release.data["supported_build"]}.')

    def _receipt(self):
        if not self.receipt_path.exists():return None
        return self._validate_receipt(json.loads(self.receipt_path.read_bytes()))

    def _validate_receipt(self, value):
        demand(isinstance(value,dict) and value.get('schema')==1 and value.get('manifest')==self.release.manifest_digest,
               'The saved installation belongs to a different installer release or is damaged')
        demand(value.get('root')==str(self.root) and value.get('status') in ('installed','restored'),
               'Installation receipt does not match this game folder')
        files=value.get('files',{})
        demand(set(files)==set(self.release.by_path),'Installation receipt has unexpected managed files')
        for path,record in files.items():
            t=self.release.by_path[path]
            permitted=[t['vanilla_sha256']]+([None] if t['kind']=='loose' else [])
            demand(record.get('before') in permitted and record.get('after')==t['after_sha256'],
                   'Installation receipt contains an unknown file version')
        return value

    def _backup(self, source, expected):
        demand(is_digest(expected),'Invalid backup hash')
        path=self.state_path('backups/'+expected+'.bin')
        if path.exists():
            demand(hash_file(path)==expected,'An existing restoration backup is damaged; it will not be overwritten')
            return path
        path.parent.mkdir(parents=True,exist_ok=True)
        temporary=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
        verified_copy(source,temporary,expected)
        os.replace(temporary,path);sync_directory(path.parent)
        return path

    def _backup_path(self, expected):
        demand(is_digest(expected),'Invalid restoration hash')
        path=self.state_path('backups/'+expected+'.bin')
        demand(path.is_file() and hash_file(path)==expected,'A required restoration backup is missing or damaged')
        return path

    def _validate_current(self, receipt):
        result=[]
        for t in self.release.targets:
            current=self.current(t['path'])
            permitted={t['vanilla_sha256']}
            if t['kind']=='loose':permitted.add(None)
            if receipt and receipt['status']=='installed':permitted.add(t['after_sha256'])
            demand(current in permitted,
                   f'Unrecognized or modified target: {t["path"]}. Restore clean game files or resolve the conflicting mod before installing.')
            if t['kind']=='archive':
                archive=BA2(self.target(t['path']))
                for a in t['assets']:
                    expected=a['sha256'] if current==t['after_sha256'] else a['vanilla_sha256']
                    demand(digest(archive.extract(a['name']))==expected,f'Unexpected embedded asset: {a["name"]}')
            result.append({'path':t['path'],'state':'installed' if current==t['after_sha256'] else ('absent' if current is None else 'vanilla'),'sha256':current})
        return result

    def inspect(self):
        self.release.verify_payloads()
        self._identity()
        if self.journal_path.exists():
            self._read_journal()
            return {'status':'recovery_required','release':self.release.name,'game':str(self.root),'message':'An interrupted operation needs recovery before installation can continue.'}
        receipt=self._receipt()
        if receipt and receipt['status']=='installed':
            for r in receipt['files'].values():
                if r['before'] is not None:self._backup_path(r['before'])
        targets=self._validate_current(receipt)
        installed=bool(receipt and receipt['status']=='installed')
        healthy=installed and all(x['sha256']==self.release.by_path[x['path']]['after_sha256'] for x in targets)
        status='installed' if healthy else ('repairable' if installed else 'ready')
        return {'status':status,'release':self.release.name,'supported_build':self.release.data['supported_build'],
                'game':str(self.root),'targets':targets,'game_running':game_running(),
                'message':{'installed':'KKS is installed and verified.','repairable':'Known files were reset or removed. Repair can restore KKS.','ready':'This installation is compatible and ready.'}[status]}

    def _read_journal(self):
        j=json.loads(self.journal_path.read_bytes())
        demand(j.get('schema')==1 and j.get('manifest')==self.release.manifest_digest and j.get('root')==str(self.root),
               'The recovery journal is invalid for this installation')
        entries=j.get('entries',[])
        demand(len(entries)==len(self.release.targets) and {e['path'] for e in entries}==set(self.release.by_path),
               'Unexpected recovery paths')
        for e in entries:
            t=self.release.by_path[e['path']]
            permitted={t['vanilla_sha256'],t['after_sha256']}
            if t['kind']=='loose':permitted.add(None)
            demand(e.get('before') in permitted and e.get('after') in permitted,'Unrecognized version in recovery journal')
            if e['before'] is not None:self._backup_path(e['before'])
        if j.get('receipt_before') is not None:self._validate_receipt(j['receipt_before'])
        return j

    def _recover_locked(self):
        if not self.journal_path.exists():return False
        j=self._read_journal()
        # Preflight every file first: no partial rollback when an outside writer changed a target.
        for e in j['entries']:
            demand(self.current(e['path']) in (e['before'],e['after']),
                   f'Recovery stopped because another program changed {e["path"]}. Backups and the journal are retained.')
        self.log('Recovering the interrupted operation…')
        for e in reversed(j['entries']):
            path=self.target(e['path']);current=file_hash(path)
            if current==e['before']:continue
            demand(current==e['after'],'Target changed during recovery')
            if e['before'] is None:
                path.unlink();sync_directory(path.parent)
            else:
                src=self._backup_path(e['before'])
                temp=self.state_path('recovery/'+uuid.uuid4().hex+'.tmp')
                verified_copy(src,temp,e['before'])
                demand(file_hash(path)==e['after'],'Target changed during recovery')
                os.replace(temp,path);sync_directory(path.parent)
            demand(file_hash(path)==e['before'],'Recovery verification failed')
        if j.get('receipt_before') is None:
            if self.receipt_path.exists():self.receipt_path.unlink()
        else:durable_json(self.receipt_path,j['receipt_before'])
        self.journal_path.unlink();sync_directory(self.state)
        self.log('Previous file state restored. All backups are retained.')
        return True

    def recover(self):
        self.release.verify_payloads();self._identity()
        lock=self.state_path('operation.lock')
        with operation_lock(lock),game_guard(self.target('Fallout76.exe'),self.executable_hash()):
            return {'status':'recovered' if self._recover_locked() else 'no_recovery_needed'}

    def run(self, operation):
        demand(operation in ('install','repair','restore'),'Unknown operation')
        self.release.verify_payloads();self._identity()
        self.state.mkdir(parents=True,exist_ok=True)
        with operation_lock(self.state_path('operation.lock')):
            # Recheck executable before denying all additional opens for the write phase.
            self._identity()
            with game_guard(self.target('Fallout76.exe'),self.executable_hash()):
                return self._run_locked(operation)

    def _run_locked(self, operation):
        if self.journal_path.exists():self._recover_locked()
        self._identity(skip_exe=True)
        receipt=self._receipt()
        checked={item['path']:item['sha256'] for item in self._validate_current(receipt)}
        installed=bool(receipt and receipt['status']=='installed')
        demand(operation!='repair' or installed,'There is no managed installation to repair; use Install')
        demand(operation!='restore' or installed,'There is no managed installation to restore')
        if installed:
            for r in receipt['files'].values():
                if r['before'] is not None:self._backup_path(r['before'])
        free=shutil.disk_usage(self.root).free
        needed=sum(self.target(t['path']).stat().st_size if self.target(t['path']).exists() else 0 for t in self.release.targets)*3+64*1024*1024
        demand(free>=needed,f'Not enough free space for staging and verified backups. At least {needed//(1024*1024)+1} MB is required.')
        tx=uuid.uuid4().hex;staged={};entries=[];result_files={}
        self.log('Saving and verifying restoration backups…')
        for i,t in enumerate(self.release.targets):
            path=self.target(t['path']);before=file_hash(path)
            demand(before==checked[t['path']],
                   'A game file changed after compatibility verification; nothing was installed')
            if before is not None:self._backup(path,before)
            original=receipt['files'][t['path']]['before'] if installed else before
            result_files[t['path']]={'before':original,'after':t['after_sha256']}
            after=original if operation=='restore' else t['after_sha256']
            entry={'path':t['path'],'before':before,'after':after};entries.append(entry)
            if after is None or before==after:continue
            stage=self.state_path(f'staging/{tx}/{i}.tmp');stage.parent.mkdir(parents=True,exist_ok=True)
            if operation=='restore':verified_copy(self._backup_path(after),stage,after)
            elif t['kind']=='loose':verified_copy(self.release.payload(t['payload'],after),stage,after)
            else:
                self.log('Building and validating '+Path(t['path']).name+'…')
                vanilla=self._backup_path(t['vanilla_sha256'])
                replacements={a['name']:self.release.payload(a['payload'],a['sha256']).read_bytes() for a in t['assets']}
                BA2(vanilla).replace_to(stage,replacements)
                demand(hash_file(stage)==after,'Patched archive does not match the verified release output')
            staged[t['path']]=stage
        # All backups and stages exist before any game file changes.
        for e in entries:demand(self.current(e['path'])==e['before'],'A game file changed during preparation; nothing was installed')
        journal={'schema':1,'manifest':self.release.manifest_digest,'root':str(self.root),'operation':operation,
                 'transaction':tx,'entries':entries,'receipt_before':receipt}
        durable_json(self.journal_path,journal)
        try:
            self.log('Applying verified files…')
            for i,e in enumerate(entries):
                path=self.target(e['path'])
                demand(file_hash(path)==e['before'],'A target changed during installation')
                if e['before']==e['after']:continue
                if e['after'] is None:path.unlink()
                else:
                    path.parent.mkdir(parents=True,exist_ok=True)
                    # Re-evaluate the path after creating missing directories.
                    path=self.target(e['path'])
                    os.replace(staged[e['path']],path)
                sync_directory(path.parent)
                self._after_replace(i,e)  # test seam, not exposed by the executable
            self.log('Reopening and validating installed files…')
            for e in entries:
                path=self.target(e['path']);demand(file_hash(path)==e['after'],'Post-write file hash mismatch')
                t=self.release.by_path[e['path']]
                if t['kind']=='archive':
                    archive=BA2(path)
                    for a in t['assets']:
                        expected=a['vanilla_sha256'] if operation=='restore' else a['sha256']
                        demand(digest(archive.extract(a['name']))==expected,'Post-write embedded asset validation failed')
            saved={'schema':1,'manifest':self.release.manifest_digest,'root':str(self.root),
                   'status':'restored' if operation=='restore' else 'installed','release':self.release.name,'files':result_files}
            durable_json(self.receipt_path,saved)
            self.journal_path.unlink();sync_directory(self.state)
            self.log('Vanilla files restored. Backups retained.' if operation=='restore' else 'KKS installed and verified.')
            return {'status':saved['status'],'release':self.release.name,'game':str(self.root),'managed_files':len(entries),'backups':str(self.state/'backups')}
        except Exception as cause:
            try:self._recover_locked()
            except Exception as recovery:
                raise SafetyError(f'Operation interrupted: {cause}. Recovery needs attention: {recovery}. Do not launch the game until recovery succeeds.') from cause
            raise SafetyError(f'Operation failed and was rolled back: {cause}') from cause

    def _after_replace(self, index, entry):
        pass
