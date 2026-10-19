# Installer 1.9.0 candidate

Unpublished feature candidate. Content and installer versions remain independent.
No public security disposition or game acceptance is implied by this source.

The application accepts publisher-signed content for all thirteen Fallout 76
locales: `en`, `de`, `ru`, `fr`, `ptbr`, `es`, `esmx`, `it`, `ja`, `ko`, `pl`,
`zhhans`, and `zhhant`. Content language names and Steam-language guidance are
available for all thirteen. The installer interface retains its existing English,
German, Russian, French and Brazilian Portuguese translations.

Supported schema-4 packages expose four independent choices:

| Option | Choices | Default |
|---|---|---|
| Equipment | KKS / Vanilla Equipment Naming | KKS |
| Perk cards | KKS / Vanilla | KKS |
| Food | Food V2 / Family Food | Food V2 |
| Junk components | KKS Default (Glyph Components) / Text Based / None | KKS Default |

There are 24 configurations per language. Junk None removes component labels;
the authored content retains a weight annotation only for Junk-Heavy. The
installer performs no numerical conversion, unit substitution or translation.
Those literal localized values come from the signed content.

One language's package contains six canonical resources and a seventh small
`payload/string-modes.json` file. Its fixed schema describes sorted raw-byte
replacements for Family Food, text components and no components. It cannot
introduce filesystem targets, executable hooks, additional options or arbitrary
archives. Food and junk IDs must be disjoint, must exist in the canonical table,
and cannot overlap complete native-equipment categories. Every equipment × food
× junk combination has its own authenticated STRINGS hash and length; native
perk descriptions retain their independently signed DLSTRINGS result.

All selected resources are generated and checked in the cache before a game
transaction starts. Repair rebuilds the selected outputs from the canonical
package and certified native tables. Restore Baseline does not need content or
derived caches. Changing content languages still requires Restore Baseline.
Japanese, Korean and the two Chinese locales use their fixed native font archive
and member names. Russian retains its Russian font archive; Latin locales retain
the English font archive.

Existing package schemas 1–3 retain their capability gates and existing profile
hashes. New choices remain disabled for packages that do not advertise schema 4.
Saved state schema 8 preserves all previous language sequence history and adds
food/junk selections. Use Installer 1.9.0 or later after installing schema-4
content, including after Restore; older installers cannot read this history.

CLI additions: `--food food-v2|family-food` and `--junk glyph|text|none` for Check
or Install. Repair and Restore use the recorded installation choices. Existing
`--naming` and `--perk-cards` options retain their meanings.

Publisher API: `build_content.build(..., string_mode_tables={(food, junk): Path,
...}, equipment_naming=True, perk_cards=True, translation_localization=True)`.
Supply all six STRINGS presentations with identical directory IDs and order;
the default must be the exact canonical payload. The publisher validates their
independent composition and signs all twelve output hashes. The CLI accepts
`--string-modes modes.json`, a six-row JSON array of `{food, junk, path}` objects;
paths are resolved relative to the JSON file. Each content update can change the
signed data without changing this profile implementation.

Native archive certificates contain hashes and metadata only. Additional CJK
certificates are checked against authenticated baseline acquisition pins and
must match the final signed packages before accepting the final application
build. Existing compatibility, overlap confirmation, sequence, transaction and
restoration checks remain in force. A future Bethesda update requires newly
certified content; this candidate does not claim compatibility with an unseen
update.

Validation includes the 312-profile synthetic matrix, profile-preserving Repair,
cacheless exact Restore, old-package upgrades, language-switch rejection,
interruption at transaction boundaries, signature/patch/matrix rejection and
the publisher round trip. Exact final build/test receipts belong with the
candidate artifact. Public release separately requires the established exact-file
installer security scan and owner disposition; no scan or publication occurs
as part of authoring these features.
