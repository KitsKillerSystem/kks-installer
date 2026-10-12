# KKS content 1.2.0 — English and Russian

The owner corrected the public content version to **1.2.0** because the previous public English release already occupies 1.1.2. This reissues the new, unpublished English/Russian R001 candidates; it does not replace the historical public 1.1.2 release. Both languages use revision 1, with monotonically increasing sequences: English 23, Russian 12. **Installer remains 1.6.0.**

[New identities and checksums](VERSION_CHANGE.json) · [Version-transition checks](VERSION_TRANSITION_VALIDATION.json)

The normal source-based package builder signed new manifests with the existing publisher key. Only content version, package revision, release sequence, creation time, build label and QA report reference changed. Inside each signed ZIP, only `manifest.json` and `manifest.sig.json` differ from the prior candidate. All six payload files, native game identities, archive replacement hashes, categories and optional-profile hashes are exact. Fonts, glyph assignments, ordering, translations, equipment naming and perk cards were not regenerated or edited.

Existing [shared-baseline validation](../content-1.1.2/README.md) remains applicable to these identical resources. The 1.2.0 check adds exact manifest/payload comparison, signatures through the published EXE, updates from the latest prior 1.1.2 candidates in both languages, unchanged installed resources, original-baseline retention, hybrid options, Repair, cache-free Restore, rejection of an older package after Restore and eligibility to reinstall the same 1.2.0 package. All 16 new compiled checks passed. All four profile output hashes remain unchanged; the hybrid configuration was exercised at runtime.

The manual ZIPs were assembled from the same authoritative sources; all six resources, two optional tables and XML contents are exact. Their documentation, signed-package reference, checksums and versioned XML filename changed. The manual resource-tool UI and new in-game rendering were not retested because the resources are unchanged; no new visual observation is claimed.

Once a higher sequence is installed, older signed packages are intentionally rejected, even after Restore. Keep the new complete 1.2.0 ZIP for reinstallation. Same-language updates retain the existing pre-KKS baseline; Restore remains required before switching languages. Steam build 25636769 only.

Download content separately through [Nexus Mods](https://www.nexusmods.com/fallout76/mods/4301). This preparation has not uploaded it to Nexus. [Installer 1.6.0](https://github.com/KitsKillerSystem/kks-installer/releases/tag/v1.6.0), its EXE/ZIP hashes, source/release tags and [VirusTotal disclosure](../installer-1.6.0/SECURITY_REVIEW.md) are unchanged. Its bundled 1.1.2 content references are historical documentation, not a compatibility restriction; current release instructions identify 1.2.0.
