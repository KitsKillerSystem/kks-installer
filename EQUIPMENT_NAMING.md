# Equipment naming preview — Installer 1.4.0

Private English prototype, not a public release. Full KKS remains the default and
recommended treatment. A supported content ZIP also offers Vanilla Equipment
Naming, restoring all WEAP:FULL, ARMO:FULL and INNR:WNAM values. INNR uses WNAM in
the actual ESM and xTranslator authoring data. All other string values and assets
remain canonical KKS; no sorting workaround is applied.

The publisher's `build_content.py --equipment-naming --translation-localization`
generates the category IDs automatically from the certified ESM. Schema 2 signs
those IDs, the fixed algorithm identifier and the alternate STRINGS hash/size,
alongside the unchanged complete canonical payload. It adds no ZIP member or
second payload. Existing schema-1 packages remain supported with Full KKS only.
The preview is limited to the English Localization profile.

At installation, the app verifies the canonical package and current game owner,
reads the hash-pinned native STRINGS member from Localization.ba2, restores the
selected values as raw bytes, and verifies the derived result against its signed
hash before starting the game transaction. XML-omitted values and native control
bytes are retained. Generated cache bytes never replace the canonical cache.

Saved owner references record `full-kks` or `vanilla-equipment`; the same signed
package and release sequence can switch in either direction. Repair retains the
installed choice and regenerates its derived cache. Receipts, output ownership
checks and recovery use the selected signed hashes. Restore needs only signed
descriptors and original backups, preserving originally absent loose files.

First installation of schema-2 content upgrades manager history to schema 5.
Use Installer 1.4.0 afterward, including after Restore; older applications cannot
read that history. Existing language histories are retained. Downgrading to an
older content sequence remains unsupported; return to Full KKS with this same ZIP.

CLI: `--naming full-kks` (default) or `--naming vanilla-equipment` on check/install.
The GUI enables its naming selector only for a package that advertises support.
Repair and Restore always operate on the saved installed profile.

Validation: the 169-test suite includes exact scope, category discovery, both
switch directions, original file presence/absence, repair and cache damage,
restore without payloads, malformed metadata, foreign-file refusal, and twelve
interrupted-switch scenarios. Real-file executable acceptance is recorded with
the private E001 feature checkpoint; automated checks do not establish gameplay
acceptance.
