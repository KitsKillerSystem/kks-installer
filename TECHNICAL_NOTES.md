# KKS 1.0.0

Historical release record. The independent installer candidate is described in [INDEPENDENT_INSTALLER.md](INDEPENDENT_INSTALLER.md); it has a separate application version and has not replaced this release.

Promoted from the exact KKS 1.0.0-rc.1 payload that the user approved after final in-game QA. All five game payloads and the complete authoring/codex snapshot are byte-identical. No localization, glyph artwork, metrics, sorting, naming or content changes were made during promotion.

## Promotion scope

Installer title/header and CLI identity now say 1.0.0. Manifest and status metadata mark the payload as accepted. The state directory is `.kks-installer-1.0.0`, with rc.1 registered as a prior test version. An active prerelease still needs its own Restore vanilla before this first public release can install. Detection, BA2 writing, backup, Repair, Restore Vanilla, journal and recovery algorithms are unchanged. No upgrade feature or new persistent metadata format was added.

The manifest changes only `release`, `in_game_verified` and `qa_candidate`; its targets, game fingerprints and all expected output hashes are unchanged. `audit/RELEASE_CODE_DIFF.patch` records the production promotion diff, and `audit/PROMOTION_VERIFICATION.json` records byte equality. Added compatibility tests are developer-only and are not used by the shipped executable.

## Archive operations

The font replaces `interface/fonts_en.swf` inside `Data/SeventySix - Interface_en.ba2`. The UTF-8 custom-renaming config replaces `interface/fontconfig_en.txt` inside `Data/SeventySix - Interface.ba2`. Three loose English string tables use `Data/strings/seventysix_en.*strings`. The executable, ESM and Localization.ba2 are fingerprinted read-only. There are no ESM/INI edits, loose font overrides or custom load-after archives.

Only version-1 GNRL BA2 is supported. The writer preserves record order, names, opaque metadata, unrelated packed bytes and trailer. Staged archives are reopened and unrelated members compared. Installed whole-file hashes and embedded asset hashes must match the pinned manifest. Replacements are atomic per file on the same volume; a durable journal supports rollback/recovery across the set of files. The multi-file operation is not one filesystem-wide atomic transaction.

## Backups and future upgrades

Receipts already preserve the manifest identity, absolute game root, installed/restored status and each target's original/installed hash. Original bytes are retained in content-addressed backup files. These are sufficient for a future installer carrying a trusted 1.0.0 compatibility descriptor and compatible restoration code. Users need to preserve the state folder, not the old executable. See UPGRADE_RESTORATION.md for the complete contract, trusted manifest digest and newer-Bethesda-build refusal rules.

The existing installer checks all supported game fingerprints and known current target hashes before restoring. If files have changed to an unknown build, close Fallout 76 and verify/update through Steam; never force old backups over them. A future installer must enforce the same checks before beginning the old-release restoration transaction.

## Verification

59 fixture tests pass, including 11 added compatibility tests demonstrating restoration without the old payload directory, subsequent installation of a simulated new release, interrupted restore recovery, and refusal of changed game files, corrupt/missing backups or untrusted metadata.

TEST_RESULTS.json records tests of the actual release EXE on a disposable copy of real game files: prior rc.1 refusal, install, two-archive interruption/recovery, repair, exact restore, and newer-file refusal for the executable, ESM, localization archive and both Interface archives. The real archives were also restored by a test-only future compatibility reader with only the trusted manifest and persisted state. Production installation and restoration algorithms were not changed. Live game files and authoritative sources remain untouched.

Final in-game QA approval applies to the identical approved payload; the newly branded executable is covered by these file-level tests. Historical authoring notes retain their original RC labels. War Shrike research remains deferred. No Nexus publication was performed.
