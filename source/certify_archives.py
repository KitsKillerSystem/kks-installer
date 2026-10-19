"""Publisher-only native archive catalogue generator; contains no signing keys.

Input must be an authenticated content ZIP and its exact certified native files.
Review and commit the generated metadata with the installer; no game bytes ship.
"""
import argparse
import json
from pathlib import Path
import tempfile

from kks_installer.ba2 import BA2, hash_file
from kks_installer.engine import demand, digest
from kks_installer.packages import import_package, LOCALIZATION
from kks_installer._application import CONTENT_LANGUAGES


def certificate(path, target):
    demand(hash_file(path) == target["vanilla_sha256"], "Certification needs the exact native archive")
    archive = BA2(path)
    members = {e.name: {"sha256": digest(archive.extract(e.name)),
               "metadata": [e.raw[0], e.raw[1].hex(), e.raw[2], e.raw[3], e.raw[7]]}
               for e in archive.entries}
    # Common locale profiles own these resources. Everything else can provide
    # native compatibility evidence; at least one must remain identifiable.
    owned = {f"interface/fontconfig_{lang}.txt" for lang in CONTENT_LANGUAGES}
    owned |= {a["name"] for a in target["assets"]}
    anchors = sorted(set(members) - owned)
    return {"path": target["path"], "members": members, "anchors": anchors}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game", type=Path, required=True)
    parser.add_argument("--package", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = {}
    for package in args.package:
        with tempfile.TemporaryDirectory() as cache:
            release = import_package(package, cache)
            for identity in release.data["identity"]:
                demand(hash_file(args.game / identity["path"]) == identity["sha256"], "Wrong certification game build")
            for target in release.targets:
                if target["kind"] == "archive" and target["path"] != LOCALIZATION:
                    result[target["vanilla_sha256"]] = certificate(args.game / target["path"], target)
    args.output.write_text('"""Native archive metadata certified from signed packages; no game payloads."""\n\n'
                          + "CATALOG = " + json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf8")


if __name__ == "__main__":
    main()
