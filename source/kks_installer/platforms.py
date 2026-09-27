"""Installation discovery and Windows safety guards (no registry writes)."""
from contextlib import contextmanager
from pathlib import Path
import ctypes, os, re, hashlib

class SafetyError(RuntimeError):
    pass

def safe_path(root, relative, *, regular=False):
    root = Path(root).resolve()
    if not isinstance(relative, str) or '\\' in relative or ':' in relative or relative.startswith('/'):
        raise SafetyError('Invalid managed path')
    parts = relative.split('/')
    if not parts or any(p in ('', '.', '..') for p in parts):
        raise SafetyError('Unsafe managed path')
    path = root
    for part in parts:
        path /= part
        if path.exists() or path.is_symlink():
            info = path.lstat()
            if path.is_symlink() or getattr(info, 'st_file_attributes', 0) & 0x400:
                raise SafetyError(f'Reparse points are not supported: {relative}')
            if path.is_file() and info.st_nlink > 1:
                raise SafetyError(f'Hard-linked files are not supported: {relative}')
    if regular and path.exists() and not path.is_file():
        raise SafetyError(f'Expected a regular file: {relative}')
    return path

def game_running():
    if os.name != 'nt': return False
    from ctypes import wintypes as w
    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [('dwSize',w.DWORD),('cntUsage',w.DWORD),('th32ProcessID',w.DWORD),
                    ('th32DefaultHeapID',ctypes.c_size_t),('th32ModuleID',w.DWORD),
                    ('cntThreads',w.DWORD),('th32ParentProcessID',w.DWORD),
                    ('pcPriClassBase',w.LONG),('dwFlags',w.DWORD),('szExeFile',w.WCHAR*260)]
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.CreateToolhelp32Snapshot.argtypes=[w.DWORD,w.DWORD];k.CreateToolhelp32Snapshot.restype=w.HANDLE
    k.Process32FirstW.argtypes=[w.HANDLE,ctypes.POINTER(PROCESSENTRY32W)]
    k.Process32NextW.argtypes=[w.HANDLE,ctypes.POINTER(PROCESSENTRY32W)]
    k.CloseHandle.argtypes=[w.HANDLE]
    handle=k.CreateToolhelp32Snapshot(2,0)
    if handle==ctypes.c_void_p(-1).value: raise SafetyError('Unable to check whether Fallout 76 is running')
    try:
        p=PROCESSENTRY32W();p.dwSize=ctypes.sizeof(p)
        ok=k.Process32FirstW(handle,ctypes.byref(p))
        if not ok:raise SafetyError('Unable to enumerate running programs')
        while ok:
            if p.szExeFile.lower() in ('fallout76.exe','project76_gamepass.exe','project76.exe'): return True
            ok=k.Process32NextW(handle,ctypes.byref(p))
        return False
    finally:k.CloseHandle(handle)

@contextmanager
def game_guard(executable, expected_hash=None):
    """Deny opens of the verified executable during a modifying transaction."""
    if game_running(): raise SafetyError('Close Fallout 76 before continuing')
    if os.name != 'nt':
        yield
        return
    from ctypes import wintypes as w
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.CreateFileW.argtypes=[w.LPCWSTR,w.DWORD,w.DWORD,ctypes.c_void_p,w.DWORD,w.DWORD,w.HANDLE]
    k.CreateFileW.restype=w.HANDLE;k.CloseHandle.argtypes=[w.HANDLE]
    handle=k.CreateFileW(str(executable),0x80000000,0,None,3,0x80,None)
    if handle==ctypes.c_void_p(-1).value:
        raise SafetyError('The game executable is in use. Close the game and pause game updates')
    try:
        if expected_hash is not None:
            k.ReadFile.argtypes=[w.HANDLE,ctypes.c_void_p,w.DWORD,ctypes.POINTER(w.DWORD),ctypes.c_void_p]
            buffer=ctypes.create_string_buffer(1024*1024);count=w.DWORD();h=hashlib.sha256()
            while True:
                if not k.ReadFile(handle,buffer,len(buffer),ctypes.byref(count),None):
                    raise SafetyError('Unable to verify the locked game executable')
                if not count.value:break
                h.update(buffer.raw[:count.value])
            if h.hexdigest()!=expected_hash:raise SafetyError('Game executable changed before the write lock was acquired')
        yield
    finally:k.CloseHandle(handle)

@contextmanager
def operation_lock(path):
    """OS lock releases on process death; the harmless lock file is retained."""
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a+b') as f:
        if f.tell()==0:f.write(b'\0');f.flush()
        f.seek(0)
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError as e:raise SafetyError('Another KKS operation is already running') from e
        try:yield
        finally:
            f.seek(0)
            if os.name=='nt':msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
            else:fcntl.flock(f.fileno(),fcntl.LOCK_UN)

def discover():
    candidates=[];steam=[]
    if os.name=='nt':
        import winreg
        for hive,key,value in [
            (winreg.HKEY_CURRENT_USER,r'Software\Valve\Steam','SteamPath'),
            (winreg.HKEY_LOCAL_MACHINE,r'SOFTWARE\WOW6432Node\Valve\Steam','InstallPath')]:
            try:
                with winreg.OpenKey(hive,key) as k:steam.append(Path(winreg.QueryValueEx(k,value)[0]))
            except OSError:pass
        for hive in [winreg.HKEY_LOCAL_MACHINE,winreg.HKEY_CURRENT_USER]:
            for key in [r'SOFTWARE\Bethesda Softworks\Fallout76',r'SOFTWARE\WOW6432Node\Bethesda Softworks\Fallout76']:
                try:
                    with winreg.OpenKey(hive,key) as k:candidates.append(Path(winreg.QueryValueEx(k,'Installed Path')[0]))
                except OSError:pass
    steam += [Path(os.environ.get('ProgramFiles(x86)','C:/Program Files (x86)'))/'Steam']
    for base in list(steam):
        file=base/'steamapps/libraryfolders.vdf'
        if file.is_file():
            text=file.read_text('utf8',errors='replace')
            steam += [Path(x.replace('\\\\','\\')) for x in re.findall(r'"path"\s*"([^"]+)"',text)]
    for base in steam:
        manifest=base/'steamapps/appmanifest_1151340.acf'
        if manifest.is_file():
            match=re.search(r'"installdir"\s*"([^"]+)"',manifest.read_text('utf8',errors='replace'))
            if match and '/' not in match[1] and '\\' not in match[1]:candidates.append(base/'steamapps/common'/match[1])
        candidates.append(base/'steamapps/common/Fallout76')
    if os.name=='nt':
        for drive in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            for name in ('Fallout 76','Fallout76'):
                candidates.extend([Path(f'{drive}:/XboxGames')/name/'Content',Path(f'{drive}:/XboxGames')/name])
    found=[];seen=set()
    for path in candidates:
        if (path/'Fallout76.exe').is_file() and (path/'Data').is_dir():
            resolved=path.resolve();key=str(resolved).casefold()
            if key not in seen:found.append(str(resolved));seen.add(key)
    return found
