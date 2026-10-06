# KKS 1.1.1 + Installer 1.5.0 — Modular equipment and perk cards

Choose KKS equipment naming and KKS perk cards independently, using one complete
content package. Keep the full experience, use native equipment with KKS perks,
keep KKS equipment with native perks, or turn both treatments off while retaining
the rest of KKS. Both KKS options are enabled by default.

- **Vanilla Equipment Naming** restores native weapon/armor names and naming rules.
- **KKS Perk Cards Off (Vanilla)** restores Bethesda's native perk descriptions.
  It does not disable perks or change their gameplay effects.
- Selectors stay disabled until a verified package supports each option.
- Switch either feature with the same ZIP. Repair preserves the installed choices;
  Restore vanilla and interrupted-operation recovery remain supported.
- Includes finalized English underarmor names without redundant classification text.

This gives KKS a practical native fallback while feature artwork or wording is
revised. New Bethesda builds still need a package certified for their current files.

## Install or update

**Fallout 76 Steam English build 25636769. Installer 1.5.0 is required.**

1. Download [KKS_Installer_1.5.0.zip](https://github.com/KitsKillerSystem/kks-installer/releases/download/v1.1.1/KKS_Installer_1.5.0.zip) and extract it.
2. Download [KKS_1.1.1_Steam_EN_25636769.zip](https://github.com/KitsKillerSystem/kks-installer/releases/download/v1.1.1/KKS_1.1.1_Steam_EN_25636769.zip) and keep it intact.
3. Close Fallout 76, run `KKSInstaller.exe`, and select your game folder.
4. Choose or drop in the content ZIP, select your options, and click Install.

Existing supported installations can update directly without restoring first.
Keep the game's KKS backups. Use Installer 1.5.0 for subsequent Repair/Restore,
including after restoring and reinstalling; older installers cannot read the new
saved history. Re-enable features with this same package instead of downgrading.
The content package is English; changing the installer UI language does not translate it.

## Validation

The exact executable and signed content passed maintainer in-game acceptance:
Restore Vanilla, Full KKS, both equipment/perk hybrids, profile-aware Repair, and
return to Full KKS. No regressions observed. **182 automated tests and 28 compiled-EXE
checks passed**, including all four combinations and forced-interruption recovery.

[Installer build evidence](https://github.com/KitsKillerSystem/kks-installer/tree/v1.1.1/review/installer-1.5.0) and
[content acceptance](https://github.com/KitsKillerSystem/kks-installer/tree/v1.1.1/review/content-1.1.1) identify the exact tested bytes.
Historical preview/candidate labels remain in the accepted artifacts; the release
acceptance supersedes them. Content is publisher-signed; the EXE is not Authenticode-signed.

`SHA256SUMS.txt` covers both download ZIPs. GitHub's automatic Source code archives
are for developers; players need the two named ZIPs. Installer and content versions
are independent. Prior releases remain available unchanged.
