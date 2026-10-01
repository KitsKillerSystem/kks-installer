# Build the independent installer

See [the root build instructions](../BUILD.md) for the locked toolchain, clean-source build, tests, provenance receipt and reproduction limits.

Run `build.ps1` with the chosen Python executable and two new output/work directories. The developer-only `review_build.py` runs all tests before PyInstaller and records the exact source revision. No content payload or private key is bundled.
