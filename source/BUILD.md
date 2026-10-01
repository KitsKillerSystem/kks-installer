# Building the independent installer

Follow [the repository build instructions](../BUILD.md). They cover prerequisites, tests, the existing build script and its equivalent explicit packaging command.

The current app excludes all content payloads. `release/` retains the unchanged 1.0.0 inputs for provenance and publisher package creation. It is not included in the EXE. The original bundled release remains available from the `v1.0.0` snapshot.
