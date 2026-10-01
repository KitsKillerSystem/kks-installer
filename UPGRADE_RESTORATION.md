# Restoring KKS 1.0.0 from a future installer

Implementation update, 1 October 2026: this branch now implements the independent installer candidate described in [INDEPENDENT_INSTALLER.md](INDEPENDENT_INSTALLER.md). The original 1.0.0 contract below is retained as provenance. Its same-baseline restoration sequence is implemented; newly certified Bethesda baselines use separate ownership-checked reconciliation and never receive old archive backups.

## Decision

No extra persistent metadata is required in 1.0.0. The existing schema-1 receipt, journal and content-addressed backups contain the installation-specific restoration facts. A future installer must ship a trusted compatibility entry for 1.0.0 and restoration code; it must not require the old installer EXE or old KKS font/string payloads. This document specifies that future implementation. It is not an automatic-upgrade feature added to 1.0.0.

The developer must preserve `source/release/manifest.json` as released. Trusted catalog entry:

- Release: KKS 1.0.0
- State directory: `.kks-installer-1.0.0`, relative to the selected game root
- Receipt/journal schema: 1
- Manifest SHA-256: `dda35c73a9c1119010a3a7c2d15517df2457b231d894e2b910dd34f1d5afd3e7`
- Supported baseline: Steam English Slasher build 25258219
- Managed files: two English font/config archives and three English loose string tables

The compatibility catalog must bind the known state-directory name and trusted manifest digest to the reviewed descriptor. A receipt's `manifest` value is a lookup key, never an authority to accept an arbitrary local/downloaded descriptor. A hash copied from the same untrusted receipt or descriptor does not authenticate it. Bundle reviewed compatibility data in the future installer, under its normal pinned/signed distribution trust boundary. Existing hashes protect integrity; they do not prove provenance against someone who deliberately rewrites local receipts/backups.

## Existing persistent data

`receipt.json` records `schema`, `manifest`, the resolved absolute `root`, `status` (installed/restored), `release`, and exactly five `files` entries. Each entry has `before` (trusted original SHA-256, or null for a loose table that did not exist) and `after` (the descriptor's installed SHA-256). `backups/<sha256>.bin` retains original bytes. Backup filenames alone are insufficient: rehash their contents. Archive originals may never be absent. Never infer original file presence from whether a backup happens to exist.

`pending.json`, when present, records the schema, manifest, root, operation, transaction, every path's before/after hashes and the previous receipt. All journal paths/hashes must be checked against the trusted old descriptor before recovery. Staging files are temporary. `operation.lock` serializes operations; its presence alone is not proof that an operation is running. Backups and restored receipts remain after a successful restore.

No original release descriptor is currently persisted beside the receipt. This is intentional: the future installer supplies the trusted descriptor. Current 1.0.0 restore/inspect/recover entry points always verify their embedded payloads, and their state directory is version-specific. A future implementation therefore needs a strictly restore/recover-only compatibility reader, bound to the old state directory, rather than invoking the new installer's ordinary restore path against old receipts or requiring old payload files. The test-only adapter demonstrates this separation; it is not a complete future updater to deploy unchanged.

## Required future sequence

1. Detect a supported installation and known KKS state folders without writing. Reject unknown active releases, multiple active states, unsafe paths, mismatched absolute root, malformed receipts or unsupported schemas. Resolve a recognized pending journal first under its owning descriptor. Keep every backup and receipt; do not delete old state to suppress a refusal.
2. Select the old descriptor from the future installer's trusted catalog. Validate receipt membership and each before/after hash against it. Verify every original backup and all current targets. Permit only exact old installed hashes or that same baseline's known vanilla hashes; absent loose targets are permitted only under the established repair/restore rules. A non-null receipt `before` always restores that verified file; null restores absence. Verify embedded font/config members, not just BA2 header shape.
3. Before restoring anything, hash all old-build identity files: Fallout76.exe, SeventySix.esm and SeventySix - Localization.ba2. Also preflight every managed archive/table. Require the exact old baseline/known-installed versions. **If any identity or target is an unknown/newer Bethesda version, do not restore even one old archive.** Report: “The game files have changed since these backups were created. Close Fallout 76 and verify/update the game in Steam, then use a KKS release certified for that build. Your backups have been retained.” Resolve conflicts/leftover loose files deliberately; never perform a stale rollback or fabricate a restored receipt.
4. Require Fallout 76 to be closed. Acquire the existing old-state operation lock and the new installer's cross-version coordination lock in a deterministic order; exclude concurrent installers. Recheck identities/current hashes after acquiring locks and before preparing writes. Use the executable guard and safe-path/reparse/hardlink rules. Verify the proposed new release supports the same baseline before unnecessarily removing old KKS. If a Bethesda update is required first, stop and direct the user to Steam; backups cannot update or downgrade the game safely.
5. Stage restoration from verified backups on the game volume; check space and hashes. Create a durable restore journal before changing game files. Recheck targets, replace atomically per file, remove only receipt-proven previously absent loose files, then reopen/hash every restored file and BA2 member. On known partial failure recover through the journal. Any external/unknown change stops recovery with state/backups retained. A lost power transition must never be guessed from display version strings.
6. Mark the old receipt restored only after complete verification; retain its backups. Verify the now-vanilla executable, ESM, localization and every target against the **new release's** trusted supported baseline. If unsupported, leave verified vanilla with old restoration data retained and stop. Never install a new payload simply because old restoration succeeded.
7. Install the new release using its normal fresh receipt/backups/journal, then reopen/hash its targets and embedded assets. Failure after the old restore leaves verified vanilla (or a new release's recoverable journal), with old data retained. A future UX may combine the stages, but must not advertise whole-upgrade atomicity unless it actually implements it.

## Boundaries and validation

Moving the game folder currently invalidates the receipt's absolute-root binding. Do not rewrite roots automatically. Missing/damaged backups, an unknown receipt digest, changed game files or a journal with unknown hashes require a safe stop and recovery/Steam verification guidance. Retaining old state after a Bethesda update does not authorize restoring it. A later installer must explicitly handle obsolete state only after proving a compatible clean new baseline; 1.0.0 does not implement that migration.

The production 1.0.0 binary keeps its tested Install/Repair/Restore/Recover behavior. `source/tests/test_future_restore.py` proves that the persisted data is sufficient using only a trusted descriptor and restoration reader; it also tests stale-build refusal and interrupted restoration. TEST_RESULTS.json records the corresponding real-archive proof and five actual-EXE newer-file refusals. These tests justify keeping the existing schema rather than introducing new release-time infrastructure.
