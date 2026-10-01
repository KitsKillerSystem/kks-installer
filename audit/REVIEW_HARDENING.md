# Review before cleanup — 2026-10-01

Reviewed starting revision: `45be02d846b05a0e25630c370ce94d2c937500b9`.
Scope: application, package parser, filesystem/BA2 writer, persistent state and
recovery, Windows integration, publisher/build tools, and all regression tests.
This is a maintainer audit assisted by Codex, not independent security certification.
The accepted application and content architecture remain frozen.

## Findings and decisions

| Finding | Treatment | Reason / risk boundary |
|---|---|---|
| Dense one-line branches, semicolons and compressed expressions throughout source and tests | Format in a separate commit; compare parsed Python syntax trees before/after | Makes validation order and exception boundaries visible without changing execution |
| Public legacy restoration manifest encoded as an opaque base64 line | Replace with readable byte literals; assert exact original bytes and digest | No new resource lookup, schema change or alteration of authenticated restoration data |
| Stale package `__version__` | Use the existing application version constant | Corrects internal metadata; visible application version remains 1.1.0 |
| Unused import, descriptor flags, fingerprint method and obsolete `_release.py` constant | Remove after checking all tracked references | No executed validation or compatibility path is removed |
| Generator used only to throw a JSON-number error; nested ZIP size ternary | Use conventional named callback and explicit branches | Preserve error type/message, size limits and validation order |
| Large manager and repeated checks | Preserve | Outer content transitions and inner five-file transactions have different durable journals; repeated checks defend each write/recovery boundary |
| Historical bundled `Release` reader and `profile.py` | Retain, label their regression-fixture purpose | Original regression tests exercise released 1.0 behavior. Runtime entry points use signed packages/ManagedEngine; removing these tests would weaken compatibility evidence |
| Legacy restore/migration path | Preserve | Existing 1.0 users need it; no old executable or payload is required to restore verified originals |
| Small validation helpers / strict state fields | Preserve | Input and saved state are untrusted, including values that normal GUI operation cannot generate |
| Crash-injection hooks | Preserve | They exercise interruptions at real durable boundaries and are not exposed as user/package execution hooks |
| Review/build documents mix current and historical evidence | Add a current security/source map and exact-build instructions | A reviewer should not need the development conversation or mistake historical hashes for the new executable |
| Build pins cover only part of the dependency closure | Pin full wheel closure and deterministic build settings; record environment/source/output hashes | Build-only change; verify two clean builds instead of asserting reproducibility from configuration alone |

No reviewed finding currently requires a runtime architecture change. No safety
check is slated for removal. Formatting and the limited semantic cleanup will be
separate commits. The complete suite and disposable real-file EXE tests must pass
before the new binary is described as ready for review.

## Security review boundaries

Trace `launcher.py` / `ui.py` → `Manager.select` → `import_package` /
`SignedRelease` → `Manager.run` → `ManagedEngine` / `Installer` → `BA2.replace_to`.
Follow `Manager.recover` and `Installer._rollback` for interrupted operations.
See `platforms.py` for path checks, game exclusion, locking and discovery.

Package-controlled file names are fixed allowlists, not general extraction paths.
Signatures authenticate publisher data; they do not sandbox a malicious publisher
or vulnerabilities in the game that consumes font assets. Static path checks and
locks are not a security boundary against a hostile local administrator racing
filesystem changes. Explicit report paths and OS runtime temporary files are
outside the five game-target paths and must be documented separately.

The application has no download, telemetry, shell-command or external-helper
feature. PyInstaller's one-file bootloader starts its own child process and
extracts bundled runtime files. OS dialogs and user-selected remote paths may
perform OS network I/O. Tests and publisher/build tools must be distinguished
from the shipped runtime when describing process and network behavior.

## Acceptance requirements

Retain the original 1.0 content ZIP byte for byte; verify all five payloads and
resulting game files against the frozen release. Exercise malformed signed and
unsigned inputs, path/link refusals, repair, restore, skipped content versions,
new game baselines and interruptions. Keep the live accepted installation and
all previously accepted artifacts untouched. Publish nothing externally as part
of this pass. Store final build/test evidence with the release candidate.
