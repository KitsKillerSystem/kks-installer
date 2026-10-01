# Independent installer 1.1.0 — reviewer entry point

Application and content have separate versions. The first signed package contains
unchanged KKS 1.0.0. This branch is an unpublished review candidate. Historical
root-level 1.0 reports/checksums describe the original bundled release; the new
release's REVIEWER_HANDOFF.md, SHA256SUMS.txt and build-receipt.json identify its
exact source and binary. No Nexus approval is claimed.

## Read the code in this order

| Stage | Source / responsibility |
|---|---|
| Start / choose | `source/launcher.py`, `kks_installer/ui.py`: CLI or Tk UI, explicit package and operation selection |
| Authenticate / import | `packages.py`: bounded ZIP reader, strict JSON, compiled publisher key, signature and payload hashes; verified cache publication |
| Compatibility / transition | `manager.py`: fixed game root, current ownership, baseline and release sequence, outer restore/install journal |
| Back up / write / verify | `managed_engine.py`, `engine.py`, `ba2.py`: strict receipts, immutable originals, staged outputs, five-file replacement and verification |
| Recover | `Manager.recover`, `Installer._rollback`: reconcile journal with known current hashes; refuse foreign changes |
| Windows boundary | `platforms.py`, `windows_drop.py`: path/link checks, process enumeration, exclusive game handle, locks, Steam discovery and file drop |

The outer manager coordinates content versions and game-baseline changes. The
inner transaction engine handles the five files. Their separate journals and
repeated checks protect different commit boundaries. `engine.Release` and
`profile.py` remain for historical regression tests. Current entry points never
select that bundled-package reader; legacy restoration uses the pinned public
`_legacy.py` descriptor, with no old mod payload embedded.

## Filesystem scope

The only game assets the signed-package profile can replace are:

- `Data/SeventySix - Interface_en.ba2`: only `interface/fonts_en.swf` changes.
- `Data/SeventySix - Interface.ba2`: only `interface/fontconfig_en.txt` changes.
- `Data/strings/seventysix_en.strings`, `.dlstrings`, `.ilstrings`.

The EXE, `Data/SeventySix.esm` and `Data/SeventySix - Localization.ba2` are identity
inputs, never write targets. Both original archives and their named members are
verified before constructing replacement archives. Unrelated archive members
are preserved. The installer does not modify INIs, other mods or game launchers.

The application reads the selected ZIP; signed cached descriptors/payloads;
receipts/journals/backups; the fixed game files; possible conflicting loose font
files; Steam registry entries and library/app manifests for discovery. It can
inspect existing `.kks-*` state directories to reject conflicting ownership.

Persistent writes live under the selected game's `.kks-manager`: verified package
cache, content-addressed descriptors, installation state, immutable baselines and
backups, receipts, journals, history, preflight/staging files and retired override
copies. Migration/restoration can also update the recognized legacy
`.kks-installer-1.0.0` receipts/journals/transaction files. Nothing installs a
service, scheduled task, registry value or autostart entry. Backups/history and
failed staging may consume disk space and are not automatically pruned.

Additional writes: PyInstaller unpacks its bundled Python/Tk/native runtime in the
OS temporary directory; read-only package checks use temporary verification
storage; the optional CLI `--report PATH` explicitly writes a JSON report at the
user-chosen path, including creating its parent directories. That report path is
not restricted to the game directory and should not be pointed at valuable files.

Game/package/state names are fixed allowlists or validated local identifiers.
`safe_path` rejects absolute paths, traversal, Windows alternate streams,
symlinks/reparse points and hardlinked regular files. Manager also rejects linked
game-root ancestors. ZIPs are streamed into generated staging paths, not extracted
with package-selected general destinations. Receipts cannot invent write targets.
These checks are not a sandbox against a malicious local administrator or a
process deliberately racing directory replacements. Run only with the access
needed for the chosen game folder.

## Package trust and integrity

