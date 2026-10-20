"""Certified modified-archive admission and installation-specific output proofs.

The package remains immutable. A local projection is accepted only with verified
original/output backups and a replacement-only proof against signed member hashes.
It is not a second content package or a way to expand resource ownership.
"""

from copy import deepcopy
import json

from .ba2 import BA2, hash_file
from .engine import demand, digest, is_digest
from .packages import LOCALIZATION, fields, integer, MAX_ASSET
from .string_tables import read_table
from ._archive_catalog import CATALOG


def inspect_original(path, target):
    """Validate every stream, then certify directory/build evidence for migration."""
    current = hash_file(path)
    if current == target["vanilla_sha256"]:
        if target["kind"] == "archive":
            archive = BA2(path)
            for asset in target["assets"]:
                native = archive.extract(asset["name"])
                demand(digest(native) == asset["vanilla_sha256"] and len(native) == asset["vanilla_size"],
                       "The certified original archive member does not match this package")
        return []
    if target["kind"] == "loose":
        demand(path.stat().st_size <= MAX_ASSET, "Existing string table exceeds supported size")
        extension = target["path"].rsplit(".", 1)[1]
        read_table(path.read_bytes(), "dlstrings" if extension == "ilstrings" else extension)
        return [target["path"]]
    # Localization is also a game-build identity and the native source for
    # optional features. Never infer its compatibility from a modified archive.
    demand(target["path"] != LOCALIZATION,
           "The Localization archive must match the certified game build")
    archive = BA2(path)
    certificate = CATALOG.get(target["vanilla_sha256"])
    demand(certificate is not None,
           "This modified archive has no compatibility certificate in this installer. Use a newer installer or verify game files: " + target["path"])
    demand(certificate["path"] == target["path"], "Archive certificate path mismatch")
    records = certificate["members"]
    demand(set(archive.by_name) == set(records),
           "Unsupported or outdated archive member catalogue: " + target["path"])
    hashes = {}
    for entry in archive.entries:
        native = records[entry.name]
        metadata = [entry.raw[0], entry.raw[1].hex(), entry.raw[2], entry.raw[3], entry.raw[7]]
        demand(metadata == native["metadata"],
               "Unsupported archive record structure: " + entry.name)
        # A valid header alone does not prove that the compressed streams work.
        hashes[entry.name] = digest(archive.extract(entry.name))
        demand(hashes[entry.name] not in native.get("obsolete", []),
               "Outdated archive member: " + entry.name)
    anchors = certificate.get("anchors", [])
    demand(not anchors or any(hashes[n] == records[n]["sha256"] for n in anchors),
           "Cannot establish the archive's supported build; build-identifying resources were changed")
    for asset in target["assets"]:
        demand(records[asset["name"]]["sha256"] == asset["vanilla_sha256"],
               "Archive certificate disagrees with the signed content package")
    return [a["name"] for a in target["assets"] if hashes[a["name"]] != a["vanilla_sha256"]]


def consent_token(root, release, originals):
    data = {"root": str(root), "manifest": release.manifest_digest,
            "naming": release.naming, "perks": release.perks, "originals": originals}
    if release.manifest["schema"] == 4:
        data.update(food=release.food, junk=release.junk)
    return digest(json.dumps(data, sort_keys=True).encode())


class BaselineRelease:
    """Adapt the proven user baseline to the strict existing transaction engine."""
    def __init__(self, certified, context, backup):
        fields(context, "schema manifest root files")
        integer(context["schema"], 1, 1)
        demand(context["manifest"] == certified.manifest_digest, "Baseline content identity changed")
        demand(type(context["files"]) is dict and set(context["files"]) == set(certified.by_path),
               "Invalid baseline context target set")
        self.certified = certified
        self.data = deepcopy(certified.data)
        self.targets = self.data["targets"]
        self.by_path = {t["path"]: t for t in self.targets}
        for target in self.targets:
            record = context["files"][target["path"]]
            fields(record, "before after")
            original, output = record["before"], record["after"]
            demand(is_digest(output) and (is_digest(original) or
                   original is None and target["kind"] == "loose"), "Invalid baseline hashes")
            src = backup(original) if original is not None else None
            if target["kind"] == "loose":
                demand(output == target["after_sha256"], "Unsigned loose output")
                if src is not None:
                    inspect_original(src, target)
            else:
                inspect_original(src, target)
                dst = backup(output)
                source, result = BA2(src), BA2(dst)
                replacements = {}
                for asset in target["assets"]:
                    data = result.extract(asset["name"])
                    demand(digest(data) == asset["sha256"] and len(data) == asset["size"],
                           "Baseline output contains an unsigned resource")
                    replacements[asset["name"]] = data
                    original_data = source.extract(asset["name"])
                    asset["vanilla_sha256"] = digest(original_data)
                    asset["vanilla_size"] = len(original_data)
                source.verify_replacement(dst, replacements)
                target["after_sha256"] = output
                target["after_size"] = dst.stat().st_size
            if original is not None:
                target["vanilla_sha256"] = original
                target["vanilla_size"] = src.stat().st_size

    def __getattr__(self, name):
        return getattr(self.certified, name)
