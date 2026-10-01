"""Authenticated, bounded seven-file content packages; no executable hooks."""

from pathlib import Path
import base64
import hashlib
import json
import os
import re
import stat
import struct
import uuid
import zipfile

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from ._application import APP_VERSION, INSTALLER_API, PROFILE, WRITER, CAPABILITIES, TRUSTED_KEYS
from .engine import demand, digest, is_digest, durable_bytes, sync_directory
from .ba2 import hash_file
from .platforms import SafetyError, safe_path

DOMAIN = b"KKS-CONTENT-MANIFEST-v1\0"
MAX_MANIFEST = 1024 * 1024
MAX_SIGNATURE = 16 * 1024
MAX_ASSET = 256 * 1024 * 1024
MAX_PACKAGE = 512 * 1024 * 1024
MAX_FILE = 32 * 1024 * 1024 * 1024
FONT = "Data/SeventySix - Interface_en.ba2"
CONFIG = "Data/SeventySix - Interface.ba2"
ARCHIVES = {FONT: "interface/fonts_en.swf", CONFIG: "interface/fontconfig_en.txt"}
STRINGS = {f"Data/strings/seventysix_en.{ext}" for ext in ("strings", "dlstrings", "ilstrings")}
IDENTITIES = {"Fallout76.exe", "Data/SeventySix.esm", "Data/SeventySix - Localization.ba2"}
PAYLOADS = {"payload/" + p for p in ARCHIVES.values()} | {"payload/" + p[5:] for p in STRINGS}
FILES = PAYLOADS | {"manifest.json", "manifest.sig.json"}
DIRECTORIES = {"payload/", "payload/interface/", "payload/strings/"}


def strict_json(raw, limit=MAX_MANIFEST):
    demand(len(raw) <= limit, "JSON data exceeds the supported size")

    def pairs(items):
        result = {}
        for key, value in items:
            demand(key not in result, "Duplicate JSON field")
            result[key] = value
        return result

    def depth(value, level=0):
        demand(level <= 20, "JSON nesting exceeds the supported depth")
        if isinstance(value, dict):
            for x in value.values():
                depth(x, level + 1)
        elif isinstance(value, list):
            demand(len(value) <= 10000, "JSON array is too large")
            for x in value:
                depth(x, level + 1)

    def reject_constant(value):
        raise SafetyError("Invalid JSON number")

    try:
        result = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=pairs,
            parse_constant=reject_constant,
        )
        depth(result)
        return result
    except (UnicodeError, ValueError, RecursionError) as e:
        raise SafetyError("Invalid UTF-8 JSON data") from e


def fields(value, expected):
    demand(
        type(value) is dict and set(value) == set(expected.split()),
        "Unexpected or missing package/state fields",
    )


def integer(value, lower=0, upper=MAX_FILE):
    demand(type(value) is int and lower <= value <= upper, "Invalid integer or size")


def plain(value, limit=180):
    demand(
        type(value) is str and 0 < len(value) <= limit and all(32 <= ord(c) < 127 for c in value),
        "Invalid display text",
    )


def version(value):
    demand(
        type(value) is str
        and re.fullmatch(r"(0|[1-9][0-9]{0,5})\.(0|[1-9][0-9]{0,5})\.(0|[1-9][0-9]{0,5})", value),
        "Expected a numeric major.minor.patch version",
    )
    return tuple(map(int, value.split(".")))


def hash_size(value):
    fields(value, "sha256 size")
    demand(is_digest(value["sha256"]), "Invalid SHA-256 digest")
    integer(value["size"])


