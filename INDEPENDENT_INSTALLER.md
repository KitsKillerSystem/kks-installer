# Independent installer and complete content packages

Status: **Installer 1.5.0 / English Content 1.1.1**, 6 October 2026. The maintainer has accepted the modular architecture in game. See review/installer-1.5.0, review/content-1.1.1 and OPTIONAL_FEATURES.md for build, acceptance and optional-feature contracts.

## User workflow

Keep `KKSInstaller.exe`. Download one complete content ZIP, close Fallout 76, open the installer, select the game folder, and browse to the ZIP or drop it onto the window. A ZIP may also be supplied at launch or dropped onto the EXE. Keep the ZIP unopened. Selection verifies and caches it; the Install action starts game changes.

Application and content versions appear separately. The app compares the selected profile’s five or six payload hashes with the installed package. Complete packages permit A to E without B, C or D. Repair uses the authenticated cache. Restore needs the signed descriptor and original backups, but neither cached payloads, the downloaded ZIP nor the old EXE. Selecting the exact signed package again repairs damaged cached descriptors/payloads. Mod content cannot reconstruct missing original game backups.

The published content supports Fallout 76, Steam, English, six targets and BA2 version 1 GNRL. The app retains historical five-target profiles and certified DE/RU/FR package support; those language content packages are not published by this release. The initial content 1.0.0 package supports Slasher build 25258219; the [content 1.0.1 compatibility release](review/content-1.0.1/README.md) certifies build 25636769 with unchanged mod files and the same installer. Exact hashes govern compatibility, never display labels. Additional platforms, language packages and future Bethesda fingerprints need explicit certification/support. There is no network update service or automatic download-folder scanning.

## Package and trust contract

The original `fo76-steam-en-fonts-strings-v1` ZIP has exactly seven files; matching optional directory entries are allowed:

```text
manifest.json
manifest.sig.json
payload/interface/fonts_en.swf
payload/interface/fontconfig_en.txt
payload/strings/seventysix_en.strings
payload/strings/seventysix_en.dlstrings
payload/strings/seventysix_en.ilstrings
```

The new `fo76-steam-en-fonts-strings-translate-v2` profile requires the same complete set plus exactly `payload/interface/translate_en.txt` (maximum 4 MiB). It requires Installer 1.2.0 and the additional `interface-translate-en-v1` capability. Both profiles still write the same five game targets. The Interface archive's fixed member list expands from fontconfig alone to fontconfig plus translation; unrelated members remain unchanged. Old packages cannot smuggle an unlisted translation file into their ZIP.

Baseline fingerprints retain the original member pins so existing 1.1.0 saved installations remain compatible. Full original archive hashes already bind the translation member; its original member hash is also explicitly verified before a new-profile write. Restore uses the installed package's authenticated profile and original archive backups.

The corrected `fo76-steam-en-fonts-strings-localization-v3` profile requires Installer **1.2.1** and capability `localization-translate-en-v1`. It uses the same six payload paths, but installs translation in `Data/SeventySix - Localization.ba2`; Interface.ba2 returns to fontconfig-only. There are now six fixed game targets. The maintainer confirmed that this target displays the Known checkmark correctly in game. The new profile binds the Localization target’s original hash/size to its existing game identity; all other archive members remain exact.

Old baseline fingerprints remain stable. Five-to-six target upgrades preserve the original baseline and create a new immutable expanded record with the additional certified original. Current ownership, payload integrity, member hashes, whole-archive output hashes and interrupted-operation recovery all cover the sixth target. A future package that removes targets requires Restore vanilla first. Do not use older installers to manage a v3 installation.

Publisher: use `--translation-localization` with the current Localization archive’s English text; `--include-translation` remains the historical v2 authoring option. They are mutually exclusive. No existing signed package is overwritten.

Ed25519 signs `KKS-CONTENT-MANIFEST-v1\0` followed by the exact UTF-8 manifest bytes. The envelope selects a public key compiled into the app. Keys supplied by a package are never trusted. Initial key ID: `kks-release-2026-10`; only its public component is in `_application.py`.

