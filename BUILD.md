# Build the independent installer candidate

This branch builds installer application **1.1.0**, separate from content version **1.0.0**. Use the `v1.0.0` source snapshot and its original instructions to rebuild the original bundled executable.

Requirements: Windows x64, Python 3.12 x64 with Tk/Tcl, and the pinned packages in `source/requirements-build.txt`. This candidate uses Python 3.12.14, PyInstaller 6.22.3 and cryptography 50.0.2. Dependencies require internet at build time; the app has no network feature. No game installation or signing private key is required to build or run synthetic tests.

From the repository root in PowerShell:

```powershell
Set-Location source
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe -c "import tkinter; print(tkinter.Tcl().eval('info patchlevel'))"
.\build.ps1 -Python "$PWD\.venv\Scripts\python.exe"
```

The script runs all 110 tests and stops on failure, then builds `app/KKSInstaller.exe`. Do not accept a build that omits Tk/Tcl. After tests pass, its equivalent packaging command is:

```powershell
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --windowed --name KKSInstaller --distpath ..\app --workpath build\pyinstaller --specpath build launcher.py
```

There is no `--add-data release;release`. The app includes its runtime, public verification key and small pinned 1.0 restoration descriptor; no mod payload, game archives or private key. Rebuilding does not guarantee a byte-identical EXE across environments.

Read-only CLI examples (replace paths):

```powershell
.\app\KKSInstaller.exe --version --report .\version.json
.\app\KKSInstaller.exe --verify-package --package 'D:\Downloads\KKS_Content.zip' --report .\package-check.json
.\app\KKSInstaller.exe --check --game 'D:\SteamLibrary\steamapps\common\Fallout76' --package 'D:\Downloads\KKS_Content.zip' --report .\game-check.json
```

`--check` uses temporary verification storage and creates no game-side state. `--install`, `--repair`, `--restore` and `--recover` modify files; test them on disposable copies. Windowed builds write to the explicit JSON report path and return 0 for success or 1 for a blocked operation.

See [INDEPENDENT_INSTALLER.md](INDEPENDENT_INSTALLER.md) for package creation, custody, state, compatibility and review boundaries.
