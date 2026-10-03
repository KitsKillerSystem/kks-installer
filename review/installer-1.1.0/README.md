# Installer 1.1.0 review evidence

Start with [REVIEWER_HANDOFF.md](REVIEWER_HANDOFF.md). The existing binary was built
from **5c6eadf80ebcec84b62a8c5bec71f7679d9f3004**. Check out that exact commit
when reproducing it; later documentation commits are not a new binary build.
Application/runtime/test/build-tool files remain unchanged since that revision.

The later [content 1.0.1 compatibility report](../content-1.0.1/README.md)
records the unchanged EXE with Steam build 25636769. That data-package release
supersedes the initial 25258219 package for updated games; it is not a new EXE.

- TEST_RESULTS.json: all 112 automated methods and 29 actual-EXE check names.
- build-a/ and build-b/: test/build logs and source/environment/hash receipts.
- REPRODUCIBILITY.json: identical outputs from two separate clean checkouts.
- BINARY_SOURCE_VERIFICATION.json: packaged application modules match compiled
  committed source; payload/legacy descriptor parity and PE security metadata.
- RUNTIME_INVENTORY.json: every bundled entry's size/hash; no mod payload.
- FORMATTING_AST_PROOF.json: exact parsed-code equality for the formatting pass.

Workstation paths in public build logs/receipts are replaced with placeholders;
receipt fields distinguish original log hashes from published log hashes.
Private game receipts, INI fingerprints, account paths, recovery locations and
private or encrypted signing keys are excluded. The signing key's backup/recovery
test completed successfully; no signing material is needed by a reviewer.

The original root-level 1.0 test reports and hashes remain historical evidence.
The installer code was developed with substantial Codex assistance under the
maintainer's direction; this evidence documents what was checked rather than
claiming independent security certification or concealing development tooling.
