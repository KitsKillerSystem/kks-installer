# KKS — Kit's Killer System

KKS adds custom glyphs, clearer item information, useful sorting and redesigned perk-card descriptions to Fallout 76.

## Installer 1.6.0 · English and Russian content 1.2.0

- [Installer 1.6.0 release and downloads](https://github.com/KitsKillerSystem/kks-installer/releases/tag/v1.6.0) — extract the installer ZIP and run `KKSInstaller.exe`.
- [English/Russian content on Nexus Mods](https://www.nexusmods.com/fallout76/mods/4301) — keep the signed content ZIP unopened. Content and installer are separate downloads and versions.

**Validated content: Fallout 76 Steam build 25636769. Use the final Installer 1.6.0.** Close the game, select its folder, choose/drop your language's content ZIP, choose options, and Install. Package selection verifies only; it does not install. Do not use Manual or source archives as installer inputs. Installer UI language does not translate content; Restore Baseline before changing content languages.

| Equipment naming | Perk descriptions | Result |
|---|---|---|
| KKS | KKS | Full KKS; defaults |
| Native | KKS | Native equipment with KKS cards |
| KKS | Native | KKS equipment with native perk descriptions |
| Native | Native | Both native treatments; other KKS features remain |

Both selectors require a supporting verified package. They change presentation, not perk gameplay. Reinstall the same ZIP with another choice to switch. Repair preserves choices. Restore Baseline restores the verified pre-KKS state, including supported prior modifications; keep `.kks-manager` and older KKS backups. Use 1.6.0 or newer after migration. Overlapping changes require confirmation; incompatible archives, changed game identities and unknown later modifications remain blocked. Play Fallout 76 explicitly opens Steam when the installation is ready.

## Release evidence and antivirus disclosure

The exact installer has a recorded **8/71 VirusTotal result** dated October 11, 2026, plus four unsupported engines. The owner authorized release with the unresolved warnings. The certificate finding remains **LIKELY BENIGN / PARTIALLY EXPLAINED**. The detections have not been conclusively established as false positives; vendor remediation continues as non-blocking maintenance.

[Detailed security review](https://github.com/KitsKillerSystem/kks-installer/blob/v1.6.0/review/installer-1.6.0/SECURITY_REVIEW.md) · [Exact VirusTotal report](https://www.virustotal.com/gui/file/46598f77674656442befca5e128da183682e720425c6ec40ff386a4bbfe4a589/detection) · [Release notes](RELEASE_NOTES.md)

EXE SHA-256: `46598f77674656442befca5e128da183682e720425c6ec40ff386a4bbfe4a589`

The release preserves the scanned executable, with 210 passing regressions, 15 final compiled checks and 48 broader checks on the branding-equivalent predecessor. [Build and acceptance evidence](review/installer-1.6.0/README.md), [content validation](review/content-1.2.0/README.md), [build instructions](BUILD.md), [optional feature contract](OPTIONAL_FEATURES.md), and [restoration contract](INDEPENDENT_INSTALLER.md).

KKS is an offline resource patcher; it does not inject code into the game or automatically download updates. Content is publisher-signed; the Windows EXE is not Authenticode-signed. Python and xTranslator are not needed by installer users. Source is in `source/kks_installer/` and `source/launcher.py`; exact build tag: `installer-v1.6.0`. GitHub distributes the installer; new content downloads belong on Nexus. Earlier release assets and evidence remain historical. Game archives, backups, signing private keys and private authoring history do not belong in this public repository.
