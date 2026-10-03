# KKS — Kit's Killer System

KKS adds custom glyphs, clearer item information, useful sorting and redesigned perk-card descriptions to Fallout 76.

## Download KKS 1.1.0 and Installer 1.2.1

[Release page and downloads](https://github.com/KitsKillerSystem/kks-installer/releases/tag/v1.1.0)

- [KKS Installer 1.2.1](https://github.com/KitsKillerSystem/kks-installer/releases/download/v1.1.0/KKS_Installer_1.2.1.zip) — extract this ZIP and run `KKSInstaller.exe`.
- [KKS Content 1.1.0](https://github.com/KitsKillerSystem/kks-installer/releases/download/v1.1.0/KKS_1.1.0_Steam_EN_25636769.zip) — keep this signed content ZIP intact.

**Supported game:** Fallout 76, Steam, English, build **25636769**. **Installer 1.2.1 is required for this content.** Installer and content versions are independent.

1. Download both named ZIPs, including the updated installer if you have an older version.
2. Close Fallout 76 and open `KKSInstaller.exe`.
3. Select the game folder, then drag the intact content ZIP onto the installer or use **Choose package**.
4. After verification, click **Install content** or **Install update**.

Existing KKS installations on the supported game build can update directly; no manual restore or intermediate content releases are needed. Selecting a package only verifies it. Keep the game's `.kks-manager` and any `.kks-installer-1.0.0` records/backups, and use Installer 1.2.1 for Repair or Restore vanilla after this update.

If Bethesda updated the game while KKS was installed, complete Steam's **Verify integrity of game files** before selecting a package certified for that new build. Unsupported game fingerprints or conflicting files stop installation. The installer never downloads updates automatically.

GitHub's automatic **Source code** archives are for developers. Players need the two named ZIPs above; Python and xTranslator are not required. Previous releases remain available under [Releases](https://github.com/KitsKillerSystem/kks-installer/releases).

## What's new

- Refined glyph artwork and more consistent visual weight, including quieter legendary wordmarks and UNIQUE equipment labels.
- Cleaner cooked-food names: cooking pot, mutation identity, name and useful effect suffixes, with effect-family sorting retained.
- More consistent CAMP object/action labels, using existing artwork for recognizable objects and buff information.
- Redesigned descriptions for all **240 standard perk cards**, including rank and ghoul variants, with clearer mechanics and flavor text. Legendary perk cards remain outside this update.
- Plan rarity grouping, unknown plans before Known plans, and a Known checkmark that retains the Plan icon.
- Targeted Sustain, Clean-food and missed UNIQUE assignment corrections.

Installer 1.2.1 fixes package drag-and-drop, refreshes the interface and securely adds English translation-file support. It preserves verified backups, repair, restoration and interrupted-operation recovery. The content and executable are the exact bytes accepted in the maintainer's playtest.

## Source and verification

- [Release notes](RELEASE_NOTES.md)
- [Content 1.1.0 validation and signed manifest](review/content-1.1.0/README.md)
- [Installer 1.2.1 build and test evidence](review/installer-1.2.1/README.md)
- [Build instructions](BUILD.md), [package/restoration contract](INDEPENDENT_INSTALLER.md), and [security scope](SECURITY_REVIEW.md)

The application is an offline asset patcher. It requires Fallout 76 to be closed and never injects code into the game. Content packages are publisher-signed; the Windows executable is **not Authenticode-signed**. Publication here does not claim Nexus approval. Historical [Installer 1.1.0 review evidence](review/installer-1.1.0/README.md) and the original root-level 1.0.0 review files remain unchanged.

`source/kks_installer/` and `source/launcher.py` contain the application. `source/tests/` contains 138 automated tests. `source/release/` preserves the original 1.0.0 inputs for provenance; the current installer does not embed them. `source/build_content.py` is publisher tooling and is excluded from the runtime.

Game archives, private signing keys, local backups and private authoring history are not part of this repository. The exact source commit for the published executable is recorded in its build receipts; later release documentation does not require a new binary.

[KKS on Nexus Mods](https://www.nexusmods.com/fallout76/mods/4301)
