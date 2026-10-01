"""Developer-only clean-source build and provenance receipt; never bundled."""

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tkinter


def sha256(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument("--build-directory", required=True, type=Path)
    args = parser.parse_args()
    source = Path(__file__).resolve().parent
    repository = source.parent

    def git(*arguments):
        return subprocess.check_output(["git", "-C", str(repository), *arguments]).decode().strip()

    if os.name != "nt" or platform.machine().lower() not in ("amd64", "x86_64"):
        raise SystemExit("Build on Windows x64 with Python 3.12.14 and Tk/Tcl.")
    if platform.python_version() != "3.12.14":
        raise SystemExit("This release toolchain requires Python 3.12.14.")
    if git("status", "--porcelain", "--untracked-files=all"):
        raise SystemExit("Commit source changes and use a clean checkout before building.")
    commit = git("rev-parse", "HEAD")
    epoch = git("show", "-s", "--format=%ct", "HEAD")
    for line in (source / "requirements-build.txt").read_text().splitlines():
        if line and not line.startswith("#"):
            name, expected = line.split()[0].split("==")
            if importlib.metadata.version(name) != expected:
                raise SystemExit("Install the locked build requirements first: " + name)

    destination = args.destination.resolve()
    build = args.build_directory.resolve()
    # A fresh directory prevents a failed build from looking like an earlier success.
    if destination.exists() or build.exists():
        raise SystemExit("Choose new destination and build directories; neither may exist.")
    destination.mkdir(parents=True)
    build.mkdir(parents=True)
    environment = os.environ.copy()
    environment.update(PYTHONHASHSEED="1", SOURCE_DATE_EPOCH=epoch, PYTHONUTF8="1")
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    source_files = {name: sha256(repository / name) for name in git("ls-files").splitlines()}
    build_command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--noupx",
        "--onefile",
        "--windowed",
        "--name",
        "KKSInstaller",
        "--distpath",
        str(destination),
        "--workpath",
        str(build / "pyinstaller"),
        "--specpath",
        str(build),
        "launcher.py",
    ]
    for name, command in (
        ("tests.log", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]),
        ("build.log", build_command),
    ):
        print("Running " + name, flush=True)
        with (destination / name).open("wb") as log:
            subprocess.run(
                command,
                cwd=source,
                env=environment,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=True,
            )
    if git("rev-parse", "HEAD") != commit or git("status", "--porcelain", "--untracked-files=all"):
        raise SystemExit("Source changed during build; output is not accepted.")
    if any(sha256(repository / name) != digest for name, digest in source_files.items()):
        raise SystemExit("Source bytes changed during build; output is not accepted.")
    executable = destination / "KKSInstaller.exe"
    receipt = {
        "source_commit": commit,
        "source_tree": git("rev-parse", "HEAD^{tree}"),
        "source_files_sha256": source_files,
        "python": sys.version,
        "python_executable": sys.executable,
        "python_base": sys.base_prefix,
        "windows": platform.platform(),
        "tcl_patchlevel": tkinter.Tcl().eval("info patchlevel"),
        "installed_distributions": {
            dist.metadata["Name"]: dist.version for dist in importlib.metadata.distributions()
        },
        "environment": {
            name: environment[name]
            for name in ("PYTHONHASHSEED", "SOURCE_DATE_EPOCH", "PYTHONUTF8")
        },
        "build_command": build_command,
        "exe_sha256": sha256(executable),
        "exe_size": executable.stat().st_size,
        "tests_sha256": sha256(destination / "tests.log"),
        "build_log_sha256": sha256(destination / "build.log"),
    }
    (destination / "build-receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf8"
    )
    print("Built " + commit + ": " + receipt["exe_sha256"], flush=True)


if __name__ == "__main__":
    main()
