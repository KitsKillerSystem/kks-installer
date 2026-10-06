# Optional features preview — Installer 1.5.0

Private English M001 prototype; gameplay acceptance and publication are separate.
The owner authorized independent perk-card on/off control after accepting E001
equipment naming in game. Both KKS options are recommended and on by default.
Each selector remains disabled until a valid package advertises its capability.

Equipment naming keeps the E001 behavior: Vanilla Equipment Naming restores
complete WEAP:FULL, ARMO:FULL and INNR:WNAM categories in STRINGS. Perk Cards Off
restores the complete PERK:DESC category in DLSTRINGS. It changes descriptions;
it does not disable the game's perks, edit gameplay records, remove shared font
assets, or change perk names and PERK:EPF2 action labels. Legendary descriptions
were already native. All other KKS text, artwork and assets retain their selected
equipment treatment. All four combinations use one canonical content ZIP.

The publisher invokes `build_content.py --equipment-naming --perk-cards
--translation-localization`. Schema 3 retains the schema-2 equipment metadata
and adds `perk_cards`: fixed `vanilla-perk-cards-v1` algorithm, ESM-derived complete
PERK:DESC IDs, and the signed alternate DLSTRINGS hash/size. It requires Installer
1.5.0 and the English Localization profile. No alternate payload or hand-maintained
ID list is shipped. Schema-1 and schema-2 packages retain their previous support.

Before a game transaction, selected alternate tables are generated from the
authenticated canonical cache and the hash-pinned native Localization members.
Raw placeholders, newline sequences and control characters survive unchanged.
Each result must match its signed hash and size before installation begins.
The two tables have separate signed outputs, covering every combination without
duplicating fonts or content packages. The canonical cache remains unchanged.

Manager schema 6 records both `naming` and `perks` on schema-3 installations.
Repair retains both installed choices and rebuilds derived caches. Check is
read-only; it reports the number of effective files that would change. Receipt,
ownership and recovery checks use the selected output hashes. Restore works
without any payload or derived cache and preserves original loose-file absence.
All existing per-language sequence history is retained. Use Installer 1.5.0 after
M001, including after Restore; older installers cannot read schema-6 history.
Return to both KKS options using M001 rather than downgrading to E001's sequence.

CLI: `--naming full-kks|vanilla-equipment` and `--perk-cards on|off` for Check or
Install. Default: `full-kks` and `on`. Repair/Restore use the saved installation.

M001 uses accepted E001 content plus finalized underarmor wording without changing
any canonical payload byte. Its ESM-derived 1,488 PERK:DESC IDs restore 451 custom
descriptions covering 240 standard cards; the other 19 changed DLSTRINGS values
remain intact. All 2,806 panel codepoints become dormant. Equipment's alternate
output is identical to E001. Independent frozen compiler, XML and deck-mapping
audits are retained with the private `Features/Optional_Features_M001` checkpoint.

This gives future packages a native perk fallback while artwork is reviewed.
New game builds still need their own certified package and current native string
baseline. The toggle does not bypass existing compatibility or ownership checks.
