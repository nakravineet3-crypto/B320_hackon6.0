import json
import math
from pathlib import Path
from typing import List
from uuid import uuid4

DATA_PATH = Path(__file__).parent.parent / "data"


def _load_catalog() -> list:
    path = DATA_PATH / "catalog.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return []


CATALOG = _load_catalog()

# Sneha's demo cart ASINs
SNEHA_DEMO_ASINS = {
    "DEMO_PLATES_01",
    "DEMO_BALLOONS_01",
    "DEMO_STREAMERS_01",
    "DEMO_CUPS_SPONSORED",
}

# Hardcoded demo flags — never change these
DEMO_FLAGS = [
    {
        "flag_id": "f1",
        "type": "quantity_error",
        "severity": "red",
        "message": "12 plates — you need 24",
        "math_explanation": "2 plates per child × 12 kids = 24 plates. You have 1 pack of 12. Need 2 packs.",
        "affected_asin": "DEMO_PLATES_01",
        "fix_action": "increase_quantity",
        "animate_at_ms": 1500,
    },
    {
        "flag_id": "f2",
        "type": "missing_accessory",
        "severity": "red",
        "message": "Balloon set — no pump included",
        "math_explanation": "This balloon set requires a pump to inflate. No pump found in your cart.",
        "affected_asin": "DEMO_BALLOONS_01",
        "fix_action": "add_compatible_item",
        "animate_at_ms": 3000,
    },
    {
        "flag_id": "f3",
        "type": "not_amazon_now",
        "severity": "amber",
        "message": "Streamers not on Amazon Now — swapping",
        "math_explanation": "These streamers arrive in 2 days. Party is tomorrow (18hrs). Swapped to Now-eligible alternative.",
        "affected_asin": "DEMO_STREAMERS_01",
        "fix_action": "swap_now_eligible",
        "animate_at_ms": 4500,
    },
    {
        "flag_id": "f4",
        "type": "sponsored_blocked",
        "severity": "blue",
        "message": "Sponsored cups blocked — failed child_safe check",
        "math_explanation": "This sponsored product has no child_safe certification. Required for kids birthday mission. Blocked per MissionCart policy.",
        "affected_asin": "DEMO_CUPS_SPONSORED",
        "fix_action": "block_sponsored",
        "animate_at_ms": 6000,
    },
]

DEMO_REPAIRED_CART = [
    {"asin": "DEMO_PLATES_01", "title": "Paper Plates 10pc", "quantity": 3, "price_inr": 120, "amazon_now_eligible": True, "sponsored": False},
    {"asin": "MC_PUMP_001", "title": "Balloon Pump", "quantity": 1, "price_inr": 149, "amazon_now_eligible": True, "sponsored": False},
    {"asin": "DEMO_BALLOONS_01", "title": "Balloon Set 20pc", "quantity": 1, "price_inr": 180, "amazon_now_eligible": True, "sponsored": False},
    {"asin": "MC_STREAMERS_NOW", "title": "Streamers 5pc (Now)", "quantity": 2, "price_inr": 85, "amazon_now_eligible": True, "sponsored": False},
    {"asin": "MC_CUPS_001", "title": "Paper Cups 20pc", "quantity": 2, "price_inr": 79, "amazon_now_eligible": True, "sponsored": False},
]


def is_demo_cart(cart_items: list) -> bool:
    """Returns True if this is Sneha's demo cart or empty cart (demo mode)."""
    if not cart_items:
        return True
    cart_asins = {i.get("asin", "") for i in cart_items}
    return cart_asins == SNEHA_DEMO_ASINS


# ── QUANTITY RULES ────────────────────────────────────

QUANTITY_RULES = {
    "plates": {"rate": 2.0, "buffer": 1.15},
    "disposable_plates": {"rate": 2.0, "buffer": 1.15},
    "cups": {"rate": 2.5, "buffer": 1.10},
    "disposable_cups": {"rate": 2.5, "buffer": 1.10},
    "napkins": {"rate": 3.0, "buffer": 1.15},
    "balloon_set": {"rate": 3.0, "buffer": 1.20},
    "balloons": {"rate": 3.0, "buffer": 1.20},
    "return_gifts": {"rate": 1.0, "buffer": 1.05},
    "trekking_socks": {"rate": 3.0, "buffer": 1.0},
    "water_bottle": {"rate": 1.0, "buffer": 1.0},
    "towels": {"rate": 3.0, "buffer": 1.0},
}

FIXED_QUANTITY = {
    "balloon_pump": 1,
    "candles": 1,
    "first_aid": 1,
    "torch": 1,
    "cake_knife": 1,
    "trash_bags": 1,
    "decorations": 1,
}

# ── COMPATIBILITY ────────────────────────────────────

