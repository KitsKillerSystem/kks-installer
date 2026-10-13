# Installer 1.8.0 — exact-file security review

Reviewed October 13, 2026. Eight warnings remain unresolved. No vendor-confirmed false positives, clean result or security certification is claimed. The owner accepted the remaining detections and documented coverage limitations for release on October 13, 2026. [Release disposition](RELEASE_DISPOSITION.json). This acceptance does not resolve the warnings.

## File and scan

- `KKSInstaller.exe`, Installer 1.8.0, **15,774,265 bytes**.
- SHA-256: `b5950ae64451436dc65c3a6934a01ba493b272280896c863d25c3ac5f2599e98`.
- [Exact VirusTotal report](https://www.virustotal.com/gui/file/b5950ae64451436dc65c3a6934a01ba493b272280896c863d25c3ac5f2599e98/detection), **2026-10-13 20:08:14 UTC / 15:08:14 CDT**.
- **8/71**: eight malicious verdicts and 63 undetected; four additional engines cannot process this file type. No detection-engine errors or timeouts appear in the captured table.
- [All 75 vendor outcomes](virustotal-results.json), [table capture](virustotal-detection-dom.txt), [file identity/details](virustotal-details.txt), [screenshot](virustotal-detection.png).

The complete standalone EXE was submitted, not a smaller launcher or the distribution ZIP. A top-level scan does not establish separate inspection of every embedded member. Unsupported results are not clean results. Content packages are outside the installer-only scan scope. The EXE is unchanged since its validated build.

## Remaining findings

| Vendor | Label | Evidence and uncertainty |
|---|---|---|
| Arctic Wolf | Unsafe | Unsafe on 1.8.0; Undetected on the recorded 1.7.0 scan. This vendor also flagged 1.6.0. No specific trigger is provided. |
| Bkav Pro | W32.Malware.E7662435 | Label changes from W32.Malware.7B1CF3CE to W32.Malware.E7662435. No code-level explanation is provided. |
| DeepInstinct | MALICIOUS | Generic classifier verdict; precise trigger undisclosed. |
| Elastic | Malicious (moderate Confidence) | Classifier verdict; precise trigger undisclosed. |
| SecureAge | Malicious | Generic verdict; precise trigger undisclosed. |
| SentinelOne (Static ML) | Static AI - Suspicious PE | Static classifier label; Python packaging is context, not a proven cause. |
| Skyhigh (SWG) | BehavesLike.Win64.Backdoor.wc | Heuristic-style label; no matching backdoor/network action established by this label. |
| Zillya | Trojan.Blank.Script.2228 | Same label as the recorded preceding scans; precise trigger remains unresolved. |

Arctic Wolf is the additional flag compared with the recorded 1.7.0 result; Bkav's label also changes. [Complete dated comparison](scan-comparison-1.7-to-1.8.json). These are different binaries; neither the count nor continuity establishes a vendor's reason or safety.

## Source and binary review

Build source: `fca6a862ae138ac8953fa30fb1f69adf77718a33`. The changes add Portuguese package/UI support, fixed locale resource paths and capability checks, and state-schema 7 for independent Portuguese release history. Historical schemas 2–6 retain their exact allowed fields; later English installs preserve schema-7 Portuguese history. The new Portuguese catalog supplies UI translations. Four existing bundled application modules change and one catalog is added. [Source diff](source-diff.txt).

Archive writing, recovery algorithms, launcher, runtime hooks, drag-and-drop and network behavior are unchanged. [Bundle comparison](bundle-comparison.json): the same 1,009 outer members, 992 exact; PYZ.pyz and 16 native files differ. The native differences are restricted to Authenticode certificate blobs, security-directory sizes and PE checksums. Loaded native code, data and resources are exact. All 16 current signatures validate as OpenAI OpCo, LLC, and the files match the recorded runtime inputs. [Native provenance](runtime-signature-provenance.json), [signature checks](runtime-signatures.json). The bootloader code/resources are exact; its expected build/debug timestamp changes. [Bootloader comparison](bootloader-comparison.json). These facts establish provenance, not false-positive findings.

The toolchain remains Python 3.12.14 and PyInstaller 6.22.3 with pinned dependencies and no UPX. The outer EXE is **not Authenticode-signed**; publisher signatures on content are separate. [Build receipt and logs](build/) have workstation-home paths redacted for publication; original private evidence is retained.

**217 regression tests and 16 exact-EXE checks pass:** 14 lifecycle checks covering signature verification, a private predecessor upgrade, all four options, Repair, rollback rejection, unchanged unrelated members and exact cacheless Restore; two additional checks reject a tampered signature and a manual archive. [Lifecycle results](exe-validation.json), [rejection results](exe-security-validation.json). No native-speaker or live-game acceptance is inferred from these tests.

## Behavior and coverage limits

KKS is an offline resource patcher. It verifies publisher-signed local packages, checks the game baseline, updates bounded resources and retains restoration data. It does not inject game code, add a service/autorun or automatically download content. The explicit Play action opens a fixed Steam URI. PyInstaller onefile startup extracts its runtime into a temporary `_MEI` directory. These design facts are not an explanation proven by the detection vendors.

The captured [behavior page](virustotal-behavior.txt) contains CAPA, CAPE Sandbox, Jujubox and Observer results. Zenbox was still analyzing at capture. The detection-engine table is complete, but sandbox coverage is incomplete. No behavioral clearance is claimed.

The available runs show temporary `_MEI` runtime extraction/loading, game-location discovery and an Explorer `OpenWithProgids` registry value. CAPE lists three Sigma matches: executable creation, a root/CA/AuthRoot store event, and Python loading in a non-Python-named process. These same three rule names appeared in the preceding release's report. Recurrence is disclosed, not treated as resolved; the earlier certificate inquiry's uncertainty remains. CAPA also lists general capabilities and an obfuscated tag; these summaries do not establish a specific malicious code path.

Jujubox reports a missing `api-ms-win-core-path-l1-1-0.dll`; that execution did not establish normal application behavior. No network communications were listed in the grouped summary at capture, but this is not proof of absence. Pending Zenbox results and the missing-library failure limit the evidence. No new broad certificate investigation or AV-score-chasing rebuild was performed.


The earlier certificate inquiry remains **LIKELY BENIGN / PARTIALLY EXPLAINED** and closed at the owner's direction; the cancelled VM investigation was not restarted. Its uncertainty remains. No such defect was established by this bounded source/bundle review, but the eight detection triggers remain unresolved. Users should not disable protections based on this review.
