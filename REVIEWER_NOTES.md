# KKS 1.0.0 — review notes

## Artifact under review

Nexus mod: https://www.nexusmods.com/fallout76/mods/4301

Uploaded file label: **KKS 1.0.0 Installer**. Original distribution filename: `KKS_1.0.0_Installer.zip`.

- ZIP: b3bc19c512a9c1a31a1574a645dffc968ca86796e390b4535fe10a809dc4f682
- KKSInstaller.exe: a268b56e497462c88bf5d4f62fd5a2f1c51c1352e33a2627dc0e9d5c383dd94d
- Embedded manifest: dda35c73a9c1119010a3a7c2d15517df2457b231d894e2b910dd34f1d5afd3e7

The ZIP contains the EXE and five documentation/checksum files, with no nested ZIP. The EXE is a PyInstaller single-file Windows application containing its Python runtime, Tk/Tcl, application modules and data. The exact quarantine trigger has not been established from the notice; these notes do not assert a false positive or a clean scan result.

## Code map

| File | Role |
| --- | --- |
| `source/launcher.py` | GUI/CLI entry point, explicit JSON report output and manifest selection. |
| `source/kks_installer/ui.py` | Tk interface; installation work runs in a background thread. |
| `source/kks_installer/profile.py` | Exact allowed target paths, baseline identity files and prior-state conflicts. |
| `source/kks_installer/engine.py` | Hash verification, backups, staging, journal, install/repair/restore and recovery. |
| `source/kks_installer/ba2.py` | Strict version-1 GNRL BA2 parsing/replacement and output verification. |
| `source/kks_installer/platforms.py` | Read-only installation discovery, safe-path checks, process enumeration and file/operation locks. |
| `source/kks_installer/_release.py` | Trusted release-manifest SHA-256. |
| `source/release/manifest.json` | Supported baseline, exact managed paths and expected before/after hashes. |

## Application behavior

The application contains no network request/update, telemetry, credential collection, startup registration, service installation or registry-write feature. Build-time `pip` installs PyInstaller; that is separate from runtime behavior. The program does not modify ESM or INI files, launch the game, or write to game-process memory.

Installation discovery reads Steam/Bethesda registry values and Steam library/app manifests, then checks standard candidate directories. Windows `ctypes` calls enumerate process names to detect a running game and open/hold a verified executable file handle to prevent launch/update during a transaction. These are file and process-list checks, not remote-process injection.

PyInstaller's one-file bootloader extracts bundled runtime files to a temporary directory. The application creates its staging/backups/receipt/journal under the selected game root's `.kks-installer-1.0.0` folder. An explicitly requested CLI report may be written to its user-supplied path. It does not silently enable elevated privileges; filesystem permission errors remain errors.

## Exactly what is installed

1. Replace `interface/fonts_en.swf` inside `Data/SeventySix - Interface_en.ba2`.
2. Replace `interface/fontconfig_en.txt` inside `Data/SeventySix - Interface.ba2`.
3. Write the three supplied English tables at `Data/strings/seventysix_en.strings`, `.dlstrings` and `.ilstrings`.

Executable, ESM and Localization.ba2 fingerprints are checked read-only. Before/after whole-file hashes and embedded asset hashes must match the pinned descriptor. Other BA2 members are preserved and checked. No alternative custom archive or loose font override is installed.

## Restoration and failure behavior

Verified originals are stored under content-addressed backup filenames and retained after restoration. The receipt distinguishes a preexisting vanilla loose table from a previously absent file. All backups and stages are prepared before game writes. Each replacement is atomic on the same volume; the set is protected by a durable recovery journal, not a single filesystem-wide atomic transaction. Unknown/concurrently changed files block rollback rather than being overwritten. Path traversal, symlinks/reparse points, hard links and mismatched metadata fail closed.

Unknown or changed game identities/targets prevent stale-backup restoration. A newer Bethesda build must be verified through Steam and supported by a newly reviewed KKS profile. Backups cannot be used to downgrade it.

## Validation evidence and limits

The sealed release passed 59 fixture tests, actual-EXE install/repair/restore tests on disposable real game copies, simulated interruption/recovery and stale-build refusal checks. The author approved final in-game QA of the identical game payload. The copied test sources are supplied here; no real Bethesda executable/ESM/archive is necessary to run them. `source/tests/test_future_restore.py` is a test-only proof of future restoration support and is not imported by the runtime.

Runtime source and all five embedded assets are byte-identical to the sealed release snapshot. Repository documentation and file inventories were added for review. No changes have been made to the quarantined EXE or ZIP. These checks are evidence for a reviewer, not a substitute for Nexus's review or an antivirus determination.