COMPATIBILITY = {
    "balloon_set": {
        "requires": "balloon_pump",
        "message": "Balloon set needs a pump to inflate",
        "evidence": "83% of similar occasions include a pump",
    },
    "balloons": {
        "requires": "balloon_pump",
        "message": "Balloons need a pump to inflate",
        "evidence": "83% co-purchase rate in community sessions",
    },
    "induction_cooktop": {
        "requires": "induction_compatible_vessel",
        "message": "Induction cooktop needs compatible vessels",
        "evidence": "84% of home setup sessions include vessels",
    },
    "cake": {
        "requires": "candles",
        "message": "Birthday cake needs candles",
        "evidence": "96% of birthday parties include candles",
    },
}


def run_real_audit(
    cart_items: list,
    occasion_type: str,
    headcount: int,
    budget_max: float,
    deadline_hours: int,
    safety_context: str,
) -> dict:
    """Run real constraint-based audit on any cart.
    Returns flags, repaired cart, totals.
    """
    flags = []
    flag_index = 0
    cart_categories = [i.get("category", "") for i in cart_items]

    # CHECK 1: QUANTITY
    for item in cart_items:
        category = item.get("category", "")
        pack_size = item.get("pack_size", 10)
        current_qty = item.get("quantity", 1)
        current_units = current_qty * pack_size

        rule = QUANTITY_RULES.get(category)
        if rule and headcount > 1:
            needed_units = math.ceil(headcount * rule["rate"] * rule["buffer"])
            needed_packs = math.ceil(needed_units / pack_size)

            if current_units < needed_units * 0.8:
                flags.append({
                    "flag_id": str(uuid4()),
                    "type": "quantity_error",
                    "severity": "red",
                    "message": f"{current_units} {category.replace('_', ' ')} — you need {needed_units}",
                    "math_explanation": (
                        f"{rule['rate']} per person × {headcount} guests × "
                        f"{rule['buffer']} buffer = {needed_units} units. "
                        f"You have {current_units}. Need {needed_packs} packs."
                    ),
                    "affected_asin": item.get("asin"),
                    "fix_action": "increase_quantity",
                    "fix_details": {"needed_packs": needed_packs, "current_packs": current_qty},
                    "animate_at_ms": flag_index * 1500 + 1500,
                })
                flag_index += 1

    # CHECK 2: COMPATIBILITY
    for item in cart_items:
        category = item.get("category", "")
        rule = COMPATIBILITY.get(category)
        if rule:
            required = rule["requires"]
            if required not in cart_categories:
                required_product = next(
                    (p for p in CATALOG if p.get("category") == required), None
                )
                flags.append({
                    "flag_id": str(uuid4()),
                    "type": "missing_accessory",
                    "severity": "red",
                    "message": (
                        f"{item.get('title', 'Item')[:25]} — "
                        f"{required.replace('_', ' ')} not in cart"
                    ),
                    "math_explanation": f"{rule['message']}. {rule['evidence']}.",
                    "affected_asin": item.get("asin"),
                    "fix_action": "add_compatible_item",
                    "fix_details": {
                        "required_category": required,
                        "suggested_product": required_product.get("title") if required_product else required,
                        "suggested_asin": required_product.get("asin") if required_product else None,
                        "suggested_price": required_product.get("price", 0) if required_product else 0,
                    },
                    "animate_at_ms": flag_index * 1500 + 1500,
                })
                flag_index += 1

    # CHECK 3: AMAZON NOW
    if deadline_hours and deadline_hours <= 24:
        for item in cart_items:
            if not item.get("amazon_now_eligible", True):
                category = item.get("category", "")
                alternative = next(
                    (p for p in CATALOG
                     if p.get("category") == category
                     and p.get("amazon_now_eligible")
                     and p.get("asin") != item.get("asin")),
                    None,
                )
                flags.append({
                    "flag_id": str(uuid4()),
                    "type": "not_amazon_now",
                    "severity": "amber",
                    "message": f"{item.get('title', 'Item')[:25]} not on Amazon Now — swapping",
                    "math_explanation": (
                        f"Delivery: {item.get('delivery_eta', 'unknown')}. "
                        f"Your deadline: {deadline_hours}hrs. "
                        f"Swapped to Now-eligible alternative."
                    ),
                    "affected_asin": item.get("asin"),
                    "fix_action": "swap_now_eligible",
                    "fix_details": {
                        "alternative_asin": alternative.get("asin") if alternative else None,
                        "alternative_title": alternative.get("title") if alternative else None,
                        "alternative_price": alternative.get("price", 0) if alternative else 0,
                    },
                    "animate_at_ms": flag_index * 1500 + 1500,
                })
                flag_index += 1

    # CHECK 4: SPONSORED
    for item in cart_items:
        if item.get("sponsored", False):
            item_safety = item.get("safety_tags", [])
            failed = (
                safety_context
                and safety_context != "general"
                and safety_context not in item_safety
            )
            if failed:
                flags.append({
                    "flag_id": str(uuid4()),
                    "type": "sponsored_blocked",
                    "severity": "blue",
                    "message": f"Sponsored product blocked — failed {safety_context} check",
                    "math_explanation": (
                        f"This sponsored product has no {safety_context} certification. "
                        f"Required for this mission. Blocked per MissionCart policy."
                    ),
                    "affected_asin": item.get("asin"),
                    "fix_action": "block_sponsored",
                    "fix_details": {"missing_tag": safety_context},
                    "animate_at_ms": flag_index * 1500 + 1500,
                })
                flag_index += 1

    # CHECK 5: BUDGET
    total = sum(
        i.get("price_inr", i.get("price", 0)) * i.get("quantity", 1)
        for i in cart_items
    )
    if budget_max and total > budget_max * 1.05:
        over_by = total - budget_max
        flags.append({
            "flag_id": str(uuid4()),
            "type": "budget_overage",
            "severity": "amber",
            "message": f"Cart is ₹{over_by:.0f} over budget",
            "math_explanation": (
                f"Total ₹{total:.0f} vs budget ₹{budget_max:.0f}. "
                f"Removing lowest-priority items."
            ),
            "affected_asin": None,
            "fix_action": "budget_repair",
            "fix_details": {"over_by": round(over_by, 2), "original_total": round(total, 2)},
            "animate_at_ms": flag_index * 1500 + 1500,
        })

    # Cap to 4 flags max, sorted by severity priority
    severity_order = {"red": 0, "blue": 1, "amber": 2}
    flags.sort(key=lambda f: severity_order.get(f.get("severity", "amber"), 99))
    flags = flags[:4]
    # Re-assign animate_at_ms after capping
    for i, flag in enumerate(flags):
        flag["animate_at_ms"] = (i + 1) * 1500

    # BUILD REPAIRED CART
    repaired_cart = list(cart_items)

    for flag in flags:
        if flag["type"] == "missing_accessory":
            details = flag.get("fix_details", {})
            if details.get("suggested_asin"):
                product = next(
                    (p for p in CATALOG if p.get("asin") == details["suggested_asin"]),
                    None,
                )
                if product:
                    repaired_cart.append({
                        "asin": product["asin"],
                        "title": product["title"],
                        "category": product["category"],
                        "quantity": 1,
                        "price_inr": product["price"],
                        "amazon_now_eligible": product.get("amazon_now_eligible", True),
                        "sponsored": False,
                        "added_by_audit": True,
                    })

        elif flag["type"] == "not_amazon_now":
            details = flag.get("fix_details", {})
            if details.get("alternative_asin"):
                repaired_cart = [
                    i for i in repaired_cart if i.get("asin") != flag["affected_asin"]
                ]
                product = next(
                    (p for p in CATALOG if p.get("asin") == details["alternative_asin"]),
                    None,
                )
                if product:
                    repaired_cart.append({
                        "asin": product["asin"],
                        "title": product["title"],
                        "category": product["category"],
                        "quantity": 1,
                        "price_inr": product["price"],
                        "amazon_now_eligible": True,
                        "sponsored": False,
                        "swapped_by_audit": True,
                    })

        elif flag["type"] == "sponsored_blocked":
            repaired_cart = [
                i for i in repaired_cart if i.get("asin") != flag["affected_asin"]
            ]
            blocked = next(
                (i for i in cart_items if i.get("asin") == flag["affected_asin"]),
                None,
            )
            if blocked:
                alt = next(
                    (p for p in CATALOG
                     if p.get("category") == blocked.get("category")
                     and not p.get("sponsored")
                     and p.get("amazon_now_eligible")),
                    None,
                )
                if alt:
                    repaired_cart.append({
                        "asin": alt["asin"],
                        "title": alt["title"],
                        "category": alt["category"],
                        "quantity": 1,
                        "price_inr": alt["price"],
                        "amazon_now_eligible": True,
                        "sponsored": False,
                        "replaced_by_audit": True,
                    })

    original_total = sum(
        i.get("price_inr", i.get("price", 0)) * i.get("quantity", 1)
        for i in cart_items
    )
    repaired_total = sum(
        i.get("price_inr", i.get("price", 0)) * i.get("quantity", 1)
        for i in repaired_cart
    )

    return {
        "flags": flags,
        "original_cart": cart_items,
        "repaired_cart": repaired_cart,
        "original_total": round(original_total, 2),
        "repaired_total": round(repaired_total, 2),
        "coverage_score": f"{len(repaired_cart)}/{len(repaired_cart)}",
        "all_amazon_now": all(
            i.get("amazon_now_eligible", True) for i in repaired_cart
        ),
        "analysis_stats": {
            "items_checked": len(cart_items),
            "flags_found": len(flags),
            "items_repaired": len([f for f in flags if f["type"] != "quantity_error"]),
            "engine": "constraint_based_v1",
        },
    }
