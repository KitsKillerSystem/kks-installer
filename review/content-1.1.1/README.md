# KKS Content 1.1.1

Complete signed content for Fallout 76 **Steam English build 25636769**.
Requires **Installer 1.5.0**. Revision 7 / English sequence 17 is the exact M001
package accepted in game by the maintainer on 6 October 2026.

[Release downloads](https://github.com/KitsKillerSystem/kks-installer/releases/tag/v1.1.1)

One canonical package supports independent KKS equipment naming and perk-card
descriptions. Both KKS options default on. Native equipment restores all
WEAP:FULL, ARMO:FULL and INNR:WNAM values; native perks restore complete PERK:DESC.
All other KKS content stays installed. This content also includes finalized
English underarmor wording, with redundant UA/Underarmor classification removed
from 70 base-name values. It retains the accepted artwork, sorting and perk deck.

[CONTENT_VALIDATION.json](CONTENT_VALIDATION.json) records independent ESM, XML,
deck-map and frozen-compiler parity. Perk fallback covers 1,488 description IDs,
replaces 451 custom descriptions for 240 standard cards, and preserves the other
19 modified descriptions. The 2,806 panel codepoints remain dormant in shared fonts.
Equipment fallback is unchanged from accepted E001. No alternate payload is shipped.

[ACCEPTANCE.json](ACCEPTANCE.json) records the maintainer's six in-game checks:
Restore Vanilla, Full KKS, both equipment/perk hybrids, profile-aware Repair and
return to Full KKS. No regressions were observed. [Installer evidence](../installer-1.5.0/README.md)
separately records 182 automated tests and 28 real-file executable checks.

The public filename changes; the ZIP, signature, payloads, revision, sequence,
historical M001 build label and signed `qa.status: candidate` are unchanged.
The acceptance record supersedes build-time pending labels. The installer retains
its historical Optional Features Preview display label for the same reason.
No rebuild or re-signing is implied by publication.

Update directly on the supported baseline. Keep game-side backups and use Installer
1.5.0 for Repair/Restore after this update, including after restoring and reinstalling.
Switch features using this same package; older content sequences cannot downgrade.
Future Bethesda builds require separately certified packages. This release publishes
English content; the installer interface language does not translate the package.
