"""Deterministic, byte-preserving equipment-name reset over complete STRINGS tables."""

from .string_tables import read_table, reset_selected

FULL = "full-kks"
VANILLA = "vanilla-equipment"
NAMING_PROFILES = (FULL, VANILLA)
CAPABILITY = "vanilla-equipment-v1"
CATEGORIES = ("WEAP:FULL", "ARMO:FULL", "INNR:WNAM")
LABELS = {
    FULL: "KKS Weapon & Armor Treatment (Recommended)",
    VANILLA: "Vanilla Equipment Naming",
}


def read_strings(data):
    return read_table(data, "strings")


def reset_equipment(canonical, vanilla, categories):
    """Preserve every unrelated value as raw bytes, including XML-illegal text."""
    selected = set().union(*(set(categories[name]) for name in CATEGORIES))
    return reset_selected(canonical, vanilla, selected, "strings")
