# KKS — Kit's Killer System

## Independent installer candidate — unreleased

This branch develops **installer application 1.1.0** with separately signed, complete content ZIPs. Its first package contains the **unchanged KKS 1.0.0** font/configuration/strings. Application and content versions are independent. The original public release linked below is still the bundled 1.0.0 installer; it has not been replaced.

The candidate accepts a ZIP through Choose package, by dropping it on the window, or by dropping it onto the EXE. It verifies the publisher signature, every file, the game baseline and saved installation before enabling installation. Complete packages permit direct jumps over intermediate releases. Repair uses the verified local cache; Restore uses authenticated descriptors and original backups without needing a download or the old EXE.

See [the implementation and package contract](INDEPENDENT_INSTALLER.md), [current build instructions](BUILD.md), and [the original 1.0 restoration contract](UPGRADE_RESTORATION.md). The candidate is for local validation until separately accepted and published. Nexus approval is not established.

## Download the full mod + installer

### [CLICK HERE TO DOWNLOAD KKS 1.0.0 (ZIP, 20.5 MB)](https://github.com/KitsKillerSystem/kks-installer/releases/download/v1.0.0/KKS_1.0.0_Installer.zip)

**This is the complete Windows installer with the KKS mod included.** No Python, xTranslator, or separate mod download is needed.

1. Download **KKS_1.0.0_Installer.zip** using the link above.
2. Right-click the ZIP, choose **Extract All**, then open the extracted folder and run **KKSInstaller.exe**.
3. Close Fallout 76, check the game location, and choose **Install KKS**.

**Supported game version:** Steam, English, Slasher build **25258219**. The installer checks compatibility before making changes. If you have a prerelease installed, use its **Restore vanilla** first. Keep the **.kks-installer-1.0.0** folder in your game directory for repair and restoration.

[Open the download page and release notes](https://github.com/KitsKillerSystem/kks-installer/releases/latest)

On the release page, choose **KKS_1.0.0_Installer.zip**. GitHub's **Source code (zip)** and **Source code (tar.gz)** downloads do not include the ready-to-run installer. The checksum file is optional.

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

The installer is an offline, on-disk asset patcher. It requires the game to be closed; it does not inject code into a running process. It supports only the pinned Steam English Slasher build 25258219. Unknown game fingerprints or conflicting target files stop installation/restoration.

The original 1.0.0 payload passed the author's final in-game QA. Publication of this source is for transparency and review; it does not imply Nexus has approved the quarantined upload.

## Repository contents

`source/kks_installer/` and `source/launcher.py` contain application code. `source/tests/` contains 110 fixture tests, including all 59 original tests. `source/release/` retains the exact 1.0.0 manifest and five inputs for provenance and package creation; **the current build does not embed them**. `source/build_content.py` is a publisher tool, excluded from the runtime. `source/build.ps1` and `source/requirements-build.txt` provide the build entry point and pinned dependencies.

The source tree omits the original EXE, Bethesda game archives/executable/ESM, local backups, signing private keys, private workstation logs and optional font-authoring/history tools. They are not required to build the installer. The original EXE is available in the complete installer ZIP linked above. The broader authoring/codex bundle remains a separate release artifact. Frozen 1.0.0 evidence and payload bytes remain unchanged.
