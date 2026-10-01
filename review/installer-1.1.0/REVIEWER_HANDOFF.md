# KKS independent installer — reviewer handoff

**Status:** prepared for Nexus manual review; source publication authorized by the maintainer. Nexus approval is not established.

**Later compatibility release:** [content 1.0.1](../content-1.0.1/README.md)
targets Steam build 25636769 using the same installer EXE and the same five mod
files. The original review pass and hashes below remain historical evidence.

Installer **1.1.0**; content **1.0.0 revision 1**, Steam English build 25258219.
User accepted the unchanged content in-game on NOIRBLACK before this cleanup.
This pass leaves that live installation intact. Nexus approval is not established.

**Exact source commit:** `5c6eadf80ebcec84b62a8c5bec71f7679d9f3004`  
**Review branch:** `release/review-hardening` (later documentation commits do not change the binary source revision above)  
**KKSInstaller.exe SHA-256:** `4e79031ef37c83dc730ff49de46cdfb21d8b326b58ba7a8e0fdb259f96baf17d`  
**KKS_1.0.0_Payload_Steam_EN_25258219_r1.zip SHA-256:** `cdb2387e90f9ce01b2ef1dd44036bfe0cf0c58e1405a99ea94bbe8970c06191b`  
**Signed manifest SHA-256:** `86d84fb18ad653a002939830802e3f43be46470075688d61e8e4bb42d442c576`

## Architecture and cleanup

The offline Windows application validates complete signed content ZIPs, checks
the game baseline, backs up original files and writes only the five allowed game
targets. An outer journal coordinates content updates; an inner transaction
engine replaces individual files and recovers interruptions. Ordinary compatible
content updates and skipped versions do not require a new EXE. New formats,
executable behavior or trust keys require an application update.

The pass expanded dense code, removed confirmed unused code, made the public
legacy restore descriptor readable without changing a byte, corrected stale
internal version metadata and clarified two validation expressions. It added a
current security/source map, locked all build wheels, and recorded exact-source
build provenance. Formatting was committed separately and all 22 initial Python
syntax trees were identical. Safety checks, archive algorithms, compatibility,
UI behavior and recovery architecture were preserved. **No user-facing change was
intentionally introduced.** The pre-change audit explains retained complexity.

## Validation results

- **112/112 automated test methods passed**, retaining all 59 original tests.
  Full suite passed after cleanup and in both clean source builds; many methods
  contain multiple adverse cases and interruption points.
- **29/29 actual-EXE checks passed** on a disposable copy of real game files:
  clean install, exact released output, cached repair, damaged-cache refusal,
  restore without payload assets, reimport, forced process-tree termination after
  a real archive write and exact recovery, original 1.0 migration, wrong package/
  target refusal and all five altered game fingerprints. Copy restored exactly;
  live game unchanged.
- Signed/unsigned malformed packages, traversal/alias/ADS/absolute paths, links,
  schema/signature/hash/size failures, backup failures, low space, locks,
  tampered receipts/journals, skipped releases and updated game baselines are
  covered by regression tests. Unknown changes block writes/recovery.
- All **five package payloads are byte-identical to released 1.0**, and the five
  installed output hashes match the frozen release. All **95 frozen production
  inventory files** are unchanged. The existing ZIP was not regenerated/resigned.
- All **12 packaged application modules** match code compiled from the named
  source commit. Bundle inspection found no KKS payload, publisher tooling,
  tests, private signing key or game archives. PE requests `asInvoker`.

Complete method IDs/check names are in TEST_RESULTS.json; build/test logs and
source/binary verification are in this review directory. Published build logs
replace workstation paths with placeholders; original log hashes are retained.
Private live-machine reports are summarized rather than redistributed. The new executable was exercised through its CLI; GUI logic is
syntax-tree-identical to the previously accepted build. No new gameplay session
was claimed for this cleanup binary, and no physical power-loss test was run.

## Security and operating scope

**Packages:** Ed25519 authenticates the exact manifest using a compiled public
key; every asset has a signed SHA-256 and size. Strict bounded ZIP/JSON validation
and fixed path/member/operation allowlists reject executable hooks and arbitrary
write instructions. Assets are data to this installer, not evaluated code. The
game consumes the SWF/font format, so trusted publisher custody still matters.

**Network/processes:** no application download, telemetry, socket-client, shell
command or helper-launch feature. PyInstaller's one-file bootloader extracts its
runtime and starts its own child. OS discovery/dialog access to remote paths and
Windows reputation checks can cause OS network traffic. Source inspection, not
a packet-capture certification, supports these statements. Build/test tools use
subprocesses and are excluded from the EXE.

**Privileges:** no elevation request; PE is unsigned (`NotSigned`). Read/write
permission is needed for the selected game folder. Tests ran in an administrator
session; protected-folder access under every standard account is not established.

**Reads/writes:** reads the chosen ZIP, fixed game identity/target files, Steam
discovery data and saved KKS state. Writes two interface archives (one named
member each), three English strings tables, and `.kks-manager` state/cache/
backups/staging/history. Recognized legacy state can be updated during migration.
No EXE/ESM/localization-archive/INI changes. OS temporary runtime files and explicit
user-selected JSON report paths are additional write locations. Detailed paths
and code entry points are in [SECURITY_REVIEW.md](../../SECURITY_REVIEW.md).

**Recovery:** verified immutable originals retain originally absent files as
absence. Repair uses authenticated cache; Restore uses descriptors and backups
without the old EXE or payload. Journals support error rollback/next-run recovery;
foreign files, missing backups or incompatible game changes stop the operation.
Backups/history are retained. Game updates never receive stale original archives.

## Reproduction and remaining caveats

Both clean builds of the exact commit, from **different source/work directories**,
produced the identical EXE hash above. Build settings: Python 3.12.14 x64,
Tcl/Tk 8.6.12, PyInstaller 6.22.3, locked wheel hashes, `PYTHONHASHSEED=1`,
`SOURCE_DATE_EPOCH=1790876010`, no UPX.
Follow [BUILD.md](../../BUILD.md), checking out the exact build commit above; compare the receipt, source archive and 1,009-entry runtime
inventory. The base Python runtime came from the local Codex environment.
Cross-machine reproduction with another Python distribution is untested;
interpreter/Tk/system DLL differences or later signing can change the binary.
Same-machine repeatability and source-to-bundle code equality are demonstrated;
these receipts are not independent attestation.

Path checks and locks do not sandbox a hostile local administrator racing the
filesystem. Process-interruption recovery is tested; abrupt storage/power failure
has separate durability limits. English Steam and the fixed archive profile are
the current supported scope. The signed package retains its original `candidate`
QA label to preserve its bytes; later human acceptance is separate evidence.
Publisher DPAPI key protection remains in place. Encrypted recovery backups were
created and independently tested on October 1: the downloaded copy decrypted to
the expected public key and passed a signing test without using the original
DPAPI key. No private key, encrypted key backup or passphrase is included here.

Source publication is authorized. Nexus uploads and the support email are being
prepared for the maintainer; their submission is a separate step. Separate
application/content downloads preserve the installer/content separation.
Upstream notices accompany the application.
