# KKS — Kit's Killer System

Installer 1.10.0 is the current release for the KKS 1.3.0 update.

KKS adds custom glyphs, item information, sorting and perk-card descriptions to Fallout 76.
[Installer 1.10.0 release](https://github.com/KitsKillerSystem/kks-installer/releases/tag/v1.10.0) · [Content on Nexus Mods](https://www.nexusmods.com/fallout76/mods/4301).

Installer 1.10.0 supports thirteen content languages and independent Equipment, Perk, Food and Junk choices. Changes are staged until **Apply Changes**; reverting to installed settings does nothing. Play does not apply drafts.

Close the game, extract the installer ZIP, run KKSInstaller.exe, select the game folder and choose/drop the unopened signed content ZIP. Select options and Install. Match the Steam content language. Restore the verified current baseline before switching languages. Preserve .kks-manager and backups. After a supported game update, choose the new content ZIP; never force an older baseline over updated game files.

The installer stays offline. UI translations cover English, German, French, Russian and Brazilian Portuguese; content supports all thirteen vanilla languages. Python and xTranslator are not required. Use corrected Polish R003 for Steam build 26054086.

[Release notes](RELEASE_NOTES.md) · [Security review](review/installer-1.10.0/SECURITY_REVIEW.md) · [Build evidence](review/installer-1.10.0/README.md).

Full suite: 250 tests on 8c9e21a. Final presentation: 26 focused tests with unchanged backend/test proof. Exact EXE checks include historical English migration and corrected Polish installation/update/Repair/Restore. The owner accepted the exact-file 7/70 scan with unresolved warnings and coverage limitations; read the linked security review.
EXE SHA-256: 5b49321ebb891dc33b80a4af511f5a3b1bfb55f08220a65ee215db189961480f
Build source: e3760cd115d4852f2ee13384b10788a91afa25c7

No game archives, new content payloads, backups or signing keys belong in this publication.
