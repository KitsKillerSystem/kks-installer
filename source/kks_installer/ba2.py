"""Strict Bethesda BA2 v1 GNRL reader and replacement-only writer.

Format/behavior researched against MGuffin/xTranslator TESVT_bsa.pas,
commit 9aa38d60860273401f8bb0dd1557c82a295c41b3. Independent implementation.
Unselected stored payloads and filename-table bytes are copied verbatim.
"""

from dataclasses import dataclass
from pathlib import Path
import hashlib, os, struct, zlib

HEADER = struct.Struct("<4sI4sIQ")
RECORD = struct.Struct("<I4sIIQIII")
CHUNK = 1024 * 1024
MAX_EXTRACT = 256 * 1024 * 1024


class ArchiveError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ArchiveError(message)


def normalize(name):
    value = name.replace("\\", "/").lower()
    require(value and not value.startswith("/") and ":" not in value, "Invalid archive asset path")
    require(all(p not in ("", ".", "..") for p in value.split("/")), "Unsafe archive asset path")
    return value


def read_exact(stream, size):
    data = stream.read(size)
    require(len(data) == size, "Truncated archive")
    return data


def hash_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(CHUNK), b""):
            digest.update(b)
    return digest.hexdigest()


def copy_count(source, destination, count):
    while count:
        data = read_exact(source, min(CHUNK, count))
        destination.write(data)
        count -= len(data)


@dataclass(frozen=True)
class Entry:
    name: str
    raw: tuple

    @property
    def offset(self):
        return self.raw[4]

    @property
    def packed(self):
        return self.raw[5]

    @property
    def size(self):
        return self.raw[6]

    @property
    def stored_size(self):
        return self.packed or self.size


class BA2:
    def __init__(self, path):
        self.path = Path(path)
        self.file_size = self.path.stat().st_size
        with self.path.open("rb") as f:
            magic, version, kind, count, self.names_offset = HEADER.unpack(
                read_exact(f, HEADER.size)
            )
            require(
                (magic, version, kind) == (b"BTDX", 1, b"GNRL"),
                "Only verified BA2 version 1 GNRL archives are supported",
            )
            require(0 < count <= 100000, "Invalid BA2 entry count")
            table_end = HEADER.size + RECORD.size * count
            require(
                table_end <= self.names_offset < self.file_size, "Invalid filename table offset"
            )
            records = [RECORD.unpack(read_exact(f, RECORD.size)) for _ in range(count)]
            f.seek(self.names_offset)
            names = []
            for _ in records:
                length = struct.unpack("<H", read_exact(f, 2))[0]
                require(0 < length <= 4096, "Invalid filename length")
                try:
                    names.append(normalize(read_exact(f, length).decode("utf8")))
                except UnicodeDecodeError as e:
                    raise ArchiveError("Invalid UTF-8 archive filename") from e
            require(len(names) == len(set(names)), "Duplicate normalized archive asset path")
            ranges = []
            for r in records:
                offset, packed, size = r[4:7]
                stored = packed or size
                require(
                    table_end <= offset <= self.names_offset
                    and offset + stored <= self.names_offset,
                    "Payload overlaps metadata or lies outside the archive",
                )
                if stored:
                    ranges.append((offset, offset + stored))
            ranges.sort()
            require(
                all(a[1] <= b[0] for a, b in zip(ranges, ranges[1:])), "Overlapping BA2 payloads"
            )
            self.data_start = min(r[4] for r in records)
            self.entries = [Entry(n, r) for n, r in zip(names, records)]
            self.by_name = {e.name: e for e in self.entries}

    def extract(self, name):
        key = normalize(name)
        require(key in self.by_name, f"Missing expected asset: {key}")
        entry = self.by_name[key]
        require(
            entry.size <= MAX_EXTRACT and entry.stored_size <= MAX_EXTRACT,
            "Target asset exceeds supported size",
        )
        with self.path.open("rb") as f:
            f.seek(entry.offset)
            data = read_exact(f, entry.stored_size)
        if entry.packed:
            try:
                decoder = zlib.decompressobj()
                data = decoder.decompress(data, entry.size + 1)
                require(
                    decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail,
                    "Invalid or oversized zlib stream",
                )
            except zlib.error as e:
                raise ArchiveError("Corrupt compressed BA2 asset") from e
        require(len(data) == entry.size, "Unpacked asset size mismatch")
        return data

    def stored_digest(self, entry):
        digest = hashlib.sha256()
        with self.path.open("rb") as f:
            f.seek(entry.offset)
            remaining = entry.stored_size
            while remaining:
                b = read_exact(f, min(CHUNK, remaining))
                digest.update(b)
                remaining -= len(b)
        return digest.digest()

    def replace_to(self, destination, replacements):
        destination = Path(destination)
        require(
            destination.resolve() != self.path.resolve(),
            "Archive writes require a separate staged file",
        )
        normalized = {normalize(n): data for n, data in replacements.items()}
        require(len(normalized) == len(replacements) and normalized, "Invalid replacement set")
        require(
            set(normalized) <= set(self.by_name),
            "Replacement target is absent; insertion is not supported",
        )
        require(
            all(isinstance(b, bytes) and 0 < len(b) <= MAX_EXTRACT for b in normalized.values()),
            "Invalid replacement bytes",
        )
        with self.path.open("rb") as src, destination.open("xb") as dst:
            copy_count(src, dst, self.data_start)
            updates = []
            for entry in self.entries:
                position = dst.tell()
                if entry.name in normalized:
                    plain = normalized[entry.name]
                    data = zlib.compress(plain, 6) if entry.packed else plain
                    dst.write(data)
                    packed, size = (len(data) if entry.packed else 0), len(plain)
                else:
                    src.seek(entry.offset)
                    copy_count(src, dst, entry.stored_size)
                    packed, size = entry.packed, entry.size
                updates.append((position, packed, size))
            names_position = dst.tell()
            src.seek(self.names_offset)
            copy_count(src, dst, self.file_size - self.names_offset)
            for i, values in enumerate(updates):
                dst.seek(HEADER.size + RECORD.size * i + 16)
                dst.write(struct.pack("<QII", *values))
            dst.seek(16)
            dst.write(struct.pack("<Q", names_position))
            dst.flush()
            os.fsync(dst.fileno())
        self.verify_replacement(destination, normalized)

    def verify_replacement(self, destination, replacements):
        other = BA2(destination)
        require(
            [e.name for e in self.entries] == [e.name for e in other.entries],
            "Archive asset ordering changed",
        )
        with self.path.open("rb") as a, other.path.open("rb") as b:
            a.seek(self.names_offset)
            b.seek(other.names_offset)
            require(a.read() == b.read(), "Filename table or trailing archive data changed")
        for before, after in zip(self.entries, other.entries):
            require(
                before.raw[:4] == after.raw[:4] and before.raw[7] == after.raw[7],
                "Opaque archive record metadata changed",
            )
            require(bool(before.packed) == bool(after.packed), "Asset compression policy changed")
            if before.name in replacements:
                require(
                    other.extract(before.name) == replacements[before.name],
                    "Injected asset validation failed",
                )
            else:
                require(
                    before.raw[5:7] == after.raw[5:7]
                    and self.stored_digest(before) == other.stored_digest(after),
                    "An unrelated stored asset changed",
                )
        return other
