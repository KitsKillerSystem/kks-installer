"""Perk-card artwork is activated by PERK:DESC strings; Off restores native text."""

from .string_tables import reset_selected

ON = "on"
OFF = "off"
PERK_PROFILES = (ON, OFF)
CAPABILITY = "vanilla-perk-cards-v1"
CATEGORIES = ("PERK:DESC",)
LABELS = {
    ON: "KKS Perk Cards On (Recommended)",
    OFF: "KKS Perk Cards Off (Vanilla)",
}


def reset_perks(canonical, vanilla, categories):
    return reset_selected(canonical, vanilla, categories["PERK:DESC"], "dlstrings")
