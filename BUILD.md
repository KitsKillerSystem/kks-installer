# Build installer application 1.2.1

Content version 1.1.0 is independent. Use the original `v1.0.0` source to reproduce
the older bundled installer. This branch's runtime build never includes
`source/release`, publisher tooling, tests, game files or private signing keys.
No game installation or publisher key is needed for synthetic tests or building.

The [1.2.1 build receipts](review/installer-1.2.1/README.md) identify exact source
commit `3d65c7df0ca28b638d416dbab0392155022a6d9b`, tree, executable and tests.
The `installer-v1.2.1` tag identifies that build commit. Historical 1.1.0 was built from
`5c6eadf80ebcec84b62a8c5bec71f7679d9f3004`; its executable and review evidence
remain frozen. Use the receipt for the executable you intend to reproduce.

## Reproduce the reviewed source

Use Windows x64, Git, Python **3.12.14 x64 with Tk/Tcl**, and a fresh checkout of the
full source commit printed in the release's build-receipt.json.
The recorded environment used Tcl/Tk **8.6.12**, PyInstaller **6.22.3** and
cryptography **50.0.2**. The complete Windows/Python-3.12 wheel closure, including
pip, is pinned with SHA-256 hashes in `source/requirements-build.txt`.

In PowerShell, from the repository root (replace the example commit/path):

```powershell
git checkout --detach <full-reviewed-commit>
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes --only-binary=:all: -r source\requirements-build.txt
.\.venv\Scripts\python.exe -c "import sys, tkinter; print(sys.version); print(tkinter.Tcl().eval('info patchlevel'))"
.\source\build.ps1 -Python "$PWD\.venv\Scripts\python.exe" -Destination C:\KKSBuild\run1\app -BuildDirectory C:\KKSBuild\run1\work
```

Both output directories must be new. The script rejects uncommitted/untracked
source, checks Python/dependency versions, runs all **138** tests, then invokes
PyInstaller with `--clean --noupx --onefile --windowed`. A failed step stops the
build. Accept the output only when `build-receipt.json` exists and logs pass;
a partially created EXE alone is not success. Do not edit source during a build.
Use a fresh checkout and venv to avoid ignored/local modules or extra packages.
Git's commit time sets `SOURCE_DATE_EPOCH`, and `PYTHONHASHSEED=1` fixes Python hash
ordering; the script clears inherited Python import-path overrides in child
processes. The receipt records the command, source tree and every tracked-file
hash, interpreter/platform/dependencies, logs and executable hash.

Repeat with new run2 output/work directories and compare:

```powershell
Get-FileHash C:\KKSBuild\run1\app\KKSInstaller.exe -Algorithm SHA256
Get-FileHash C:\KKSBuild\run2\app\KKSInstaller.exe -Algorithm SHA256
```

These controls follow [PyInstaller's reproducible-build guidance](https://pyinstaller.org/en/stable/advanced-topics.html#creating-a-reproducible-build).
The release handoff reports the actual two-build result, rather than promising
cross-machine identity. Published source/environment/hash receipts and full
test/build logs identify both clean builds. The source tag preserves the exact
reviewed revision; the later content release tag also includes release documentation.

## Limits of reproduction and provenance

Matching Python's version string alone does not guarantee matching interpreter,
standard library, Tcl/Tk, OpenSSL or Windows system DLL bytes. This build used
the Python 3.12.14 runtime provided by the local Codex environment (MSC v.1944,
64 bit); that provenance is disclosed, not assumed equivalent to every Python
3.12.14 distribution. The receipts record interpreter and dependency versions.
Independent builders can compare their runtime/module source and explain any
remaining differences. Different base runtimes/toolchains, system DLLs or later
Authenticode signing can change the binary. The current build is unsigned and
uses no UPX. Build receipts/checksums bind named artifacts to this recorded build;
they are not independent attestation or a code-signing certificate.

Dependency installation needs access to the Python package index unless wheels
are supplied locally. For offline building, download the locked wheels on an
online machine, verify with pip's `--require-hashes`, then install with
`--no-index --find-links <wheel-directory>`. The build/test/application themselves
have no dependency download step. Preserve the wheel files if long-term exact
reproduction matters. `source/review_build.py` is developer tooling and never
imports into the application.

## Run and check

```powershell
.\KKSInstaller.exe --version --report .\version.json
.\KKSInstaller.exe --verify-package --package D:\Downloads\KKS_Content.zip --report .\package-check.json
.\KKSInstaller.exe --check --game D:\SteamLibrary\steamapps\common\Fallout76 --package D:\Downloads\KKS_Content.zip --report .\game-check.json
```

Windowed builds use the explicit report file and return 0 for success or 1 for a
blocked operation. `--check` creates no game state (temporary package verification
and the requested report are still writes). `--install`, `--repair`, `--restore`
and `--recover` modify game files/state; validate on disposable copies.

To run only synthetic tests: `python -m unittest discover -s source/tests -v`
requires `source` on the import path; the simplest invocation is to change into
`source` and run `python -m unittest discover -s tests -v` with the locked venv.

Source style is Black 26.5.1, Python 3.12 target, line length 100; formatting tools
are optional development tools, not runtime/build dependencies. The initial
formatting commit was checked with exact AST equality for all 22 Python files.
Read [SECURITY_REVIEW.md](SECURITY_REVIEW.md) for the security scope and
[INDEPENDENT_INSTALLER.md](INDEPENDENT_INSTALLER.md) for publisher/package contracts.
