# KKS 1.1.0 + Installer 1.2.1

KKS 1.1.0 brings the artwork and information pass across inventory, crafting,
CAMP interactions and the full standard perk deck.

- Refined glyph silhouettes and visual weight, with smaller, balanced legendary wordmarks.
- Cleaner cooked-food names with mutation identity and useful effect suffixes; primary effect-family sorting is preserved.
- More consistent CAMP object/action labels and deployment of existing object artwork.
- Redesigned descriptions for all 240 standard perk cards, including ranks and ghoul variants, with clearer mechanics and flavor text. Legendary perk cards remain outside this update.
- Plan rarity grouping, unknown plans above Known plans, and a checkmark alongside the retained Plan icon.
- Targeted Sustain, standalone Clean-food and missed UNIQUE equipment fixes.

Installer 1.2.1 fixes package drag-and-drop, refreshes the interface and adds
verified English translation-file support with backups, repair and restoration.

## Install or update

**Steam English build 25636769. Installer 1.2.1 is required.**

1. Download both named ZIP assets. Extract `KKS_Installer_1.2.1.zip`.
2. Close Fallout 76 and run `KKSInstaller.exe`.
3. Select the game folder, then drop in or choose the intact `KKS_1.1.0_Steam_EN_25636769.zip`.
4. After verification, click **Install content** or **Install update**.

Existing supported KKS installations can update directly without restoring first.
Keep the game's KKS backup folders and use Installer 1.2.1 for Repair or Restore
vanilla afterward. This is a complete package; no intermediate versions are needed.
If Bethesda updates the game, wait for a package certified for that new build.

## Validation

The package is the exact content accepted in the maintainer's final playtest.
Installer validation includes 138 automated tests, two byte-identical clean builds,
actual install/upgrade/repair/restore checks and repeated packaged drag-and-drop.
Content signatures are separate from Windows signing; the EXE is not Authenticode-signed.

[Content evidence](https://github.com/KitsKillerSystem/kks-installer/tree/v1.1.0/review/content-1.1.0)
and [installer build evidence](https://github.com/KitsKillerSystem/kks-installer/tree/v1.1.0/review/installer-1.2.1).
`SHA256SUMS.txt` covers both download ZIPs. GitHub's automatic Source code archives
are for developers; players need the two named assets. Application and content
versions are independent. Previous releases remain available unchanged.
