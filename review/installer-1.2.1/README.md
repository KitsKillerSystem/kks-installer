# Installer 1.2.1 build and test evidence

The released executable was built from
**3d65c7df0ca28b638d416dbab0392155022a6d9b** (`installer-v1.2.1`).
Later content-release commits update documentation/evidence only. Check out the
exact build commit when reproducing the binary using [BUILD.md](../../BUILD.md).

Both clean builds passed all **138 automated tests** and produced byte-identical
executables. `build-a/` and `build-b/` contain their source/environment/hash receipts
and complete test/build logs. Workstation paths are replaced with `<USERPROFILE>`;
each receipt distinguishes original and published log hashes. The private original
receipts remain preserved; no private key, game backup or live receipt is included.

[TEST_RESULTS.json](TEST_RESULTS.json) records ten actual executable checks for
the new profile, six further checks for the final content package, and packaged
window-drop / ZIP-at-launch checks. The original profile tests exercise direct
five-to-six-target upgrade, repair, restore and fresh reinstall. Final content
tests confirm direct upgrade, cached repair and restoration. Disposable game
copies were restored and the live installation was not changed by these tests.

Window drops were exercised with Unicode and spaces in the filename, including
a repeated drop. The app remained alive, reverified the package and closed
normally. Both drop and ZIP-at-launch views displayed six verified files and
Ready to install; package selection did not install content automatically.

The maintainer subsequently accepted the content's checkmark and sorting in game.
This is finite developer testing and owner acceptance, not independent security
certification, Authenticode signing or Nexus approval. Historical 1.1.0 evidence
and the older published executable remain unchanged.
