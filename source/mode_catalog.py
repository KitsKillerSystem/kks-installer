"""Publisher-only composition of six approved STRINGS presentations."""

import base64
import json
from pathlib import Path

from kks_installer.engine import demand, digest
from kks_installer.equipment import FULL, VANILLA, NAMING_PROFILES, reset_equipment
from kks_installer.string_tables import read_table
from kks_installer import string_modes as modes


def load_mode_tables(path):
    from kks_installer.packages import strict_json, bounded_file, MAX_MANIFEST, fields
    path = Path(path).resolve()
    rows = strict_json(bounded_file(path, MAX_MANIFEST))
    demand(type(rows) is list and len(rows) == 6, "Supply exactly six mode table paths")
    result = {}
    for row in rows:
        fields(row, "food junk path")
        demand(type(row["food"]) is str and row["food"] in modes.FOOD_PROFILES
               and type(row["junk"]) is str and row["junk"] in modes.JUNK_PROFILES,
               "Unknown mode table choice")
        key = (row["food"], row["junk"])
        demand(key not in result and type(row["path"]) is str and row["path"],
               "Duplicate mode table choice or invalid path")
        result[key] = path.parent / row["path"]
    return result


def build_modes(canonical, native, equipment_categories, tables):
    """Return one patch payload and all twelve signed STRINGS outputs.

    tables maps (food-v2|family-food, glyph|text|none) to complete table paths.
    Exact raw values and directory order are checked for every composition.
    Unused byte-pool layout is normalized only when a value actually changes.
    """
    expected = {(f, j) for f in modes.FOOD_PROFILES for j in modes.JUNK_PROFILES}
    demand(set(tables) == expected, "Supply every food and junk STRINGS combination")
    baseline = read_table(canonical, "strings")
    values = dict(baseline)
    decoded = {}
    for choice, path in tables.items():
        raw = Path(path).read_bytes()
        rows = read_table(raw, "strings")
        demand([sid for sid, _ in rows] == [sid for sid, _ in baseline],
               "String mode table changed the directory IDs or order")
        decoded[choice] = rows
        if choice == (modes.FOOD_DEFAULT, modes.JUNK_DEFAULT):
            demand(raw == canonical, "Default string mode must be the exact canonical payload")

    def delta(choice):
        return [{"id": sid, "value": base64.b64encode(value).decode("ascii")}
                for sid, value in sorted(decoded[choice]) if value != values[sid]]

    document = {"schema": 1,
                "food": {"family-food": delta(("family-food", "glyph"))},
                "junk": {"text": delta(("food-v2", "text")), "none": delta(("food-v2", "none"))}}
    equipment_ids = set().union(*(set(v) for v in equipment_categories.values()))
    patch = modes.decode_patch(document, equipment_ids)
    outputs = []
    for food in modes.FOOD_PROFILES:
        for junk in modes.JUNK_PROFILES:
            derived = modes.apply_modes(canonical, patch, food, junk)
            demand(read_table(derived, "strings") == decoded[(food, junk)],
                   "Food and junk tables cannot be composed independently")
            for naming in NAMING_PROFILES:
                result = derived if naming == FULL else reset_equipment(derived, native, equipment_categories)
                outputs.append(dict(naming=naming, food=food, junk=junk, sha256=digest(result), size=len(result)))
    raw = (json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n").encode()
    demand(len(raw) <= modes.MAX_PATCH, "String mode patch exceeds the supported size")
    return raw, dict(algorithm=modes.CAPABILITY, payload=modes.PAYLOAD, outputs=outputs)
