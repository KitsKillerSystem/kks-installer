# KKS — Kit's Killer System

KKS adds custom glyphs, clearer item information, useful sorting and redesigned perk-card descriptions to Fallout 76.

## Installer 1.8.0 — prepared update

Adds Brazilian Portuguese content support and Português (Brasil) UI. English, Russian, German and French remain supported. Publication disposition is pending; [Installer 1.7.0](https://github.com/KitsKillerSystem/kks-installer/releases/tag/v1.7.0) remains the current public release.

**Content downloads belong on [Nexus Mods](https://www.nexusmods.com/fallout76/mods/4301).** GitHub distributes the installer and its public source/review evidence. The installer does not download content. Portuguese content 1.2.0 requires Installer 1.8.0 or later; the first Portuguese edition has not received native-speaker review or in-game testing.

Close Fallout 76, extract the installer ZIP and run `KKSInstaller.exe`. Select the game folder, choose/drop the unopened signed content ZIP, choose options and Install. Selection verifies the package; it does not install. Manual/source archives are not installer inputs. Set the game's Steam language to match the content. Restore Baseline before switching content languages; the installer UI language does not translate content.

| Equipment naming | Perk descriptions | Result |
|---|---|---|
| KKS | KKS | Full KKS; defaults |
| Native | KKS | Native equipment with KKS cards |
| KKS | Native | KKS equipment with native perk descriptions |
| Native | Native | Both native treatments; other KKS features remain |

Options require a supporting verified package. Reinstall to change them; Repair preserves them. Restore Baseline returns the verified pre-KKS state, including supported prior modifications. Keep `.kks-manager` and KKS backups. Overlapping changes require confirmation; incompatible archives and unknown later edits remain blocked. Current content baseline: Steam build 25636769. Python and xTranslator are not required by installer users.

## Release evidence

The exact 1.8.0 EXE records **8/71 detections** on October 13, 2026, plus four unsupported engines. Remaining warnings are unresolved; no false-positive determination or security certification. [Detailed review](review/installer-1.8.0/SECURITY_REVIEW.md) · [Exact scan](https://www.virustotal.com/gui/file/b5950ae64451436dc65c3a6934a01ba493b272280896c863d25c3ac5f2599e98/detection) · [Release notes](RELEASE_NOTES.md).

217 regressions and 16 exact-EXE checks pass. [Build and comparison evidence](review/installer-1.8.0/README.md). Build source `fca6a862ae138ac8953fa30fb1f69adf77718a33`; EXE SHA-256 `b5950ae64451436dc65c3a6934a01ba493b272280896c863d25c3ac5f2599e98`. The EXE is not Authenticode-signed; content has separate publisher signatures. No game archives, backups, signing keys or private authoring material belong in this repository.