Exactly five assets plus `manifest.json` and `manifest.sig.json` are permitted;
three empty structural directory entries are optional. No scripts, DLLs, EXEs,
nested archives, arbitrary operations or install hooks are accepted. Ed25519
verifies a domain-separated signature of the exact manifest bytes against a key
compiled into `_application.py`; the ZIP cannot supply its own trusted key.
The Python test harness injects fixture keys, but no user/package key override is
exposed by the shipped CLI or GUI. Private publishing keys never ship.

The parser rejects unknown fields, duplicate JSON keys, non-finite numbers,
unsupported schema/API/writer/platform/language, bad versions, duplicate/aliased
paths and ZIP structural inconsistencies. Entry count, central directory,
compressed/uncompressed sizes and JSON depth are bounded. Every payload is
streamed with a signed size limit and SHA-256 check. Cache reads are revalidated;
identity, original-member and completed-file hashes are checked at write/recovery
boundaries. Game support is currently Steam English with certified exact file
fingerprints, not just a display version string.

The installer treats font SWF/configuration/strings as bytes and never evaluates
them, invokes them or imports them as code. The game consumes these formats; a
publisher signature authenticates the author, not the safety of arbitrary font
content or the absence of bugs in the game's parsers. New data within the current
profile can ship without rebuilding the app; new executable behavior, formats or
trust keys require a new app. Complete packages allow skipping intermediate
content versions. Downgrades and conflicting reused release identities fail.

## Network, processes and privileges

There is no application download, update fetch, telemetry, HTTP/socket client,
shell invocation or external helper command. Discovery and file dialogs can cause
OS network access when Steam libraries or user-selected paths are remote. Windows
security/reputation checks are also outside application control; this is not a
claim of zero machine-wide network traffic.

PyInstaller's one-file bootloader extracts runtime files and starts its own child
process. Windows process enumeration checks whether Fallout 76 is running; an
exclusive handle prevents normal game startup while writes run. No game is
launched. The build/test tooling uses subprocesses, including crash-test workers;
it is not bundled. `build_content.py` is publisher-only tooling using local DPAPI
for key custody, not an installer entry point.

The executable requests `asInvoker`, with no UAC elevation request or privilege
escalation code. It needs write access to the selected game's managed files and
state directory. A protected Steam folder may require the user to choose an
appropriately authorized account/session. Development/testing here occurred in
an administrator session; that does not establish that every protected install
will work under a standard account. The PE is not Authenticode-signed; the content
signature is separate from Windows executable signing.

## Backups, repair, restoration and failure

All needed originals and complete output candidates are verified before replacing
game files. Original absence of loose strings is recorded as absence. Atomic
same-volume file replacements and flushed journals allow recovery between files;
five-file installation is not one filesystem-wide atomic operation. Process
death is tested. Windows directory metadata is not explicitly flushed; physical
power-loss/storage-failure durability is not guaranteed by these tests.

Repair uses authenticated cached assets and verified originals. Restore requires
signed descriptors and installation-specific originals, but not the content ZIP,
its cached assets or the old executable. Missing/damaged backups or unknown game
changes block the operation. Ordinary errors attempt rollback; abrupt termination
leaves a journal for the next Recover action. Unknown external modifications are
preserved and require user resolution, not guessed at or overwritten.

When a certified game update replaces the baseline, the manager never restores
old archives over new ones. It retires only loose overrides it can prove belong
to the prior installation, retains evidence, records new originals and installs
against the new certified baseline. No automatic backup deletion occurs.

## Validation and release evidence

The build runs all 112 unittest methods (including 59 original tests and their
subcases) before packaging. Tests cover complete/skipped updates, changed game
baselines, exact restore, malformed packages, path/link and state tampering,
space/write failures, locks, interruptions in installation, upgrade and recovery,
and subprocess death. Two additional tests pin the readable legacy descriptor to
the original released bytes and confirm it remains restore-only.

The release handoff records additional actual-EXE tests on disposable real game
files, exact five-payload/output parity, frozen production preservation and clean
build reproduction results. Finite tests support these guarantees within the
stated model; they are not a proof against all OS/filesystem races. See
[BUILD.md](BUILD.md) for reproduction and [audit/REVIEW_HARDENING.md](audit/REVIEW_HARDENING.md)
for the pre-change audit and deliberately preserved complexity.
