"""Bounded binary string-table resets; retain unrelated text as exact raw bytes."""

import struct

from .engine import demand

MAX_TABLE = 256 * 1024 * 1024


def read_table(data, extension):
    demand(extension in ("strings", "dlstrings"), "Unsupported feature string table")
    demand(8 <= len(data) <= MAX_TABLE, "Invalid string-table size")
    count, size = struct.unpack_from("<II", data)
    base = 8 + 8 * count
    demand(base + size == len(data), "Invalid string-table directory size")
    rows, seen = [], set()
    for index in range(count):
        sid, offset = struct.unpack_from("<II", data, 8 + index * 8)
        demand(sid not in seen and offset < size, "Duplicate or invalid string-table entry")
        seen.add(sid)
        start = base + offset
        if extension == "strings":
            end = data.find(b"\0", start)
            demand(end >= 0, "Unterminated string-table entry")
        else:
            demand(start + 4 <= len(data), "Truncated string length")
            length = struct.unpack_from("<I", data, start)[0]
            start += 4
            end = start + length - 1
            demand(length >= 1 and end < len(data) and data[end] == 0,
                   "Invalid length-prefixed string")
        raw = data[start:end]
        demand(b"\0" not in raw, "Embedded NUL in string-table entry")
        rows.append((sid, raw))
    return rows


def reset_selected(canonical, vanilla, selected, extension):
    """Restore complete selected IDs without normalizing newlines or placeholders."""
    rows = read_table(canonical, extension)
    originals = dict(read_table(vanilla, extension))
    selected = set(selected)
    demand(selected <= originals.keys(), "Feature strings are absent from the vanilla baseline")
    demand(selected <= {sid for sid, _ in rows}, "Feature strings are absent from KKS content")
    directory, pool = bytearray(), bytearray()
    changed = False
    for sid, value in rows:
        replacement = originals[sid] if sid in selected else value
        changed |= replacement != value
        directory.extend(struct.pack("<II", sid, len(pool)))
        if extension == "dlstrings":
            pool.extend(struct.pack("<I", len(replacement) + 1))
        pool.extend(replacement + b"\0")
        demand(len(pool) + 8 + len(rows) * 8 <= MAX_TABLE, "Derived string table is too large")
    result = struct.pack("<II", len(rows), len(pool)) + directory + pool
    return bytes(result) if changed else canonical
