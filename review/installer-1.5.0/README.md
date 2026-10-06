# Installer 1.5.0 build and acceptance evidence

The exact accepted executable was built from **85b6d10ecba99cfdb624900d6acfd08bff7c14d5**
(`installer-v1.5.0`). Later release commits change documentation/evidence only.
Use that build commit and [BUILD.md](../../BUILD.md) for reproduction.

The clean build passed **182 automated tests**. [build/](build/) contains the
source/environment/hash receipt and complete test/build logs. Local workstation
paths are replaced with `<USERPROFILE>`; original and published log hashes are
recorded separately. This release records one clean build, not a two-build identity
claim. Private originals and accepted artifacts remain preserved.

[TEST_RESULTS.json](TEST_RESULTS.json) records **28 compiled-executable checks**:
signature validation, read-only Check, upgrade from E001 installed by Installer
1.4.0, all four equipment/perk combinations, saved-choice Repair, damaged derived
caches, cache-free Restore, exact original loose-file absence, and a forced
process-tree termination after a real archive write followed by recovery.
The disposable game copy was restored; those checks did not modify the live game.

The maintainer subsequently passed all six reported in-game checks: Restore
Vanilla, Full KKS, both hybrid configurations, profile-aware Repair, and return to
Full KKS. No regressions were observed; the modular architecture is owner-validated.
See [content acceptance](../content-1.1.1/ACCEPTANCE.json).

The published EXE is byte-identical to that accepted build. Its historical preview
display label remains unchanged. The public content is English; UI language
choices and pre-existing DE/RU/FR package support do not certify unpublished content.
These are finite development checks and maintainer acceptance, not independent
security certification, Windows Authenticode signing or Nexus approval.
