# KKS — Kit's Killer System

KKS adds custom glyphs, clearer item information, useful sorting and redesigned
perk-card descriptions to Fallout 76.

## Download KKS 1.1.1 and Installer 1.5.0

[Release page and downloads](https://github.com/KitsKillerSystem/kks-installer/releases/tag/v1.1.1)

- [KKS Installer 1.5.0](https://github.com/KitsKillerSystem/kks-installer/releases/download/v1.1.1/KKS_Installer_1.5.0.zip) — extract this ZIP and run `KKSInstaller.exe`.
- [KKS Content 1.1.1](https://github.com/KitsKillerSystem/kks-installer/releases/download/v1.1.1/KKS_1.1.1_Steam_EN_25636769.zip) — keep this signed content ZIP intact.

**Supported content: Fallout 76, Steam, English, build 25636769. Installer 1.5.0 is required.**
Installer and content versions are independent.

1. Download both named ZIPs, including the updated installer.
2. Close Fallout 76 and open `KKSInstaller.exe`.
3. Select the game folder, then drop in the intact content ZIP or use Choose package.
4. After verification, choose your equipment/perk options and click Install content / Install update.

Existing supported installations update directly without a manual restore or
intermediate release. Selecting a package only verifies it. Keep the game's
`.kks-manager` and any `.kks-installer-1.0.0` records/backups. Use Installer 1.5.0 for
Repair and Restore after this update, including after a restore/reinstall cycle.

## Your equipment and perk choices

| Equipment naming | Perk cards | Result |
|---|---|---|
| KKS | KKS | Full KKS experience; recommended defaults |
| Vanilla | KKS | Native equipment names with KKS perk cards |
| KKS | Vanilla | KKS equipment names with native perk descriptions |
| Vanilla | Vanilla | Both native treatments; other KKS features remain installed |

Both selectors unlock only when the verified package supports them. Perk Cards Off
restores native descriptions; it does not disable perks or change gameplay effects.
Close the game and install the same ZIP with another selection to switch back.
Repair preserves your choices. Restore vanilla returns the managed files to their
original state. This release also finalizes English underarmor naming while keeping
the accepted artwork, sorting, Known checkmarks and 240-card standard perk deck.

After a Bethesda update, complete Steam's Verify integrity of game files before
selecting content certified for that new build. Optional features do not bypass
compatibility checks. The installer never downloads updates automatically.
The content ZIP here is English; installer UI language selection does not translate it.

## Validation and source

The maintainer passed six in-game checks: Restore Vanilla, Full KKS, both hybrid
configurations, profile-aware Repair, and return to Full KKS, with no regressions
observed. The accepted build also passed **182 automated tests and 28 compiled-EXE
checks**, including all four combinations, cache-free restoration and interruption recovery.

- [Release notes](RELEASE_NOTES.md)
- [Content 1.1.1 validation and signed manifest](review/content-1.1.1/README.md)
- [Installer 1.5.0 build and test evidence](review/installer-1.5.0/README.md)
- [Optional feature contract](OPTIONAL_FEATURES.md), [build instructions](BUILD.md),
  [package/restoration contract](INDEPENDENT_INSTALLER.md), and [security scope](SECURITY_REVIEW.md)

The app is an offline asset patcher; it requires Fallout 76 to be closed and never
injects code into the game. Content is publisher-signed; the Windows EXE is not
Authenticode-signed. The exact accepted artifacts retain their historical preview
labels; release acceptance and build provenance are recorded in the evidence above.

Players need the two named downloads, not GitHub's automatic Source code archives.
Python and xTranslator are not required. Previous releases and their evidence remain
available unchanged. The application source is in `source/kks_installer/` and
`source/launcher.py`; publisher tooling and frozen legacy inputs are not embedded.
Game archives, signing private keys, game backups and private authoring history do
not belong in this repository. Publication here does not claim Nexus approval.

[KKS on Nexus Mods](https://www.nexusmods.com/fallout76/mods/4301)
