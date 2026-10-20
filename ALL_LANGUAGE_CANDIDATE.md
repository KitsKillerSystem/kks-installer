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
| Food | Kit's Style / Abby's Style | Kit's Style |
| Junk components | KKS Default (Glyph Components) / Text Based / None | KKS Default |

Kit's Style groups prepared food by gameplay use; Abby's Style groups it by food
family. These final KKS 1.3.0 names are presentation changes only, prepared with
the staged Apply work for the next installer build. Classification, sorting,
glyph allocation, codepoints and package behavior are unchanged. The installer
uses the short names in every interface language to preserve the existing layout.
The sealed 1.9.0 candidate retains its historical labels.

There are 24 configurations per language. Junk None removes component labels;
the authored content retains a weight annotation only for Junk-Heavy. The
installer performs no numerical conversion, unit substitution or translation.
Those literal localized values come from the signed content.

One language's package contains six canonical resources and a seventh small
`payload/string-modes.json` file. Its fixed schema describes sorted raw-byte
replacements for Abby's Style, text components and no components. It cannot
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
The stable food identifiers remain `food-v2` for Kit's Style and `family-food`
for Abby's Style in packages, saved state and the CLI; no migration is required.

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

## Staged configuration draft — October 20, 2026

Source preparation only on `codex/staged-apply-r001`, after the sealed 1.9.0
candidate. The owner deferred executable building and full validation until the
live Bethesda-version diff is complete. The sealed EXE and content are unchanged;
the application version remains unbumped until the next build is prepared.

The four configuration selectors now change an in-memory pending configuration.
They start no worker, package processing, verification, deployment or filesystem
operation. Apply Changes sits beside Play in the existing presentation. It is
enabled only for a different draft on the verified installed package with an
available cache. Returning all four choices to their installed values disables
Apply; calling its handler directly with equal values also does no backend work.

Startup loads the authenticated installed choices and cached manifest identity.
Apply captures the complete draft and uses the existing install preflight,
overlap consent and transaction. Only successful post-operation inspection can
establish installed state. Failure retains the last verified snapshot and draft,
disables Apply, and requires an explicit Check/recovery. Cancellation retains the
draft. Recovery synchronizes the UI with the configuration actually recovered.
Pending choices are session-local and are not saved as installation receipts.

Repair takes the currently installed configuration from the manager and leaves
an unapplied draft intact. Restore uses its existing independent transaction and
clears the installed UI snapshot after inspection. No transaction, rollback,
cache format, package schema, CLI deployment behavior or game-running guard is
redesigned. No partial/delta deployment optimization is introduced.

Package selection/drop retains signature verification, cache import and explicit
Install/Install update behavior. A new manifest is still an update even when its
four choices equal those installed; it is not hidden by the Apply no-op rule.
Selecting the exact installed package loads its actual installed choices rather
than misleading constructor defaults. Other selected packages retain their
existing initial-choice/capability behavior. Explicit Check can still perform
verification; selector changes cannot.

Focused source tests cover selector I/O prohibition, change-and-revert, direct
no-op Apply, startup/cache identity, complete Apply dispatch, verification failure,
cancellation, recovery, Repair/Restore, package update identity, older capability
gates, translations and the existing 900x700 minimum layout. Full regression,
new-baseline archive fixtures, executable build and exact-EXE checks remain
deferred. No themes, preview artwork or unrelated UI polish was added.
