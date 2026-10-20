"""Signed, bounded raw-byte food/junk presentation patches; no executable hooks."""

import base64
import struct

from .engine import demand
from .string_tables import read_table, MAX_TABLE

CAPABILITY = "kks-string-modes-v1"
PAYLOAD = "payload/string-modes.json"
MAX_PATCH = 4 * 1024 * 1024
FOOD_DEFAULT = "food-v2"
JUNK_DEFAULT = "glyph"
FOOD_PROFILES = (FOOD_DEFAULT, "family-food")
JUNK_PROFILES = (JUNK_DEFAULT, "text", "none")
FOOD_LABELS = {FOOD_DEFAULT: "Kit's Style", "family-food": "Abby's Style"}
JUNK_LABELS = {JUNK_DEFAULT: "KKS Default (Glyph Components)", "text": "Text Based", "none": "None"}


def decode_patch(document, equipment_ids=()):
    demand(type(document) is dict and set(document) == {"schema", "food", "junk"}
           and type(document["schema"]) is int and document["schema"] == 1,
           "Invalid string mode patch schema")
    result = {}
    for group, choices in (("food", ("family-food",)), ("junk", ("text", "none"))):
        demand(type(document[group]) is dict and set(document[group]) == set(choices),
               "Unknown string mode patch choice")
        result[group] = {}
        for choice in choices:
            rows = document[group][choice]
            demand(type(rows) is list and len(rows) <= 10000, "Invalid string mode patch size")
            values = {}
            previous = 0
            for row in rows:
                demand(type(row) is dict and set(row) == {"id", "value"}, "Invalid string mode patch row")
                sid = row["id"]
                demand(type(sid) is int and previous < sid <= 0xffffffff, "Unsorted or duplicate string mode ID")
                previous = sid
                demand(type(row["value"]) is str and len(row["value"]) <= 262144,
                       "Invalid string mode value")
                try:
                    raw = base64.b64decode(row["value"], validate=True)
                except (ValueError, TypeError) as error:
                    raise ValueError("Invalid string mode base64") from error
                demand(b"\0" not in raw, "Embedded NUL in string mode value")
                values[sid] = raw
            result[group][choice] = values
    food_ids = set(result["food"]["family-food"])
    junk_ids = set(result["junk"]["text"]) | set(result["junk"]["none"])
    demand(not food_ids.intersection(junk_ids), "Food and junk string mode IDs overlap")
    demand(not (food_ids | junk_ids).intersection(equipment_ids),
           "String mode IDs overlap equipment categories")
    return result


def apply_modes(canonical, patch, food=FOOD_DEFAULT, junk=JUNK_DEFAULT):
    demand(food in FOOD_PROFILES and junk in JUNK_PROFILES, "Unknown food or junk mode")
    replacements = dict(patch["food"].get(food, {}))
    replacements.update(patch["junk"].get(junk, {}))
    if not replacements:
        return canonical
    rows = read_table(canonical, "strings")
    demand(replacements.keys() <= {sid for sid, _ in rows}, "String mode IDs are missing from content")
    directory, pool = bytearray(), bytearray()
    changed = False
    for sid, value in rows:
        replacement = replacements.get(sid, value)
        changed |= replacement != value
        directory.extend(struct.pack("<II", sid, len(pool)))
        pool.extend(replacement + b"\0")
        demand(len(pool) + 8 + len(rows) * 8 <= MAX_TABLE, "Derived string mode table is too large")
    return bytes(struct.pack("<II", len(rows), len(pool)) + directory + pool) if changed else canonical
