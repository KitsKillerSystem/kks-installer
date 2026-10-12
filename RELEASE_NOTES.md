# KKS Installer 1.6.0

Installer 1.6.0 adds independent Russian equipment/perk options, preserves a verified pre-KKS baseline when using supported modified Interface archives, and includes a guarded **Play Fallout 76** button. English and Russian KKS 1.1.2 content is distributed separately through [Nexus Mods](https://www.nexusmods.com/fallout76/mods/4301). Installer and content versions remain independent.

## Install or update

1. Download `KKS_Installer_1.6.0.zip` below, extract it, and run `KKSInstaller.exe`.
2. Download the English or Russian **1.1.2 content package** from Nexus and keep that ZIP unopened. Manual/source archives are not installer inputs.
3. Close Fallout 76, select the game folder, choose/drop the content ZIP, choose equipment/perk options, and Install.

Both languages support KKS/native equipment naming and KKS/native perk descriptions independently. Turning both options off retains other KKS features. Repair preserves your selections. **Restore Baseline** restores the verified pre-KKS state, including supported prior modifications. Keep the game's KKS backups. Restore before switching content languages; installer UI language alone does not change content language. Earlier 1.6.0 previews must be replaced with this final build for current Russian modular packages.

Supported release content: **Fallout 76 Steam build 25636769**. Modified archives still require structural compatibility; overlapping resource replacements require explicit confirmation that expires if inputs change. Unsupported game identities and unknown later edits remain blocked. Use 1.6.0 or newer to manage a migrated baseline. Play starts the game only when clicked after readiness checks; installation never launches it automatically.

## Antivirus disclosure

The recorded October 11, 2026 scan of the exact EXE reports **8/71 detections**, plus four unsupported engines. The owner authorized release with these unresolved warnings. The certificate finding remains **LIKELY BENIGN / PARTIALLY EXPLAINED**; neither that assessment nor successful functional testing proves the eight detections false positives. Legitimate false-positive/vendor remediation continues separately as non-blocking maintenance. The public ZIP updates release documentation only; its executable has not been rebuilt or altered.

EXE SHA-256: `46598f77674656442befca5e128da183682e720425c6ec40ff386a4bbfe4a589`

[Exact VirusTotal report](https://www.virustotal.com/gui/file/46598f77674656442befca5e128da183682e720425c6ec40ff386a4bbfe4a589/detection) · [Detailed findings, vendor labels and limitations](https://github.com/KitsKillerSystem/kks-installer/blob/v1.6.0/review/installer-1.6.0/SECURITY_REVIEW.md)

## Validation and source

**210 automated regressions** passed on the exact build source. The final EXE passed **15 compiled checks**, including all eight English/Russian option combinations, signatures, Repair and exact cache-free Restore. **48 broader checks** passed on the preceding branding build; the final code change was verified as branding-only. Final package/hash checks and three read-only EXE checks passed again for publication. [Build/test evidence](https://github.com/KitsKillerSystem/kks-installer/blob/v1.6.0/review/installer-1.6.0/README.md).

The executable is built from source tag [`installer-v1.6.0`](https://github.com/KitsKillerSystem/kks-installer/tree/installer-v1.6.0); the publication tag `v1.6.0` adds documentation/evidence. It is not Authenticode-signed. `SHA256SUMS.txt` covers the ZIP and extracted EXE. GitHub's automatic source archives are for developers, not installable content. Prior releases remain unchanged.

English/Russian 1.1.2 includes accepted Food V2 sorting, component/junk glyphs, paired regular/Ultracite ammo sorting, revised consumable descriptions and queued glyph/menu fixes. Russian includes the approved full localized perk deck and 39 primary legendary wordmarks. [Content validation and known limits](https://github.com/KitsKillerSystem/kks-installer/blob/v1.6.0/review/content-1.1.2/README.md).
