# KKS — Kit's Killer System

KKS adds custom glyphs, clearer item information, useful sorting and redesigned perk-card descriptions to Fallout 76.

## Installer 1.7.0

Installer 1.7.0 adds French/German support for the same independent equipment-name and perk-card options available in English and Russian. [Download Installer 1.7.0](https://github.com/KitsKillerSystem/kks-installer/releases/tag/v1.7.0). Earlier releases remain unchanged.

Content downloads are separate on [Nexus Mods](https://www.nexusmods.com/fallout76/mods/4301). French/German packages with these options require 1.7.0. Their native-language wording has received less player feedback and may receive corrections. The owner plans an in-game visual inspection before uploading those content editions.

**Certified content: Fallout 76 Steam build 25636769.** Close the game, run the installer, select its folder, choose/drop the unopened signed content ZIP, choose options and Install. Package selection verifies only; it does not install. Manual/source archives are not installer inputs. Restore Baseline before switching content languages. Installer UI language does not translate content.

| Equipment naming | Perk descriptions | Result |
|---|---|---|
| KKS | KKS | Full KKS; defaults |
| Native | KKS | Native equipment with KKS cards |
| KKS | Native | KKS equipment with native perk descriptions |
| Native | Native | Both native treatments; other KKS features remain |

Both selectors require a supporting verified package. Choices affect presentation, not perk gameplay. Reinstall the same ZIP to switch options. Repair preserves choices. Restore Baseline restores the verified pre-KKS state, including supported prior modifications. Keep `.kks-manager` and older KKS backups. Overlapping changes require confirmation; incompatible archives, changed game identities and unknown later edits remain blocked. Play explicitly opens Steam after readiness checks.

## Release evidence and antivirus disclosure

The exact new EXE has a recorded **7/71 VirusTotal result** dated October 12, 2026, plus four unsupported engines. The remaining warnings have not been confirmed as false positives. The earlier certificate finding remains **LIKELY BENIGN / PARTIALLY EXPLAINED**; that closed inquiry is not reopened. The owner authorized release with the remaining detections and disclosed coverage limits; that decision does not resolve the warnings.

[Detailed 1.7.0 review](review/installer-1.7.0/SECURITY_REVIEW.md) · [Exact scan](https://www.virustotal.com/gui/file/85112d5d56ac7c83e31d6f0488a8af080baae85320dbdb3bdac57b44afdc9749/detection) · [Release notes](RELEASE_NOTES.md)

EXE SHA-256: `85112d5d56ac7c83e31d6f0488a8af080baae85320dbdb3bdac57b44afdc9749`. 212 regressions and 24 exact-EXE release checks passed. Of 1,009 embedded outer members, 1,008 match released 1.6.0 exactly; only the Python module archive differs. Of 173 modules, only version/capability policy and package validation changed. [Build and validation evidence](review/installer-1.7.0/README.md).

KKS is an offline resource patcher; it does not inject code into the game or automatically download updates. Content is publisher-signed; the EXE is not Authenticode-signed. Python and xTranslator are not required by installer users. Build source commit: `28e8f7edb277d767ddebb062682f66b7955b9341`. GitHub distributes the installer; new content belongs on Nexus. Game archives, backups, signing keys and private authoring history do not belong in this repository.
