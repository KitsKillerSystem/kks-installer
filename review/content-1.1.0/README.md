# KKS Content 1.1.0

Complete signed content for Fallout 76 Steam English build **25636769**.
Requires **Installer 1.2.1**. Content revision 8 / sequence 10 is the exact
package accepted by the maintainer in game on 3 October 2026.

[Download release](https://github.com/KitsKillerSystem/kks-installer/releases/tag/v1.1.0)

The update combines refined glyph artwork, CAMP object/action consistency,
cooked-food effect-family sorting, all 240 standard perk cards, Plan rarity
ordering and Known checkmarks, plus targeted Sustain, Clean-food and UNIQUE fixes.
Unknown plans sort before Known plans; the Plan icon and rarity suffixes remain.
Legendary perk cards are outside this update.

The ZIP contains the signed manifest and six fixed font/configuration/translation/
string payloads. Translation replaces only the two Known values in the current
Localization archive's English text. Fontconfig remains unchanged. The final
sort correction adds one leading space to the existing 3,033 Plan-family names.

Six final actual-executable checks cover signature validation, previous candidate
installation, update preflight, direct upgrade, cached repair and exact restore.
All archive outputs are unchanged from the accepted checkmark build. Prior
profile-expansion checks and the 138-test installer suite are recorded in
[the installer evidence](../installer-1.2.1/README.md).

[ACCEPTANCE.json](ACCEPTANCE.json) records owner acceptance and exact package hashes;
the accompanying manifest and signature are copied directly from the ZIP.
The signed builder's `qa.status: candidate` and historical report identifier
remain unchanged to preserve the exact tested package. This acceptance record
supersedes that build-time status; it is not a new signature or independent audit.

Existing KKS users on the supported game build can update directly. Download
Installer 1.2.1, close the game, select the intact content ZIP and Install update.
Keep game-side backups and use 1.2.1 for subsequent Repair or Restore vanilla.
Older installers cannot manage the new six-target profile.

No Bethesda archives, game executable, private receipts or signing keys are
distributed in these review files. Nexus publication and approval are separate.
