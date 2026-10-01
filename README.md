# KKS — Kit's Killer System

## Download the installer and content

[Current download page: KKS Content 1.0.1 and Installer 1.1.0](https://github.com/KitsKillerSystem/kks-installer/releases/tag/v1.0.1)

- [KKS Installer 1.1.0](https://github.com/KitsKillerSystem/kks-installer/releases/download/v1.0.1/KKS_Installer_1.1.0.zip): reusable Windows application; extract this ZIP and run KKSInstaller.exe.
- [KKS Content 1.0.1](https://github.com/KitsKillerSystem/kks-installer/releases/download/v1.0.1/KKS_1.0.1_Payload_Steam_EN_25636769_r1.zip): complete signed font/configuration/strings package; keep this ZIP intact.

1. Download both ZIPs if you do not already have installer 1.1.0.
2. Extract only the installer ZIP, close Fallout 76, and open KKSInstaller.exe.
3. Select the game folder and the intact content ZIP, then choose Install when the compatibility check succeeds.

**Supported game version for content 1.0.1:** Steam, English, Slasher hotfix build **25636769**. No artwork, strings, font configuration or installer code changed in this compatibility release. See [package verification and update notes](https://github.com/KitsKillerSystem/kks-installer/blob/release/review-hardening/review/content-1.0.1/README.md).

If Bethesda updated the game while KKS was installed, complete Steam's Verify integrity of game files before selecting the new compatible package. The installer requires the current vanilla archives before retiring old KKS overrides across game builds; it will not restore old archives over an unverified new build. Keep the game's **.kks-manager** and any **.kks-installer-1.0.0** records and backups.

GitHub's automatic Source code downloads are for developers; use the two named ZIP assets above. Python and xTranslator are not needed. The [original bundled 1.0.0 release](https://github.com/KitsKillerSystem/kks-installer/releases/tag/v1.0.0) is preserved for history and its older supported game build.

## Historical v1.0.0 source and review notes

The default branch retains the original bundled installer source. The current independent installer source and review evidence are on [release/review-hardening](https://github.com/KitsKillerSystem/kks-installer/tree/release/review-hardening). The following source notes describe the historical 1.0.0 release; use the current downloads above for Steam build 25636769.

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
