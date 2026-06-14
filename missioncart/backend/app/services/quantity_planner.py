"""
Quantity Planner — computes how many packs of an item are needed
for a mission, based on headcount, usage rate, buffer, and pack size.

Formula: ceil(headcount × usage_rate × buffer ÷ pack_size)
"""

import json
import math
from pathlib import Path
from typing import Optional


_RULES_PATH = Path(__file__).parent.parent / "data" / "quantity_rules.json"

# Map catalog categories → quantity rule keys
CATEGORY_TO_RULE = {
    "plates": "plates",
    "disposable_plates": "plates",
    "cups": "cups",
    "disposable_cups": "cups",
    "napkins": "napkins",
    "tissue_pack": "napkins",
    "balloon_set": "balloons",
    "balloons": "balloons",
    "candles": "candles",
    "cake_knife": "candles",
    "return_gifts": "return_gifts",
    "decoration_streamers": "streamers",
    "decorations": "streamers",
    "tablecloth": "tablecloth",
    "disposable_spoons": "spoons_forks",
    "disposable_forks": "spoons_forks",
    "trash_bags": "trash_bags",
    "cleanup": "trash_bags",
    "towels": "towels",
    "led_bulb": "led_bulbs",
    "water_bottle": "water_bottles",
    "diapers_newborn": "diapers_newborn",
    "trekking_socks": "socks_travel",
}


def _load_rules() -> dict:
    try:
        with open(_RULES_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


_RULES = _load_rules()


def _resolve_rule_key(category: str) -> Optional[str]:
    """Map a catalog category to a quantity rule key."""
    if not category:
        return None
    cat = category.lower()
    # Exact rule match
    if cat in _RULES:
        return cat
    # Mapping table
    if cat in CATEGORY_TO_RULE:
        return CATEGORY_TO_RULE[cat]
    # Partial match — rule key contained in category or vice versa
    for rule_key in _RULES:
        if rule_key in cat or cat in rule_key:
            return rule_key
    return None


def calculate_quantity(
    category: str,
    pack_size: int = 1,
    headcount: int = 1,
    days: int = 1,
    pet_weight_kg: float = 5.0,
) -> dict:
    """Compute packs/units required for a category given context.

    Returns: {units_required, packs_required, explanation}
    """
    pack_size = max(1, int(pack_size or 1))
    headcount = headcount or 1
    rule_key = _resolve_rule_key(category)
    rule = _RULES.get(rule_key) if rule_key else None

    if not rule:
        # Fallback: 1 pack
        label = (category or "item").replace("_", " ")
        return {
            "units_required": pack_size,
            "packs_required": 1,
            "explanation": f"1 pack of {label}",
        }

    # Evaluate the formula safely
    formula = rule.get("formula", "1")
    try:
        units = eval(
            formula,
            {"__builtins__": {}},
            {
                "headcount": headcount,
                "days": days,
                "pet_weight_kg": pet_weight_kg,
                "math": math,
            },
        )
    except Exception:
        units = pack_size

    units = max(1, math.ceil(units))

    if rule.get("pack_divide"):
        packs = max(1, math.ceil(units / pack_size))
    else:
        packs = max(1, int(units))

    # Format explanation with available context
    try:
        explanation = rule.get("explanation", "").format(
            units=units, headcount=headcount, days=days
        )
    except Exception:
        explanation = f"{units} units needed"

    return {
        "units_required": units,
        "packs_required": packs,
        "explanation": explanation,
    }


# Backward-compatible alias
def calculate(category: str, pack_size: int, context: dict) -> dict:
    return calculate_quantity(
        category=category,
        pack_size=pack_size,
        headcount=context.get("headcount", 1),
        days=context.get("trip_duration_days", 1),
        pet_weight_kg=context.get("pet_weight_kg", 5.0),
    )
