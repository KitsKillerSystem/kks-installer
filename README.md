# KKS — Kit's Killer System

## Independent installer 1.1.0 — manual-review candidate

This branch contains **installer application 1.1.0** with separately signed, complete content ZIPs. **Content 1.0.1** certifies the unchanged KKS 1.0 font/configuration/strings for Steam English build **25636769**. Application and content versions are independent. The installer EXE is unchanged from the reviewed 1.1.0 build.

The candidate accepts a ZIP through Choose package, by dropping it on the window, or by dropping it onto the EXE. It verifies the publisher signature, every file, the game baseline and saved installation before enabling installation. Complete packages permit direct jumps over intermediate releases. Repair uses the verified local cache; Restore uses authenticated descriptors and original backups without needing a download or the old EXE.

Reviewers: start with the [current handoff and test evidence](review/installer-1.1.0/README.md), then [SECURITY_REVIEW.md](SECURITY_REVIEW.md) for current file/network/process/privilege scope and the source map. Exact new artifact hashes and test/build evidence are supplied with the review candidate; root-level 1.0 hashes remain historical.

See [the implementation and package contract](INDEPENDENT_INSTALLER.md), [current build instructions](BUILD.md), and [the original 1.0 restoration contract](UPGRADE_RESTORATION.md). Local validation is complete: 112 automated tests, 29 actual-EXE checks and two byte-identical clean builds. Exact 1.0 content also passed the maintainer's in-game acceptance. Nexus approval is not established.

## Download the installer and content

[Current download page: KKS Content 1.0.1 and Installer 1.1.0](https://github.com/KitsKillerSystem/kks-installer/releases/tag/v1.0.1)

- [KKS Installer 1.1.0](https://github.com/KitsKillerSystem/kks-installer/releases/download/v1.0.1/KKS_Installer_1.1.0.zip): reusable Windows application; extract this ZIP and run KKSInstaller.exe.
- [KKS Content 1.0.1](https://github.com/KitsKillerSystem/kks-installer/releases/download/v1.0.1/KKS_1.0.1_Payload_Steam_EN_25636769_r1.zip): complete signed font/configuration/strings package; keep this ZIP intact.

1. Download both ZIPs if you do not already have installer 1.1.0.
2. Extract only the installer ZIP, close Fallout 76, and open KKSInstaller.exe.
3. Select the game folder and the intact content ZIP, then choose Install when the compatibility check succeeds.

**Supported game version for content 1.0.1:** Steam, English, Slasher hotfix build **25636769**. No artwork, strings, font configuration or installer code changed in this compatibility release. See [package verification and update notes](review/content-1.0.1/README.md).

If Bethesda updated the game while KKS was installed, complete Steam's Verify integrity of game files before selecting the new compatible package. The installer requires the current vanilla archives before retiring old KKS overrides across game builds; it will not restore old archives over an unverified new build. Keep the game's **.kks-manager** and any **.kks-installer-1.0.0** records and backups.

GitHub's automatic Source code downloads are for developers; use the two named ZIP assets above. Python and xTranslator are not needed. The [original bundled 1.0.0 release](https://github.com/KitsKillerSystem/kks-installer/releases/tag/v1.0.0) is preserved for history and its older supported game build.

## About KKS

KKS 1.0.0 provides a standalone Fallout 76 installer. This repository also contains its source for review of the released Windows executable.

**Mod page:** https://www.nexusmods.com/fallout76/mods/4301

KKS installs its reviewed English font, font configuration and localization payloads. The GUI offers Install, Repair and Restore vanilla, with recovery for interrupted operations. End users do not need Python or xTranslator.

## For Nexus reviewers

- [Build instructions](BUILD.md): build the current independent executable. A game installation is not required to build or run the fixture tests. Use the `v1.0.0` release source for the original bundled EXE.
- [Current implementation](INDEPENDENT_INSTALLER.md) and [original reviewer notes](REVIEWER_NOTES.md): entry points, operating-system interactions, file changes and safety checks.
- [Release fingerprints](RELEASE_SHA256SUMS.txt): identify the original uploaded ZIP, its executable and pinned release manifest.
- [Original source snapshot](SOURCE_SNAPSHOT.json): historical SHA-256 inventory of the sealed 1.0.0 review snapshot; it does not describe this development branch's changed runtime code.
- [Restoration contract](UPGRADE_RESTORATION.md): persistent state and requirements for future version compatibility.

The installer is an offline, on-disk asset patcher. It requires the game to be closed; it does not inject code into a running process. Each signed content package specifies exact supported Steam English game fingerprints. Unknown game fingerprints or conflicting target files stop installation/restoration.

The original 1.0.0 payload passed the author's final in-game QA. Publication of this source is for transparency and review; it does not imply Nexus has approved the quarantined upload.

## Repository contents

`source/kks_installer/` and `source/launcher.py` contain application code. `source/tests/` contains 112 fixture tests, including all 59 original tests. `source/release/` retains the exact 1.0.0 manifest and five inputs for provenance and package creation; **the current build does not embed them**. `source/build_content.py` is a publisher tool, excluded from the runtime. `source/build.ps1` and `source/requirements-build.txt` provide the build entry point and pinned dependencies.

The source tree omits the original EXE, Bethesda game archives/executable/ESM, local backups, signing private keys, private workstation logs and optional font-authoring/history tools. They are not required to build the installer. The original EXE is available in the complete installer ZIP linked above. The broader authoring/codex bundle remains a separate release artifact. Frozen 1.0.0 evidence and payload bytes remain unchanged.
