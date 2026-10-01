# KKS Content 1.0.1 - Steam English compatibility update

Content **1.0.1 revision 1**, release sequence **2**, supports Steam English
Slasher hotfix build **25636769**. It uses the unchanged **installer 1.1.0**.
All five font/configuration/strings files and all five expected installed target
hashes are identical to released KKS 1.0. This is a compatibility release, not
the planned content 1.1 audit or artwork update.

## Downloads and fingerprints

[GitHub release and both downloads](https://github.com/KitsKillerSystem/kks-installer/releases/tag/v1.0.1)

- Content ZIP: `KKS_1.0.1_Payload_Steam_EN_25636769_r1.zip` (8,870,558 bytes).
- Content ZIP SHA-256: `90681dd798e0e5542d88185b70049963a5854485c404ae8047509b56297b7902`.
- Signed manifest SHA-256: `3eadd1098060e5b4e427808aa5147627a7a01812bbac1888adbd6b72cc5ae97d`.
- Unchanged installer ZIP SHA-256: `7be53528ee55c9b1c0ea85a60d26f648432b65ee093c7206f6b834cbb2487c62`.
- Unchanged KKSInstaller.exe SHA-256: `4e79031ef37c83dc730ff49de46cdfb21d8b326b58ba7a8e0fdb259f96baf17d`.
- Exact executable source: `5c6eadf80ebcec84b62a8c5bec71f7679d9f3004`.
- Signing key ID: `kks-release-2026-10`; no trust-key change.

The new manifest changes content version/sequence, certification time/report,
game build label/baseline ID, and Fallout76.exe hash/size. ESM, localization
archive, mod payloads, vanilla target hashes and generated output hashes are
unchanged. The publisher's current tool retains `qa.status: candidate` in the
signed descriptor; the completed automated acceptance is recorded separately
below. No new gameplay session or Nexus approval is claimed.

## Validation

**23 package-specific checks passed** using the exact existing EXE on disposable
copies of real files. See [ACCEPTANCE.json](ACCEPTANCE.json).

- The compiled trusted key accepts the new signature; an edited manifest fails.
- Current game plus new package reports ready; old package remains refused.
- Fresh installation produces the exact frozen 1.0 mod outputs.
- Cached repair succeeds, and restoration works with cached payloads removed.
- Same-sequence reinstall after restoration succeeds.
- Actual old-build 1.0 installation transitions directly to the new certified
  baseline after Steam-equivalent archive verification, retaining historical
  backups and retiring the previous owner. No new EXE is needed.
- Changed executable plus still-modified archives is refused without mutation;
  Steam verification is required before game-baseline reconciliation.
- Fresh installation restores original loose-file absence. Across the game
  baseline transition, an existing ILSTRINGS table already equal to current
  vanilla is preserved and restored as part of the new baseline. Independent
  extraction from the current localization archive confirms those bytes. The
  initial harness incorrectly expected this vanilla table to be absent; that
  expectation was corrected without changing the application or package.
- Final read-only checks report ready on both disposable copies and the owner's
  restored live game. Live game files and INI settings were not changed during
  package certification/testing. The owner will perform the live reinstall.

The existing application evidence remains [112 fixture tests, 29 prior real-EXE
checks, and two identical clean builds](../installer-1.1.0/README.md). Those
unchanged-code checks were not rerun for this data-only package release.

## Installing and updating

Keep installer 1.1.0. Select the intact 1.0.1 content ZIP inside it; extract only
the installer download. Complete packages need no intermediate releases.

If Bethesda updated the game while KKS was installed, close the game and first
use Steam's Verify integrity of game files. Keep .kks-manager and any legacy
restoration folders. Then select this compatible package. The app verifies the
new vanilla archives, retires recognized old modified string overrides, retains
existing current-vanilla tables and installs the complete new package. It does
not apply old archive backups to an unverified new game build.

The previously uploaded installer ZIP remains exactly the same. Nexus needs the
new content ZIP for this build; old content 1.0.0 targets build 25258219. Every
upload remains subject to Nexus review/scanning policies.