The strict manifest binds content version/revision, monotonic sequence, installer API/minimum version/capabilities, fixed product/profile/platform/language, exact game identities, payload lengths/hashes, before/after target lengths/hashes, embedded asset hashes, baseline ID and QA report. Packages cannot add paths, commands, scripts or settings. The builder retains `qa.status: candidate` in signed metadata; public acceptance is recorded separately without changing the tested ZIP or its signature.

Validation bounds the central directory before allocating it. It rejects extra/duplicate/aliased paths, traversal, links, alternate streams, header disagreement, hidden/trailing data, encryption, unsupported compression, duplicate JSON keys, BOM and unknown schemas. Limits: 512 MiB ZIP/combined payload, 256 MiB per payload, 1 MiB manifest, 16 KiB signature, 11 ZIP entries. Streaming decompression checks signed lengths/hashes before publication to the cache. Failed `import-*` staging is untrusted and never selected as a release.

Content signatures establish the publisher key that authorized these bytes. They are not Windows Authenticode or Nexus approval. SWF is the existing game font container: describe the download as a **font/configuration/string data package without an installer executable or update script**, not a promise that every format is incapable of code. The app never executes package assets.

## Fixed operations and retained state

The app changes only the fixed members in the selected authenticated profile: the English font in Interface_en.ba2, fontconfig in Interface.ba2, the English translation in Localization.ba2 for v3 (Interface.ba2 for historical v2), and three English loose string tables. Fallout76.exe and SeventySix.esm remain read-only identities. Localization.ba2 retains its original identity pin and becomes a managed target only in v3. No ESM/INI edits, registry writes, game-process injection, startup registration, service, telemetry, network request or automatic privilege elevation is added.

| Module | Responsibility |
| --- | --- |
| `engine.py`, `ba2.py` | Original transaction engine and unchanged archive writer |
| `packages.py` | Strict package authentication and bounded import |
| `managed_engine.py`, `_legacy.py` | Strict state validation and restore-only pinned 1.0 compatibility |
| `manager.py` | Selection, update coordination, recovery and baseline reconciliation |
| `launcher.py`, `ui.py`, `windows_drop.py` | CLI, GUI and Windows file-drop adapter |
| `build_content.py` | Publisher-only certification/signing; excluded from runtime |

Each game's `.kks-manager` retains:

| Location | Meaning |
| --- | --- |
| `installation.json` | Root-bound ID, active/obsolete owners, sequence high-water mark and content/baseline registries |
| `packages/<manifest hash>/` | Signed descriptors and verified repair files |
| `baselines/<id>.json` | Immutable vanilla hashes and original loose-file presence |
| `installs/<id>/` | Receipts, backups, staging and phase journals |
| `pending.json` | Durable coordinator plan/phase |
| `history/<transaction>.json` | Completed/recovered operations |
| `quarantine/<transaction>/` | Old string overrides retired after a game update |
| `preflight/<transaction>/` | Verified candidate archive outputs |

History/backups have no automatic garbage collection; temporary/preflight records can accumulate. Do not delete state to bypass a refusal. Moving a game folder invalidates its absolute-root binding; there is no automatic rebinding. Local receipts are not a security boundary against an administrator rewriting all local history. Signatures and fixed path/hash allowlists constrain accepted game bytes.

## Updates and recovery

On the same game baseline, the app validates old restoration data and verifies new archive outputs **before** removing old KKS. It restores old KKS, verifies vanilla, installs the complete package, verifies outputs, publishes state and retires the journal. Original loose-file presence survives across versions. Replacements are atomic per file; the whole update is recoverable, not one atomic operation. Recovery can return the previous managed state, verified vanilla, or commit a completed new installation. Unknown external changes stop recovery with state retained.

After Bethesda changes the baseline, a newly certified package must match all three current identity files and **every archive in the selected profile**, including Localization for v3 before cleanup. Old ownership/backups must validate. Only old KKS loose overrides whose bytes match the authenticated old receipt may be quarantined and removed. New vanilla tables remain; unknown tables block all cleanup. No old archive/table backups are restored to the new build. The old owner becomes obsolete, with its historical receipt preserved rather than falsely marked restored. Interrupted cleanup recovers forward to new verified vanilla.

Returning users still need Steam's game files to match the package. Incomplete updates or unsupported fingerprints stop safely. Conflicting version/revision/baseline reuse and old release sequences are rejected. The exact highest installed sequence can be reinstalled after Restore. Downgrade controls are not implemented.

