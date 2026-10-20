# Installer 1.10.0 — exact-file security review

Reviewed October 20, 2026. Seven warnings remain unresolved. No clean result, vendor-confirmed false positives or security certification is claimed. The project owner accepted release of this exact executable with the remaining warnings and coverage limitations on October 20, 2026. Dedicated security hardening is the next work phase.

## Exact file and scan

- KKSInstaller.exe, 20,363,770 bytes, Installer 1.10.0.
- SHA-256: 5b49321ebb891dc33b80a4af511f5a3b1bfb55f08220a65ee215db189961480f
- Frozen source: e3760cd115d4852f2ee13384b10788a91afa25c7.
- [VirusTotal report](https://www.virustotal.com/gui/file/5b49321ebb891dc33b80a4af511f5a3b1bfb55f08220a65ee215db189961480f/detection), 2026-10-20 19:29:42 UTC / 14:29:42 CDT.
- 7 malicious verdicts and 63 undetected: **7/70**. TEHTRIS timed out. Four additional engines could not process the file type. All 75 vendor rows are recorded in [the exact scan capture](virustotal-results.json).
- The outer EXE is not Authenticode-signed. Content publisher signatures are separate.

The report concerns the complete standalone EXE. It does not establish separate inspection of every embedded member. Content and manual packages remain outside the installer-only VirusTotal scope. The executable was not rebuilt or altered after its validated build.

## Remaining vendor findings

| Vendor | Label | Bounded assessment and uncertainty |
|---|---|---|
| Bkav Pro | W32.Malware.CCC32327 | Changed from W32.Malware.E7662435 on 1.8.0 to W32.Malware.CCC32327. The report provides a malware label but no matching code, rule, trace or reason. The exact new application code and native runtime provenance were checked; no unexplained embedded code was found. A changed label on a changed binary does not establish a new malicious behavior. Exact trigger unknown; not vendor-confirmed as a false positive. |
| DeepInstinct | MALICIOUS | Same MALICIOUS verdict as the recorded 1.8.0 scan. A generic verdict without an identified code path. Reviewed source changes concern bounded package features, UI and historical receipt compatibility. The report does not connect the verdict to one of those changes. Exact trigger remains unknown; recurrence does not resolve it. |
| Elastic | Malicious (moderate Confidence) | Same Malicious (moderate Confidence) label as 1.8.0. The label communicates a classifier confidence, not a demonstrated behavior. Source/bundle identity checks pass and no unexplained application or native code was found. There is no vendor rationale identifying why this file is flagged. Classifier cause unknown; confidence wording is not a safety finding. |
| McAfee Scanner | Ti!5B49321EBB89 | Changed from Undetected on 1.8.0 to Ti!5B49321EBB89. This is the newly appearing vendor warning. Its suffix matches the first twelve hexadecimal characters of this file's SHA-256, but that observation does not explain the detection. The review explicitly checked all newly changed application modules, launcher/source identity and 16 native-file differences; those native loaded code/data/resources are unchanged. The captured report supplies no matching malicious code path or behavior. New unresolved warning for this exact file; do not infer a threat family or dismiss it from the label. |
| SecureAge | Malicious | Same Malicious verdict as 1.8.0. A generic verdict with no exposed rule or trace. Frozen application/source matching and bounded signed-data handling provide provenance; they do not prove the vendor's cause or negate the verdict. Exact trigger unknown; no vendor determination received. |
| SentinelOne (Static ML) | Static AI - Suspicious PE | Same Static AI - Suspicious PE label as 1.8.0. The result explicitly identifies static classification. The EXE is a PyInstaller onefile program without UPX and is not Authenticode-signed. Those are packaging facts, not a demonstrated reason for this classifier's warning. Static classifier reason unknown; no confirmed false-positive finding. |
| Zillya | Trojan.Blank.Script.2228 | Same Trojan.Blank.Script.2228 label as 1.8.0 and recorded preceding releases. The label does not provide the detected script, matching rule or behavioral trace. Every embedded KKS module and the launcher match their reviewed source; no unexpected Python module was added. The known string_modes addition accepts bounded signed data and has no executable hooks. Exact trigger remains unresolved; historical recurrence is not vendor clearance. |

Compared with the recorded 1.8.0 scan, McAfee Scanner newly flags this file; Bkav's label changes. Arctic Wolf and Skyhigh (SWG) change to Undetected. TEHTRIS changes from Undetected to Timeout. The other 70 outcomes match. These are dated reports for different binaries; the lower headline count is not evidence that a warning was resolved or that this file is safer. [Full comparison](scan-comparison-1.8-to-1.10.json).

## Source and bundle provenance

The binary/source comparison checks the complete executable against its build receipt. Every embedded KKS Python module and the launcher match frozen source. Compared with Installer 1.8.0, 991 shared outer members are identical and two installer-art PNGs are added. Changed outer members are PYZ.pyz, the launcher and 16 native runtime files. The native differences are restricted to Authenticode metadata/security-directory fields/checksums; loaded code, data and resources are exact to 1.8.0, and current bytes match recorded runtime inputs. This establishes provenance, not a vendor-confirmed explanation for antivirus findings.

One application module, string_modes, is added; eight application modules change. Other embedded Python modules are unchanged. Changes add thirteen-language content support, certified game baselines, signed Food/Junk recipes, staged selectors with explicit Apply Changes, and compatibility with authenticated historical Family Food receipt captions. Halloween art is loaded locally.
Comparison: https://github.com/KitsKillerSystem/kks-installer/blob/v1.10.0/review/installer-1.10.0/binary-source-review.json
Source diff: https://github.com/KitsKillerSystem/kks-installer/blob/v1.10.0/review/installer-1.10.0/source-diff.patch

String recipes contain bounded data only, with checked schema, allowed choices, sorted unique IDs, disjoint category scopes and signed output hashes. Packages remain publisher-signed; archive/member targets remain application-controlled. Historical caption compatibility admits only the known captions of the authenticated family-food profile and preserves manifest, root, target-set, baseline and hash checks.

The runtime is an offline local resource patcher. It verifies local packages and installation state, updates defined resources and preserves restoration data. Play explicitly launches a fixed Steam URI. No automatic content download, service or autorun feature was added. PyInstaller onefile startup extracts its runtime into a temporary directory. These facts are not proof of any detection's cause.

## Validation attribution

The full 250-test suite passed on source 8c9e21a in 634.297 seconds. Final source e3760cd received 26 focused UI/Apply tests in 11.994 seconds, 18 language/resize checks and reviewed screenshots. The reuse proof establishes unchanged backend/test bytes and reviewed presentation-only differences. The full suite was not rerun against the final artwork revision.
Reuse proof: https://github.com/KitsKillerSystem/kks-installer/blob/v1.10.0/review/installer-1.10.0/presentation-test-reuse.json
Build receipt and logs: https://github.com/KitsKillerSystem/kks-installer/blob/v1.10.0/review/installer-1.10.0/build/build-receipt.json

The exact final EXE authenticated thirteen then-current packages and exercised a real historical-source English installation through a Steam update, migration, Repair and cacheless restoration to the exact new baseline. The historical receipt is retained.
Exact validation: https://github.com/KitsKillerSystem/kks-installer/blob/v1.10.0/review/installer-1.10.0/exact-exe-validation.json

The earlier Polish R002 package authenticated correctly but had a separate font-routing defect; authentication alone did not prove rendering. Corrected Polish R003, sequence 3, now passes the same exact EXE's installation/update, archive readback, Repair and cacheless Restore. All string tables and mode recipes remain unchanged. Native Polish font faces/aliases and ordinary glyphs are preserved in the corrected library.
Corrected package SHA-256: 351f1526f7330006b8ae72c1dd66d1a86868e8d7eb2bc3cf26c15ef9599bf50a
Polish validation: https://github.com/KitsKillerSystem/kks-installer/blob/v1.10.0/review/installer-1.10.0/polish-package-validation.json
Font validation: https://github.com/KitsKillerSystem/kks-installer/blob/v1.10.0/review/installer-1.10.0/polish-font-validation.json

No native-speaker or live-game acceptance is inferred from these automated checks. The toolchain remains Python 3.12.14 and PyInstaller 6.22.3, with pinned dependencies and no UPX. Public copies redact workstation home paths; originals remain private and hashed.
Copy provenance: https://github.com/KitsKillerSystem/kks-installer/blob/v1.10.0/review/installer-1.10.0/PUBLIC_COPY_PROVENANCE.json


## Behavioral and scan coverage limits

TEHTRIS's timeout supplies no completed detection result. Avast-Mobile, BitDefenderFalx, Symantec Mobile Insight and Trustlook are unable to process this file type; those are not clean scans.

At the captured observation, the Behavior page still states that some sandboxes are analysing the file. Zenbox, VirusTotal Jujubox, CAPE Sandbox and CAPA are listed. Its interim NOT FOUND summaries for detections, MITRE signatures, IDS/Sigma rules, dropped files and network communications do not establish a clean dynamic result. No current behavioral clearance or absence-of-network conclusion is claimed. Any later behavior result should be assessed before final promotion.

Jujubox later reported a startup error: api-ms-win-core-path-l1-1-0.dll was missing. Visible activity includes extraction/loading of the bundled runtime under a temporary _MEI directory. This sandbox result does not establish successful application execution. Some sandbox analyses were still pending; the current results are partial. [Behavior capture](virustotal-behavior.json).

CAPA reports static capabilities for Xen-related strings, analysis-tool strings and QueryPerformanceCounter timing. The latter is imported by 22 bundled runtime components whose loaded code/data are byte-identical to 1.8.0; KKS application source contains no direct Xen or QueryPerformanceCounter term. The overview provides no rule-match addresses or exact analysis-tool strings, so the Xen/tool references cannot be attributed conclusively. Static labels do not demonstrate executed evasion or prove a benign cause. [Bounded context](capa-static-context.json).

Vendor reasons and engine versions are not exposed in the captured overview. Packaging and provenance facts do not prove the reason for a vendor's warning. No vendor has confirmed a false positive for this exact executable.

## Release disposition

The bounded review found no new confirmed security defect in the inspected source, dependencies or source/bundle correspondence. This is not a comprehensive exclusion of malware, and the seven exact triggers remain unresolved.

The earlier certificate inquiry remains closed at LIKELY BENIGN / PARTIALLY EXPLAINED with its original uncertainty. No cancelled VM work, vendor-remediation campaign or score-chasing rebuild was restarted.

The project owner explicitly accepted the current exact-file scan and instructed publication on October 20, 2026. Release proceeds with seven unresolved warnings, the timeout/unsupported outcomes and the disclosed partial behavioral coverage. This is an owner release decision, not vendor clearance or a safety guarantee. The executable remains unchanged. The next phase is dedicated security hardening. [Recorded decision](OWNER_RELEASE_DECISION.json). Do not advise users to disable protection.