def validate_manifest(m):
    fields(
        m,
        "schema package_type product channel content_version package_revision release_sequence created_utc installer_api minimum_installer_version required_capabilities profile game files targets qa",
    )
    integer(m["schema"], 1, 1)
    integer(m["installer_api"], INSTALLER_API, INSTALLER_API)
    demand(
        (m["package_type"], m["product"], m["channel"], m["profile"])
        == ("kks-content", "KKS", "release", PROFILE),
        "Unsupported product, channel or asset profile",
    )
    version(m["content_version"])
    demand(
        version(m["minimum_installer_version"]) <= version(APP_VERSION),
        "This content package needs a newer KKS Installer",
    )
    integer(m["package_revision"], 1, 2**31 - 1)
    integer(m["release_sequence"], 1, 2**53 - 1)
    demand(
        m["required_capabilities"] == CAPABILITIES,
        "Unsupported archive writer or installer capability",
    )
    demand(
        type(m["created_utc"]) is str
        and re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", m["created_utc"]),
        "Invalid package timestamp",
    )
    game = m["game"]
    fields(game, "id platform app_id language build_label baseline_id identity")
    demand(
        (game["id"], game["platform"], game["language"]) == ("fallout76", "steam", "en"),
        "This application supports Fallout 76 Steam English packages only",
    )
    integer(game["app_id"], 1151340, 1151340)
    plain(game["build_label"])
    plain(game["baseline_id"], 100)
    demand(
        type(game["identity"]) is list and len(game["identity"]) == 3,
        "Exactly three game identity files are required",
    )
    for item in game["identity"]:
        fields(item, "path sha256 size")
        hash_size({k: item[k] for k in ("sha256", "size")})
    demand({x["path"] for x in game["identity"]} == IDENTITIES, "Unexpected game identity path")
    demand(
        type(m["files"]) is list and len(m["files"]) == 5, "Exactly five payload files are required"
    )
    payloads = {}
    for f in m["files"]:
        fields(f, "path sha256 size")
        demand(
            f["path"] in PAYLOADS and f["path"] not in payloads,
            "Unexpected or duplicate payload path",
        )
        hash_size({k: f[k] for k in ("sha256", "size")})
        integer(f["size"], 1, MAX_ASSET)
        payloads[f["path"]] = f
    demand(
        sum(f["size"] for f in payloads.values()) <= MAX_PACKAGE,
        "Payload exceeds the supported total size",
    )
    demand(
        type(m["targets"]) is list and len(m["targets"]) == 5,
        "Exactly five game targets are required",
    )
    seen = set()
    for t in m["targets"]:
        demand(
            type(t) is dict and type(t.get("path")) is str and t["path"] not in seen,
            "Duplicate or invalid target",
        )
        seen.add(t["path"])
        if t["path"] in ARCHIVES:
            fields(
                t,
                "path kind version type writer vanilla_sha256 vanilla_size after_sha256 after_size assets",
            )
            integer(t["version"], 1, 1)
            demand(
                (t["kind"], t["type"], t["writer"]) == ("archive", "GNRL", WRITER),
                "Unsupported archive operation",
            )
            demand(
                type(t["assets"]) is list and len(t["assets"]) == 1,
                "Exactly one permitted archive member is required",
            )
            a = t["assets"][0]
            fields(a, "name payload vanilla_sha256 vanilla_size sha256 size")
            demand(
                a["name"] == ARCHIVES[t["path"]] and a["payload"] == "payload/" + a["name"],
                "Forbidden archive member or payload",
            )
            demand(is_digest(a["vanilla_sha256"]), "Invalid original member digest")
            integer(a["vanilla_size"], 1, MAX_ASSET)
            demand(
                {k: a[k] for k in ("sha256", "size")}
                == {k: payloads[a["payload"]][k] for k in ("sha256", "size")},
                "Archive member does not match payload",
            )
        else:
            fields(t, "path kind payload vanilla_sha256 vanilla_size after_sha256 after_size")
            demand(
                t["path"] in STRINGS
                and t["kind"] == "loose"
                and t["payload"] == "payload/" + t["path"][5:],
                "Forbidden loose-file operation",
            )
            demand(
                t["after_sha256"] == payloads[t["payload"]]["sha256"]
                and t["after_size"] == payloads[t["payload"]]["size"],
                "Loose target does not match payload",
            )
        demand(
            is_digest(t["vanilla_sha256"]) and is_digest(t["after_sha256"]), "Invalid target digest"
        )
        integer(t["vanilla_size"], 1)
        integer(t["after_size"], 1)
    demand(seen == set(ARCHIVES) | STRINGS, "Unexpected target set")
    fields(m["qa"], "status report_id")
    demand(m["qa"]["status"] in ("candidate", "approved"), "Invalid QA status")
    plain(m["qa"]["report_id"])
    return m


