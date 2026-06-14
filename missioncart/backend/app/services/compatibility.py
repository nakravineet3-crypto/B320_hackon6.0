from typing import Dict, List, Tuple


# Inline compatibility rules
# These are functional dependencies, not claims
COMPATIBILITY_RULES: Dict[str, dict] = {
    "balloon_set": {
        "requires": ["balloon_pump"],
        "message": "Balloon set needs a pump to inflate",
    },
    "balloons": {
        "requires": ["balloon_pump"],
        "message": "Balloons need a pump to inflate",
    },
    "induction_cooktop": {
        "requires": ["induction_compatible_vessel"],
        "message": "Induction cooktop needs compatible vessels",
    },
    "cake": {
        "recommends": ["candles", "cake_knife"],
        "message": "Cake needs candles and a knife",
    },
    "camping_tent": {
        "requires": ["sleeping_bag"],
        "message": "Tent needs a sleeping bag",
    },
}


def check_compatibility(
    category: str,
    cart_categories: List[str],
) -> Tuple[List[str], List[str]]:
    """Returns (missing_required, incompatible_found)"""
    rules = COMPATIBILITY_RULES.get(category, {})

    missing = [
        r for r in rules.get("requires", [])
        if r not in cart_categories
    ]

    incompatible = [
        i for i in rules.get("incompatible_with", [])
        if i in cart_categories
    ]

    return missing, incompatible


def get_missing_message(category: str) -> str:
    rules = COMPATIBILITY_RULES.get(category, {})
    return rules.get("message", "")
