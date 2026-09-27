# Build KKS 1.0.0 on Windows

## Requirements

- Windows x64.
- Python 3.12 x64 with `venv`, `pip` and Tk/Tcl. The released executable was built using Python **3.12.14** and PyInstaller **6.22.3**. Other build environments can produce a different executable hash.
- Internet access for the development-only dependency installation below. The installed KKS application has no runtime network feature.

No Fallout 76 installation, xTranslator, font editor or localization compiler is required to build the EXE. The exact release inputs are already included in `source/release/`.

## Build steps

Download this repository using GitHub's **Code → Download ZIP**, extract it, and open PowerShell in the extracted repository folder containing this file. With the intended Python 3.12 interpreter available as `python`, run:

```powershell
python --version
Set-Location source
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe -c "import tkinter; print(tkinter.Tcl().eval('info patchlevel'))"
if ($LASTEXITCODE -ne 0) { throw 'Python Tk/Tcl is unavailable; repair the Python installation before building.' }
.\build.ps1 -Python "$PWD\.venv\Scripts\python.exe"
```

The build script runs the 59 fixture tests first and stops if they fail. It then packages `launcher.py`, its application modules and the `release` directory with PyInstaller's Windows, single-file GUI mode. The output is **`app/KKSInstaller.exe`**, relative to the repository root. End users do not install the build dependencies.

The Tk/Tcl check must succeed before packaging. Stop if PyInstaller warns that the tkinter installation is broken or excludes tkinter; that would not be a complete GUI build. Repair the Python installation with its Tk/Tcl component selected and retry. The released EXE already embeds this component.

If local PowerShell policy prevents running the reviewed `build.ps1`, the equivalent commands below perform the build without changing that policy. Run them from `source` after creating the environment and installing requirements:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'Tests failed; stop here.' }
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --windowed --name KKSInstaller --add-data "$PWD\release;release" --distpath ..\app --workpath build\pyinstaller --specpath build launcher.py
if ($LASTEXITCODE -ne 0) { throw 'Build failed.' }
```

## Read-only verification

The fixture tests use temporary synthetic game files. They do not need a game installation. Rebuilding the application does not install KKS or alter the game.

For an optional check of an actual game installation, from the repository root:

```powershell
.\app\KKSInstaller.exe --check --game 'D:\SteamLibrary\steamapps\common\Fallout76' --report .\check-result.json
```

Replace the example path with your own game folder. `--check` performs compatibility checks; it does not patch game files. The JSON result is written to the explicit report path. Actual Install/Repair/Restore/Recover operations must be tested only on appropriate copies or a deliberately chosen supported installation.

## Integrity and reproduction scope

The release manifest SHA-256 is `dda35c73a9c1119010a3a7c2d15517df2457b231d894e2b910dd34f1d5afd3e7` and is pinned in `source/kks_installer/_release.py`. The engine checks every bundled payload against that manifest. Preserve the manifest and payload bytes; do not re-save them through an editor, change line endings, or regenerate the assets for this review.

This reproduces the executable's source and embedded inputs. It does not promise a bit-for-bit identical EXE: PyInstaller bootloader/build metadata and dependency versions can differ. The original artifact hashes are in RELEASE_SHA256SUMS.txt. Rebuilding is separate from replacing the already uploaded Nexus artifact; keep that original for review.