class SignedRelease:
    def __init__(self, folder, raw, signature, keys=None):
        self.folder = Path(folder)
        envelope = strict_json(signature, MAX_SIGNATURE)
        fields(envelope, "schema algorithm key_id signature")
        integer(envelope["schema"], 1, 1)
        demand(envelope["algorithm"] == "Ed25519", "Unsupported signature algorithm")
        plain(envelope["key_id"], 100)
        keys = TRUSTED_KEYS if keys is None else keys
        demand(envelope["key_id"] in keys, "This package is not signed by a trusted KKS publisher")
        demand(type(envelope["signature"]) is str, "Invalid signature encoding")
        demand(len(raw) <= MAX_MANIFEST, "Manifest is too large")
        try:
            sig = base64.b64decode(envelope["signature"], validate=True)
            demand(len(sig) == 64, "Invalid signature length")
            Ed25519PublicKey.from_public_bytes(bytes.fromhex(keys[envelope["key_id"]])).verify(
                sig, DOMAIN + raw
            )
        except (ValueError, InvalidSignature) as e:
            raise SafetyError("The KKS package signature is invalid") from e
        self.manifest = validate_manifest(strict_json(raw))
        self.raw = raw
        self.signature = signature
        self.manifest_digest = digest(raw)
        self.name = "KKS " + self.manifest["content_version"]
        self.targets = self.manifest["targets"]
        self.by_path = {t["path"]: t for t in self.targets}
        self.files = {f["path"]: f for f in self.manifest["files"]}
        self.data = {
            "schema": 1,
            "release": self.name,
            "supported_build": self.manifest["game"]["build_label"],
            "identity": self.manifest["game"]["identity"],
            "targets": self.targets,
        }

    @classmethod
    def load(cls, folder, keys=None):
        folder = Path(folder)
        raw = bounded_file(safe_path(folder, "manifest.json", regular=True), MAX_MANIFEST)
        sig = bounded_file(safe_path(folder, "manifest.sig.json", regular=True), MAX_SIGNATURE)
        return cls(folder, raw, sig, keys)

    def payload(self, relative, expected):
        demand(
            relative in self.files and self.files[relative]["sha256"] == expected,
            "Unexpected payload request",
        )
        p = safe_path(self.folder, relative, regular=True)
        demand(
            p.is_file()
            and p.stat().st_size == self.files[relative]["size"]
            and hash_file(p) == expected,
            "A cached payload is missing or damaged. Select the same content ZIP again: "
            + relative,
        )
        return p

    def verify_payloads(self):
        for f in self.files.values():
            self.payload(f["path"], f["sha256"])


def bounded_file(path, limit):
    with Path(path).open("rb") as f:
        data = f.read(limit + 1)
    demand(len(data) <= limit, "Saved data exceeds the supported size")
    return data


def _container(file):
    file.seek(0, 2)
    size = file.tell()
    demand(22 <= size <= MAX_PACKAGE, "Content ZIP is incomplete or exceeds the supported size")
    file.seek(0)
    demand(file.read(4) == b"PK\x03\x04", "Self-extracting or prefixed ZIP files are not supported")
    # Small fixed entry count: bound the central directory before ZipFile allocates it.
    file.seek(size - 22)
    eocd = file.read(22)
    sig, disk, cd_disk, disk_n, n, cd_size, cd_offset, comment = struct.unpack("<4s4H2IH", eocd)
    demand(
        sig == b"PK\x05\x06"
        and disk == cd_disk == 0
        and disk_n == n
        and 7 <= n <= 10
        and comment == 0,
        "Unsupported, multipart, ZIP64, or malformed ZIP directory",
    )
    demand(
        cd_size <= 65536 and cd_offset + cd_size == size - 22,
        "Invalid ZIP directory bounds or trailing data",
    )
    z = zipfile.ZipFile(file)
    infos = z.infolist()
    demand(len(infos) == n, "ZIP directory count mismatch")
    seen = set()
    total = 0
    for i in infos:
        name = i.filename
        demand(
            name == i.orig_filename and name not in seen and name in FILES | DIRECTORIES,
            "Unexpected, duplicate or unsafe ZIP path",
        )
        seen.add(name)
        demand(
            i.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
            and not (i.flag_bits & ~0x808),
            "Unsupported ZIP flags or compression",
        )
        demand(i.volume == 0 and not i.extra and not i.comment, "Unsupported ZIP metadata")
        mode = i.external_attr >> 16
        demand(
            not stat.S_IFMT(mode)
            or stat.S_ISREG(mode)
            or (name in DIRECTORIES and stat.S_ISDIR(mode)),
            "Links and special files are forbidden",
        )
        if name == "manifest.json":
            limit = MAX_MANIFEST
        elif name == "manifest.sig.json":
            limit = MAX_SIGNATURE
        elif name in DIRECTORIES:
            limit = 0
        else:
            limit = MAX_ASSET
        demand(
            i.file_size <= limit and i.compress_size <= MAX_PACKAGE,
            "ZIP entry exceeds the supported size",
        )
        total += i.file_size
    demand(
        FILES <= seen and total <= MAX_PACKAGE + MAX_MANIFEST + MAX_SIGNATURE,
        "Incomplete or oversized content package",
    )
    # Reject hidden data/local aliases and central/local size disagreement.
    ordered = sorted(infos, key=lambda i: i.header_offset)
    expected = 0
    for i in ordered:
        demand(i.header_offset == expected, "Overlapping or hidden ZIP entries")
        file.seek(i.header_offset)
        header = file.read(30)
        demand(len(header) == 30, "Truncated local ZIP header")
        h = struct.unpack("<4s5H3I2H", header)
        demand(
            h[0] == b"PK\x03\x04"
            and h[2] == i.flag_bits
            and h[3] == i.compress_type
            and h[10] == 0,
            "Local ZIP header mismatch",
        )
        name_bytes = file.read(h[9])
        demand(name_bytes == i.filename.encode("utf-8"), "Local ZIP filename mismatch")
        end = file.tell() + i.compress_size
        if i.flag_bits & 8:
            file.seek(end)
            descriptor = file.read(16)
            demand(
                len(descriptor) == 16
                and struct.unpack("<4sIII", descriptor)
                == (b"PK\x07\x08", i.CRC, i.compress_size, i.file_size),
                "Invalid ZIP data descriptor",
            )
            end += 16
        else:
            demand(h[6:9] == (i.CRC, i.compress_size, i.file_size), "Local ZIP sizes disagree")
        expected = end
    demand(expected == cd_offset, "Hidden or truncated ZIP content")
    return z