Released 1.0.0's `.kks-installer-1.0.0` is recognized by its built-in pinned descriptor, receipt and backups; restore/migration needs no old EXE or payload. Unknown prerelease experiments require their own safe restoration first. Stable/legacy locks, executable guards, path/link checks and repeated identity checks protect modifying operations.

## Publisher workflow and key custody

Use the build environment from BUILD.md. `build_content.py build --help` lists required inputs. Certify every package against clean vanilla game files and paired, reviewed font/configuration/strings. The tool reads game files, builds expected archives in temporary storage, computes hashes, signs the manifest and verifies the ZIP; it does not install anything.

Example from `source`, with paths/report identity chosen deliberately:

```powershell
python build_content.py build --game 'D:\VanillaGameCopy' --payload '.\release\payload' --output 'D:\Candidates\KKS_1.0.0_Content_r1.zip' --key "$env:LOCALAPPDATA\KKS\Signing\kks-release-2026-10.dpapi.json" --content-version 1.0.0 --revision 1 --sequence 1 --baseline-id steam-en-25258219 --build-label 'Steam English Slasher 25258219' --report-id 'local-acceptance-report' --expected-legacy '.\release\manifest.json'
```

For the current translation profile, supply `--translation-localization` and the current Localization English translation file alongside the other inputs. The old `--include-translation` option is retained only for historical v2 packages. Existing output ZIPs are never overwritten. Later releases receive a new sequence and the complete five- or six-payload profile; a different game baseline receives a new baseline ID. No partial or differential package is accepted. The tool marks packages as candidates; a separate acceptance record promotes the exact tested bytes after owner approval.

The initial private signing key is Windows-DPAPI encrypted for the current publishing account and stored outside the repository. Never log, commit, bundle or copy private bytes into the master snapshot. Before public rollout, the publisher should create a passphrase-encrypted recovery export and keep it securely offline:

```powershell
python build_content.py export-recovery-key --key "$env:LOCALAPPDATA\KKS\Signing\kks-release-2026-10.dpapi.json" --output 'E:\PrivateOfflineBackup\kks-release-2026-10.pem'
```

The command prompts privately for a matching passphrase of at least 16 characters. Do not enter it in chat. Recovery export and independent decryption/public-key/signing verification of the downloaded backup completed on October 1, 2026. Private locations and backup material are intentionally excluded from this repository. Losing the account/machine without that export can require an app with a new trusted key. Automatic key rotation and recovery-key import are not implemented; rotation may need an app update. Signing is a publisher operation, never an end-user step.

## Acceptance and boundaries

The 182 tests include all 59 original tests, strict signature/ZIP/schema cases, source-process termination, changed/foreign game files, low space, backup permission failures, locks/links, cache damage, preserved file presence, A→B→C and A→E updates, legacy migration, each file boundary, metadata commit boundaries, interrupted recovery and new-baseline reconciliation. Synthetic future baselines prove the protocol, not compatibility with an unreleased game build.

Local acceptance additionally records real-file tests of the built EXE: exact frozen 1.0 parity, repair/restore, forced process-tree termination/recovery, legacy migration and changed-file refusals. The maintainer accepted the unchanged 1.0 content in-game and recovery-key backup verification is complete. Nexus submission/review remains separate; see review/installer-1.5.0 for current evidence and review/installer-1.1.0 for historical evidence. Existing 1.0 gameplay approval applies to identical payload bytes, not every new workflow. Nexus may still review data packages, and the app can still need future security/compatibility updates.

Content 1.1.0 has owner acceptance for artwork, the standard perk deck and final Known checkmark/sorting. Its six final real-file installer checks and unchanged accepted bytes are recorded in review/content-1.1.0.


## Modular profiles (1.5.0)

Schema 3 adds complete, signed category metadata for optional equipment naming and
perk descriptions. Both options default to KKS. Alternate outputs are generated
from certified native members and must match signed hashes before game changes.
All four combinations use one canonical package. Manager schema 6 saves both
choices; Repair preserves them and Restore retains original file presence.
Use Installer 1.5.0 after installing schema-3 content, including after Restore.
See OPTIONAL_FEATURES.md for exact categories and schema-1/2 compatibility.
