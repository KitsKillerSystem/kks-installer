"""Deterministic, byte-preserving equipment-name reset over complete STRINGS tables."""

import struct

from .engine import demand

FULL = "full-kks"
VANILLA = "vanilla-equipment"
NAMING_PROFILES = (FULL, VANILLA)
CAPABILITY = "vanilla-equipment-v1"
CATEGORIES = ("WEAP:FULL", "ARMO:FULL", "INNR:WNAM")
LABELS = {
    FULL: "KKS Weapon & Armor Treatment (Recommended)",
    VANILLA: "Vanilla Equipment Naming",
}
MAX_TABLE = 256 * 1024 * 1024


def read_strings(data):
    demand(8 <= len(data) <= MAX_TABLE, "Invalid STRINGS table size")
    count, size = struct.unpack_from("<II", data)
    base = 8 + 8 * count
    demand(base + size == len(data), "Invalid STRINGS directory size")
    rows, seen = [], set()
    for index in range(count):
        sid, offset = struct.unpack_from("<II", data, 8 + index * 8)
        demand(sid not in seen and offset < size, "Duplicate or invalid STRINGS entry")
        seen.add(sid)
        end = data.find(b"\0", base + offset)
        demand(end >= 0, "Unterminated STRINGS entry")
        rows.append((sid, data[base + offset : end]))
    return rows


def reset_equipment(canonical, vanilla, categories):
    """Preserve every unrelated value as raw bytes, including XML-illegal text."""
    rows = read_strings(canonical)
    originals = dict(read_strings(vanilla))
    selected = set().union(*(set(categories[name]) for name in CATEGORIES))
    demand(selected <= originals.keys(), "Equipment names are absent from the vanilla baseline")
    demand(selected <= {sid for sid, _ in rows}, "Equipment names are absent from KKS content")
    directory, pool = bytearray(), bytearray()
    changed = False
    for sid, value in rows:
        replacement = originals[sid] if sid in selected else value
        changed |= replacement != value
        directory.extend(struct.pack("<II", sid, len(pool)))
        pool.extend(replacement + b"\0")
    result = struct.pack("<II", len(rows), len(pool)) + directory + pool
    demand(len(result) <= MAX_TABLE, "Derived STRINGS table is too large")
    return bytes(result) if changed else canonical