def import_package(path, cache, keys=None):
    """Import into app state only, never the game targets; verify before publication."""
    path = Path(path)
    demand(path.suffix.lower() == ".zip", "Select a complete KKS content ZIP")
    cache = Path(cache)
    stage = safe_path(cache, "import-" + uuid.uuid4().hex)
    stage.mkdir(parents=True)
    try:
        with path.open("rb") as handle:
            with _container(handle) as z:
                raw = z.read("manifest.json")
                sig = z.read("manifest.sig.json")
                release = SignedRelease(stage, raw, sig, keys)
                for f in release.files.values():
                    info = z.getinfo(f["path"])
                    demand(
                        info.file_size == f["size"],
                        "Payload length disagrees with its signed manifest",
                    )
                    p = safe_path(stage, f["path"], regular=True)
                    p.parent.mkdir(parents=True, exist_ok=True)
                    h = hashlib.sha256()
                    count = 0
                    with z.open(info) as src, p.open("xb") as dst:
                        while block := src.read(min(1024 * 1024, f["size"] - count + 1)):
                            count += len(block)
                            demand(
                                count <= f["size"], "Decompressed payload exceeds its signed size"
                            )
                            h.update(block)
                            dst.write(block)
                        dst.flush()
                        os.fsync(dst.fileno())
                    demand(
                        count == f["size"] and h.hexdigest() == f["sha256"],
                        "Payload checksum failed",
                    )
                durable_bytes(stage / "manifest.json", raw)
                durable_bytes(stage / "manifest.sig.json", sig)
        release.verify_payloads()
        destination = safe_path(cache, release.manifest_digest)
        if destination.exists():
            demand(destination.is_dir(), "Invalid package cache destination")
            # A fully verified reimport may repair this exact content-addressed cache,
            # including a corrupted descriptor. It cannot select another release.
            for f in release.files.values():
                target = safe_path(destination, f["path"], regular=True)
                target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(safe_path(stage, f["path"], regular=True), target)
                sync_directory(target.parent)
            durable_bytes(safe_path(destination, "manifest.json", regular=True), raw)
            durable_bytes(safe_path(destination, "manifest.sig.json", regular=True), sig)
        else:
            os.replace(stage, destination)
            sync_directory(cache)
        result = SignedRelease.load(destination, keys)
        result.verify_payloads()
        return result
    except (OSError, zipfile.BadZipFile, RuntimeError, ValueError) as e:
        if isinstance(e, SafetyError):
            raise
        raise SafetyError("Could not verify this content ZIP: " + str(e)) from e
    # Failed staging is retained as untrusted import-* data, never used as a release.
