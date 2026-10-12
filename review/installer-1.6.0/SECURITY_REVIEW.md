# Installer 1.6.0 — release security review

**Release disposition: owner accepted the remaining detections and coverage limitations on October 11, 2026.** This is a project release decision, not a conclusion that the detections are false positives. Audit A001 remains **LIKELY BENIGN / PARTIALLY EXPLAINED**, with its original evidence, uncertainty and historical hold recommendation preserved. The owner closed the certificate inquiry and cancelled the proposed VM reproduction.

## Exact reviewed executable

- File: `KKSInstaller.exe`, 15,766,831 bytes; Installer 1.6.0.
- SHA-256: `46598f77674656442befca5e128da183682e720425c6ec40ff386a4bbfe4a589`
- [VirusTotal detection report](https://www.virustotal.com/gui/file/46598f77674656442befca5e128da183682e720425c6ec40ff386a4bbfe4a589/detection)
- Recorded analysis: **October 11, 2026, 19:41:24 CDT / October 12, 00:41:24 UTC**.
- **8/71 detections**, 63 undetected; four additional engines could not process the file type. No timeout/failure was listed. Unsupported results are outside the 71-engine denominator and are not clean results.
- [Complete recorded vendor output](virustotal-results.json). This is a dated record; the live service may change.

The published executable is byte-identical to the scanned candidate. Its original candidate ZIP remains preserved privately; the public ZIP updates release documentation only. No executable, runtime, signature, compression strategy or code was changed to alter the antivirus score. Content packages are separate Nexus downloads and are outside the installer-only scan requirement.

## Remaining detections

| Vendor | Recorded label | Evidence limit |
|---|---|---|
| Arctic Wolf | Unsafe | Broad verdict; no engine-specific trigger exposed. |
| Bkav Pro | W32.Malware.E5FED199 | Detection label alone does not establish a malware family or the matched code path. |
| DeepInstinct | MALICIOUS | Generic verdict; the responsible feature is not disclosed. |
| Elastic | Malicious (moderate Confidence) | Classifier verdict; the exact trigger remains unknown. |
| SecureAge | Malicious | No precise trigger supplied; source review is not a vendor false-positive determination. |
| SentinelOne (Static ML) | Static AI - Suspicious PE | Static classifier label. Bundled Python/onefile packaging is context, not a proven cause. |
| Skyhigh (SWG) | BehavesLike.Win64.Backdoor.wc | Heuristic-style label; no specific backdoor/network action is established by this label. |
| Zillya | Trojan.Blank.Script.2228 | Exact-file finding remains unresolved; appearances on older packaging variants do not establish the cause. |

All eight exact triggers remain unresolved. No vendor has confirmed a false positive for this file. KKS continues pursuing legitimate false-positive/vendor remediation as a **non-blocking maintenance workstream**. Submission materials and vendor routes are prepared; no vendor reply or completed submission is claimed by this release. New evidence of an actual security defect would require action.

## Source and normal behavior

Exact build source: [`8cad8b2195c069518ab0fc4334b77a816c25347d`](https://github.com/KitsKillerSystem/kks-installer/tree/installer-v1.6.0), tagged `installer-v1.6.0`. The later `v1.6.0` publication commit adds documentation/evidence only. [Build receipt and logs](build/) record a clean-source build using Python 3.12.14, PyInstaller 6.22.3, Tcl/Tk 8.6.12 and hash-pinned dependencies, without UPX. The final EXE is **not Authenticode-signed**. The runtime came from the disclosed local Codex Python distribution; a matching version string alone does not promise identical binaries across machines.

KKS is an offline game-resource patcher. It verifies signed local content packages, supported game identity, bounded archive contents and intended changes; saves verified originals; and supports profile switching, Repair and Restore Baseline. Overlapping existing modifications require explicit, input-bound confirmation. It does not inject code into Fallout 76, add an autorun/service or download updates. The optional Play button explicitly opens the fixed Steam game URI after state checks. PyInstaller onefile startup extracts its bundled Python/Tk/runtime into a temporary `_MEI` directory. These are expected behaviors, not proof of why a scanner flagged the file.

## Certificate finding: what is and is not established

CAPE's reported Event 13 attributes an AuthRoot certificate-store Blob write to `C:\Windows\sysmon.exe`. The fingerprint `F40042E2E5F7E8EF8189FED15519AECE42C3BFA2` matches Microsoft Identity Verification Root Certificate Authority 2020 and occurs in the signing chains of 16 bundled runtime binaries. Monitoring/Windows signature validation is the leading explanation. No KKS certificate-import or trust-store-write path or unexplained helper was found in the reviewed source/bundle.

The actor PID, event timing, causal call chain, original Blob and before/after effective trust change remain unproven. The authenticated account could not retrieve the original CAPE EVTX (`ForbiddenError`). Three bounded read-only local probes showed no persistent change across 154 certificate-key records, but the root was already cached and snapshots do not establish which process performed a transient operation. No controlled VM reproduction was performed. This supports the limited classification **LIKELY BENIGN / PARTIALLY EXPLAINED**, not full attribution or an antivirus clearance. [Preserved audit summary and original evidence hashes](certificate-audit-summary.json).

## Validation and coverage limits

The exact build passed **210 automated regressions**. Its final EXE passed **15 compiled checks**, covering all four equipment/perk combinations in each language, signed package verification, Repair and exact cache-free Restore. The previous branding build passed **48 broader package/baseline checks**, including overlap consent/invalidation, modified-baseline continuity and language isolation; a source/AST comparison verified that the final source changed branding only. Final GUI title observation and three fresh publication-time read-only version/package checks also passed. See [validation](evidence/VALIDATION.json) and [earlier 48 checks](evidence/previous-branding-48-checks.json).

Audit A001 matched all 20 embedded KKS code objects and 998 native/data members to the recorded build inputs. In the preceding/final bundle comparison, only two Python modules changed; 171 were exact. Sixteen native binary differences were limited to signing-table/checksum data; normalized code/data were exact. [Bundle comparison](evidence/bundle-comparison.json). This establishes provenance within the recorded build, not independent attestation.

Sandbox reports had incomplete execution coverage; at least one reported a missing `api-ms-win-core-path-l1-1-0.dll`. An absence of reported network activity in an incomplete run is not a behavioral clearance. Functional regression tests are not malware certification. The findings are not concealed or conclusively dismissed, and this release does not advise disabling antivirus or bypassing its warnings.
