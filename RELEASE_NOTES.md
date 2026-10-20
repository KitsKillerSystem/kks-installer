# KKS Installer 1.10.0

Released with the owner-accepted exact-file security disposition documented below.

Installer 1.10.0 supports all thirteen vanilla content languages and adds independent Food and Junk Components choices. Selectors now stage changes until you press **Apply Changes** beside Play. Returning to installed settings does no work; Play never applies a pending draft.

Food offers **Kit's Style** and **Abby's Style**. Junk Components offers **KKS Default (Glyph Components)**, **Text Based**, and **None**. None retains weight annotations only for Junk-Heavy items. Equipment naming and perk-card choices remain independent. These options require a supporting signed package.

Post-update migration now accepts the historical Family Food caption in authenticated installation receipts while retaining baseline/hash checks. The normal supported update path is: open installer, select/drop the new signed ZIP, Install update, Play. An initial old-baseline warning may remain until the new package is selected. Never restore old archives over an updated game or delete .kks-manager to bypass checks.

The approved Halloween presentation fills the left panel. Content languages are English, German, French, Russian, Brazilian Portuguese, Spanish, Latin American Spanish, Italian, Japanese, Korean, Polish, Simplified Chinese and Traditional Chinese. Installer UI translations remain English, German, French, Russian and Brazilian Portuguese; UI language does not translate game content.

Extract KKS_Installer_1.10.0.zip and run KKSInstaller.exe. Get the separate signed language ZIP from [Nexus Mods](https://www.nexusmods.com/fallout76/mods/4301); keep it unopened and choose/drop it into the installer. Match the Steam game language. Restore the verified current baseline before switching content languages. Python/xTranslator are not required.

Current content targets Steam build 26054086. Use corrected Polish R003 rather than superseded R002; its font routing and exact-EXE update/Repair/Restore checks pass. Other earlier releases remain unchanged.

Validation: 250 full-suite tests on 8c9e21a; 26 focused tests for the final presentation with unchanged backend/test proof. Exact final EXE checks cover historical English migration/Repair/cacheless Restore, authentication across all thirteen languages, and the corrected Polish R003 lifecycle. [Review evidence](https://github.com/KitsKillerSystem/kks-installer/blob/v1.10.0/review/installer-1.10.0/README.md).

Security: the October 20, 2026 scan reports **7/70** detections, one timeout and four unsupported engines. The owner accepted release with these unresolved warnings and partial behavioral coverage; Jujubox encountered a missing-DLL startup error. No vendor-confirmed false-positive or safety claim is made. [Detailed review](https://github.com/KitsKillerSystem/kks-installer/blob/v1.10.0/review/installer-1.10.0/SECURITY_REVIEW.md) · [exact-file scan](https://www.virustotal.com/gui/file/5b49321ebb891dc33b80a4af511f5a3b1bfb55f08220a65ee215db189961480f/detection).

EXE SHA-256: 5b49321ebb891dc33b80a4af511f5a3b1bfb55f08220a65ee215db189961480f
Build source: e3760cd115d4852f2ee13384b10788a91afa25c7
The EXE is not Authenticode-signed. Content signatures are separate.

GitHub assets are the installer ZIP and checksums only. Content/manual downloads stay on Nexus.
