# KKS — Kit's Killer System

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

- [Build instructions](BUILD.md): build the executable from the included Python source and exact release inputs. A game installation is not required to build or run the fixture tests.
- [Reviewer notes](REVIEWER_NOTES.md): entry points, operating-system interactions, file changes and safety checks.
- [Release fingerprints](RELEASE_SHA256SUMS.txt): identify the original uploaded ZIP, its executable and pinned release manifest.
- [Source snapshot](SOURCE_SNAPSHOT.json): SHA-256 of every copied runtime source, test, build file and payload. These files are unchanged from the sealed 1.0.0 developer bundle.
- [Restoration contract](UPGRADE_RESTORATION.md): persistent state and requirements for future version compatibility.

The installer is an offline, on-disk asset patcher. It requires the game to be closed; it does not inject code into a running process. It supports only the pinned Steam English Slasher build 25258219. Unknown game fingerprints or conflicting target files stop installation/restoration.

The original 1.0.0 payload passed the author's final in-game QA. Publication of this source is for transparency and review; it does not imply Nexus has approved the quarantined upload.

## Repository contents

`source/kks_installer/` and `source/launcher.py` contain all application code. `source/tests/` contains the 59 fixture tests. `source/release/` contains the exact manifest and five inputs embedded in the executable. `source/build.ps1` and `source/requirements-build.txt` provide the build entry point and pinned PyInstaller version.

The source tree omits the original EXE, Bethesda game archives/executable/ESM, local backups, private workstation logs and optional font-authoring/history tools. They are not required to build the installer. The original EXE is available in the complete installer ZIP linked above. The broader authoring/codex bundle remains a separate release artifact. Root documentation is prepared for this review; copied application code and payloads remain unchanged.
