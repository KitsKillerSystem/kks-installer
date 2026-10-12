# KKS Installer 1.7.0

Adds independent equipment-naming and perk-card options for supporting French and German packages. English/Russian support, drag-and-drop, Repair and baseline restoration are retained. No new installer resource targets are introduced.

Download `KKS_Installer_1.7.0.zip`, extract it, and run `KKSInstaller.exe`. Keep the separate signed content ZIP unopened. Close Fallout 76, select its folder, choose/drop the matching package, choose options and install. Restore Baseline before switching content languages; keep KKS backup history. Manual/source ZIPs are not installer inputs. Certified content baseline: Steam build 25636769.

French/German content will be distributed separately through [Nexus Mods](https://www.nexusmods.com/fallout76/mods/4301). It has received less native-speaker feedback, so grammar and terminology may receive follow-up corrections. Installer UI language alone does not change game content language.

**Validation:** 212 regression tests and 24 exact-EXE checks passed, including B003 upgrades, all four profiles in both languages, Repair and exact cacheless Restore. The new content has not yet received the owner's planned in-game inspection.

**Antivirus disclosure:** October 12, 2026, **7/71 detections**, four additional unsupported engines. The owner authorized release with the seven unresolved warnings and disclosed coverage limits; no false-positive determination is claimed. All native runtime/data members are exact to 1.6.0; only two bundled application modules changed as intended. [Exact scan](https://www.virustotal.com/gui/file/85112d5d56ac7c83e31d6f0488a8af080baae85320dbdb3bdac57b44afdc9749/detection) · [Detailed review](https://github.com/KitsKillerSystem/kks-installer/blob/v1.7.0/review/installer-1.7.0/SECURITY_REVIEW.md).

EXE SHA-256: `85112d5d56ac7c83e31d6f0488a8af080baae85320dbdb3bdac57b44afdc9749`. The EXE is not Authenticode-signed. Content uses separate publisher signatures. Source build commit: `28e8f7edb277d767ddebb062682f66b7955b9341`. This release preserves the scanned EXE bytes; earlier releases remain unchanged. Source tag: `installer-v1.7.0`; the publication tag `v1.7.0` adds release documentation and evidence.
