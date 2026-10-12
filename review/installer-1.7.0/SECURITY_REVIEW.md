# Installer 1.7.0 — exact-file security review

**Scan and source/bundle review complete; seven residual warnings remain disclosed. This candidate has not been published.** The owner authorized this scan on October 12, 2026 and plans a quiet GitHub update. No claim of a clean result, vendor-confirmed false positives, or VirusTotal certification is made. The closed 1.6.0 certificate investigation and cancelled VM work are not reopened by this update.

## Exact executable and result

- File: `KKSInstaller.exe`, 15,766,981 bytes, version 1.7.0.
- SHA-256: `85112d5d56ac7c83e31d6f0488a8af080baae85320dbdb3bdac57b44afdc9749`
- [VirusTotal report](https://www.virustotal.com/gui/file/85112d5d56ac7c83e31d6f0488a8af080baae85320dbdb3bdac57b44afdc9749/detection); analysis **October 12, 2026, 09:24:38 CDT / 14:24:38 UTC**.
- **7/71**: seven malicious verdicts, 64 undetected; four additional engines unable to process the file type. No detection-engine timeout or failure listed. Unsupported results are not clean results.
- [All 75 recorded vendor outcomes](virustotal-results.json), [visible detection table](virustotal-detection-dom.txt), [exact-file details](virustotal-details.txt).

The full standalone EXE was submitted, not a smaller launcher or outer ZIP. A top-level scan does not guarantee that every embedded member was separately analyzed. Content/manual packages are outside the installer-only scan scope. The executable was neither rebuilt nor altered after scanning.

## Findings and comparison

| Vendor | Label | Evidence and limit |
|---|---|---|
| Bkav Pro | W32.Malware.7B1CF3CE | Label changed from W32.Malware.E5FED199 to W32.Malware.7B1CF3CE. No matching code path or vendor-confirmed cause is supplied. |
| DeepInstinct | MALICIOUS | Generic classifier verdict; the exact trigger is not disclosed. |
| Elastic | Malicious (moderate Confidence) | Classifier verdict; the exact trigger is not disclosed. |
| SecureAge | Malicious | Generic verdict; no precise trigger is supplied. |
| SentinelOne (Static ML) | Static AI - Suspicious PE | Static classifier label; onefile Python packaging is context, not a demonstrated cause. |
| Skyhigh (SWG) | BehavesLike.Win64.Backdoor.wc | Heuristic-style label; the label does not establish a specific backdoor or network action. |
| Zillya | Trojan.Blank.Script.2228 | The same label appeared in the recorded 1.6.0 scan; its exact trigger remains unresolved. |

These are the same seven vendors that remain from the recorded 1.6.0 8/71 result. Arctic Wolf changes from Unsafe to Undetected; Bkav's label changes as recorded above. All other recorded vendor outcomes match. This comparison is between dated reports of different exact files, not proof that a warning was resolved or that the new executable is safer.

## What changed and what was checked

Build source: `28e8f7edb277d767ddebb062682f66b7955b9341`. The runtime changes are limited to application version/capability policy and signed-manifest validation for French/German optional equipment and perk profiles. The content builder and two regression tests support those changes. Writer targets and algorithms, source-language restoration, UI, launcher Unicode handling and drag/drop behavior remain unchanged. [Source diff](source-diff.txt).

[Exact bundle comparison](bundle-comparison.json) finds the same 1,009 outer members: 1,008 are byte-identical to released 1.6.0; only PYZ.pyz differs. Of 173 Python modules, 171 are byte-identical and only `kks_installer._application` and `kks_installer.packages` changed, as expected. Every native/data member, launcher and runtime hook is exact. The build receipt's source hashes were checked before publication documentation was edited. These checks establish provenance, not a vendor determination.

The unchanged toolchain is Python 3.12.14, PyInstaller 6.22.3 and hash-pinned dependencies, built without UPX. The EXE is not Authenticode-signed. [Build receipt and logs](build/). **212 regression tests** and **24 checks using this exact executable** pass: both B003 upgrades, all French/German equipment/perk combinations, profile-preserving Repair, unrelated-member preservation and exact cacheless Restore. [Compiled checks](exe-validation.json). No live-game or native-speaker acceptance is implied by these tests.

## Behavior, uncertainty and release handling

KKS is an offline resource patcher. It validates publisher-signed content, verifies the supported game baseline, writes bounded resources, retains originals and supports restoration. It does not inject code into Fallout 76, create an autorun/service or download updates. A user-selected Play action opens a fixed Steam game URI. PyInstaller onefile startup extracts its runtime to a temporary _MEI directory. These behaviors explain the tool's design; they do not prove the reason for a vendor's flag.

The [captured behavior report](virustotal-behavior.txt) shows CAPA, CAPE Sandbox, VirusTotal Jujubox and VirusTotal Observer results; Zenbox was still processing. Three Sigma matches are listed: executable creation, a root/CA/AuthRoot store event, and Python loading in a non-Python-named process. Temporary _MEI runtime extraction and game-installation discovery are visible. One sandbox reports that api-ms-win-core-path-l1-1-0.dll is missing, limiting that run's coverage. No network communications were listed at capture, but this is not a network-behavior clearance. These are bounded observations, not a comprehensive malware exclusion.

The certificate-related rule also appeared in the earlier 1.6.0 inquiry. Its recurrence is disclosed, not treated as resolved. The earlier certificate audit remains **LIKELY BENIGN / PARTIALLY EXPLAINED**, with its original uncertainty preserved. Identical native members support continuity with that reviewed runtime; they do not establish the actor or cause of this run's certificate event. The owner closed that inquiry and made vendor remediation non-blocking unless new evidence establishes an actual defect. No additional VM or certificate investigation was performed.

No new confirmed security defect was established by this bounded update review. The seven exact vendor triggers remain unresolved. Public release timing and residual-risk acceptance are separate from this scan authorization; this record does not invent approval of the new scan result. Keep accurate disclosure, do not advise disabling protection, and preserve the exact reviewed bytes for publication.
