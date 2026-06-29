import json
import math
from pathlib import Path
from typing import List
from uuid import uuid4

DATA_PATH = Path(__file__).parent.parent / "data"


# ── MODULE-LEVEL DATA LOADS ──────────────────────────────────────────────────

def _load_catalog() -> list:
    path = DATA_PATH / "catalog.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return []


def _load_json_safe(filename: str, fallback):
    """Load a JSON file from DATA_PATH. Returns fallback on any error — never crashes startup."""
    path = DATA_PATH / filename
    try:
        if path.exists():
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return fallback


CATALOG = _load_catalog()

# occasion_need_taxonomy.json — used for real coverage scoring
_TAXONOMY_RAW = _load_json_safe("occasion_need_taxonomy.json", {})
OCCASION_TAXONOMY = _TAXONOMY_RAW.get("occasions", {})

# quantity_sufficiency_rules.json — richer formula library overriding hardcoded QUANTITY_RULES
_QTY_RAW = _load_json_safe("quantity_sufficiency_rules.json", {})
QUANTITY_RULES_JSON: list = _QTY_RAW.get("rules", [])

# social_completeness.json — near-universal item signals per occasion
_SC_RAW = _load_json_safe("social_completeness.json", {})
SOCIAL_COMPLETENESS: dict = _SC_RAW.get("occasions", {})


# ── DEMO CONSTANTS ────────────────────────────────────────────────────────────

# Legacy ASIN set kept for reference — is_demo_cart() no longer uses it alone
SNEHA_DEMO_ASINS = {
    "DEMO_PLATES_01",
    "DEMO_BALLOONS_01",
    "DEMO_STREAMERS_01",
    "DEMO_CUPS_SPONSORED",
}

# Hardcoded demo flags — NEVER modify these
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

# Hardcoded ASIN map kept intact — never modify
DEMO_ASIN_MAP = {
    "DEMO_PLATES_01": "Paper Plates 10pc",
    "DEMO_BALLOONS_01": "Balloon Set 20pc",
    "DEMO_STREAMERS_01": "Streamers 5pc",
    "DEMO_CUPS_SPONSORED": "Party Cups 10pc (Sponsored)",
}


# ── QUANTITY RULES (hardcoded fallback) ───────────────────────────────────────

QUANTITY_RULES = {
    "plates":           {"rate": 2.0, "buffer": 1.15},
    "disposable_plates":{"rate": 2.0, "buffer": 1.15},
    "cups":             {"rate": 2.5, "buffer": 1.10},
    "disposable_cups":  {"rate": 2.5, "buffer": 1.10},
    "napkins":          {"rate": 3.0, "buffer": 1.15},
    "balloon_set":      {"rate": 3.0, "buffer": 1.20},
    "balloons":         {"rate": 3.0, "buffer": 1.20},
    "return_gifts":     {"rate": 1.0, "buffer": 1.05},
    "trekking_socks":   {"rate": 3.0, "buffer": 1.0},
    "water_bottle":     {"rate": 1.0, "buffer": 1.0},
    "towels":           {"rate": 3.0, "buffer": 1.0},
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

# ── COMPATIBILITY (hardcoded) ──────────────────────────────────────────────────

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


# ── HELPER: QUANTITY RULE LOOKUP ──────────────────────────────────────────────

def _get_qty_rule_json(category: str, occasion_type: str) -> dict | None:
    """
    Find the best matching rule from quantity_sufficiency_rules.json.
    Prefers occasion-specific context over 'default' context.
    Returns None if no rule found for the category.
    """
    best: dict | None = None
    for rule in QUANTITY_RULES_JSON:
        if rule.get("category") != category:
            continue
        contexts = rule.get("occasion_contexts", ["default"])
        if occasion_type and occasion_type in contexts:
            # Exact occasion match — highest priority, return immediately
            return rule
        if "default" in contexts:
            best = rule  # Keep as fallback
    return best


def _eval_qty_formula(formula: str, headcount: int) -> int:
    """
    Safely evaluate a simple quantity formula string.
    Supported tokens: headcount, math.ceil, *, /, +, -, integers.
    """
    try:
        result = eval(  # noqa: S307 — formula is from our own JSON, not user input
            formula,
            {"__builtins__": {}},
            {"headcount": headcount, "ceil": math.ceil},
        )
        return max(1, int(math.ceil(float(result))))
    except Exception:
        return 1


# ── DEMO CART DETECTION ───────────────────────────────────────────────────────

def is_demo_cart(
    cart_items: list,
    occasion_type: str = "",
    session_goal: str = "",
) -> bool:
    """
    Multi-gate demo cart detection — resilient to ASIN changes.
    All 5 gates must pass for the demo path to activate.
    """
    if not cart_items or len(cart_items) < 3:
        return False

    # Gate 1: occasion or goal must signal birthday/kids
    birthday_keywords = {"kids_birthday", "birthday", "kids", "party", "children"}
    text = f"{occasion_type} {session_goal}".lower()
    if not any(kw in text for kw in birthday_keywords):
        return False

    # Gate 2: item count must be 3-6
    if not (3 <= len(cart_items) <= 6):
        return False

    # Gate 3: cart must contain plates + balloons + cups categories
    cart_cats = {item.get("category", "") for item in cart_items}
    # party_supplies is accepted as a proxy for plates (B001PLATES uses it)
    if "party_supplies" in cart_cats:
        cart_cats.add("plates")
    required_cats = {"plates", "balloon_set", "cups"}
    if not required_cats.issubset(cart_cats):
        return False

    # Gate 4: must have one sponsored AND one non-Now item (demo story requires both)
    has_sponsored = any(item.get("sponsored", False) for item in cart_items)
    has_non_now = any(not item.get("amazon_now_eligible", True) for item in cart_items)
    if not (has_sponsored and has_non_now):
        return False

    # Gate 5: the sponsored item must have empty safety_tags (signature of DEMO_CUPS_SPONSORED)
    sponsored_items = [i for i in cart_items if i.get("sponsored")]
    if not any(len(i.get("safety_tags", ["sentinel"])) == 0 for i in sponsored_items):
        return False

    return True


# ── COVERAGE SCORE ────────────────────────────────────────────────────────────

def compute_coverage_score(
    repaired_cart: list,
    occasion_type: str,
    taxonomy: dict,
) -> dict:
    """
    Real coverage: covered must-have needs / total must-have needs for the occasion.
    Falls back to item count when the occasion has no taxonomy profile.
    """
    profile = taxonomy.get(occasion_type or "general", {})
    must_haves = [n for n in profile.get("needs", []) if n.get("priority") == "must_have"]

    if not must_haves:
        # No taxonomy profile — fall back to item count ratio (always complete)
        n = len(repaired_cart)
        return {
            "display": f"{n}/{n}",
            "covered": n,
            "total": n,
            "fraction": 1.0,
            "missing": [],
        }

    cart_cats = {item.get("category", "") for item in repaired_cart}

    needs_covered: set = set()
    needs_total: set = set()

    for need in must_haves:
        need_id = need.get("need_id") or (need.get("category_candidates") or [""])[0]
        needs_total.add(need_id)
        if any(cat in cart_cats for cat in need.get("category_candidates", [])):
            needs_covered.add(need_id)

    covered = len(needs_covered)
    total = len(needs_total) if needs_total else len(repaired_cart)

    return {
        "display": f"{covered}/{total}",
        "covered": covered,
        "total": total,
        "fraction": round(covered / total, 3) if total > 0 else 1.0,
        "missing": list(needs_total - needs_covered),
    }


# ── SEVERITY SORT KEY ────────────────────────────────────────────────────────

def _flag_sort_key(flag: dict) -> tuple:
    """
    Sorting key for flags before the 4-flag cap.
    Priority: red(0) > blue(1) > amber(2)
    Within same severity: missing_accessory(0) > sponsored_blocked(1) >
                          not_amazon_now(2) > quantity_error(3) >
                          quality_floor / return_risk(4) >
                          social_completeness(5)
    """
    severity_rank = {"red": 0, "blue": 1, "amber": 2}
    type_rank = {
        "missing_accessory": 0,
        "sponsored_blocked": 1,
        "not_amazon_now": 2,
        "quantity_error": 3,
        "quality_floor": 4,
        "return_risk": 4,
        "budget_overage": 5,
        "social_completeness": 6,
    }
    s = severity_rank.get(flag.get("severity", "amber"), 99)
    t = type_rank.get(flag.get("type", ""), 99)
    return (s, t)


# ── REAL AUDIT ────────────────────────────────────────────────────────────────

def run_real_audit(
    cart_items: list,
    occasion_type: str,
    headcount: int | None,
    budget_max: float | None,
    deadline_hours: int | None,
    safety_context: str,
) -> dict:
    """
    Run constraint-based audit on any non-demo cart.
    Checks 1-8 applied. Returns flags (max 4), repaired cart, totals, coverage.
    """
    flags: list[dict] = []
    cart_categories = [i.get("category", "") for i in cart_items]

    # ── CHECK 1: QUANTITY ─────────────────────────────────────────────────────
    if headcount and headcount > 1:
        for item in cart_items:
            category = item.get("category", "")
            pack_size = item.get("pack_size", 10)
            current_qty = item.get("quantity", 1)
            current_units = current_qty * pack_size

            # Prefer JSON rule; fall back to hardcoded dict
            json_rule = _get_qty_rule_json(category, occasion_type)
            if json_rule:
                needed_units = max(
                    _eval_qty_formula(json_rule["formula"], headcount),
                    json_rule.get("minimum", 1),
                )
                rate_display = json_rule["formula"]
                buffer = 1.0  # JSON rules bake the buffer into the formula
            else:
                fallback = QUANTITY_RULES.get(category)
                if not fallback:
                    continue
                needed_units = math.ceil(headcount * fallback["rate"] * fallback["buffer"])
                rate_display = f"{fallback['rate']} per person × {headcount} guests × {fallback['buffer']} buffer"
                buffer = fallback["buffer"]

            needed_packs = math.ceil(needed_units / pack_size)

            if current_units < needed_units * 0.8:
                flags.append({
                    "flag_id": str(uuid4()),
                    "type": "quantity_error",
                    "severity": "red",
                    "message": f"{current_units} {category.replace('_', ' ')} — you need {needed_units}",
                    "math_explanation": (
                        f"Formula: {rate_display} = {needed_units} units. "
                        f"You have {current_units}. Need {needed_packs} packs."
                    ),
                    "affected_asin": item.get("asin"),
                    "fix_action": "increase_quantity",
                    "fix_details": {"needed_packs": needed_packs, "current_packs": current_qty},
                })

    # ── CHECK 2: COMPATIBILITY ────────────────────────────────────────────────
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
                })

    # ── CHECK 3: AMAZON NOW ───────────────────────────────────────────────────
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
                })

    # ── CHECK 4: SPONSORED ────────────────────────────────────────────────────
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
                })

    # ── CHECK 5: BUDGET ───────────────────────────────────────────────────────
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
        })

    # ── CHECK 6: QUALITY FLOOR ────────────────────────────────────────────────
    for item in cart_items:
        if item.get("rating", 5.0) < 3.5:
            flags.append({
                "flag_id": str(uuid4()),
                "type": "quality_floor",
                "severity": "amber",
                "title": f"Low-rated item: {item.get('title', '')}",
                "message": f"Rated {item.get('rating', '?')}★ — community reviews suggest issues with this product.",
                "math_explanation": "MissionCart quality floor is 3.5★. This item is below that threshold.",
                "asin": item.get("asin"),
                "affected_asin": item.get("asin"),
                "fix_action": "suggest_alternative",
                "fix_details": {"min_rating": 3.5, "current_rating": item.get("rating")},
            })

    # ── CHECK 7: RETURN RISK ──────────────────────────────────────────────────
    # Threshold mirrors constraint_engine.py: 0.30 (relaxes to 0.40 at low budget,
    # but audit always uses the standard 0.30 threshold for consistency)
    for item in cart_items:
        if item.get("return_risk", 0) > 0.30:
            flags.append({
                "flag_id": str(uuid4()),
                "type": "return_risk",
                "severity": "amber",
                "title": f"High return rate: {item.get('title', '')[:40]}",
                "message": (
                    f"{int(item.get('return_risk', 0) * 100)}% of buyers return this item. "
                    f"Consider an alternative."
                ),
                "math_explanation": "MissionCart flags items with >30% return rate as high-risk.",
                "asin": item.get("asin"),
                "affected_asin": item.get("asin"),
                "fix_action": "suggest_alternative",
                "fix_details": {"return_risk": item.get("return_risk")},
            })

    # ── CHECK 8: SOCIAL COMPLETENESS ──────────────────────────────────────────
    if occasion_type:
        social_data = SOCIAL_COMPLETENESS.get(occasion_type, {})
        cart_cats_set = {item.get("category", "") for item in cart_items}
        for item_sig in social_data.get("near_universal", []):
            if item_sig.get("adoption_rate", 0) >= 0.90:
                cats_to_check = item_sig.get("category_candidates", [item_sig.get("category", "")])
                # social_completeness.json stores single category strings, not lists
                if isinstance(cats_to_check, str):
                    cats_to_check = [cats_to_check]
                if not any(cat in cart_cats_set for cat in cats_to_check):
                    flags.append({
                        "flag_id": str(uuid4()),
                        "type": "social_completeness",
                        "severity": "blue",
                        "title": "Almost everyone adds this",
                        "message": item_sig.get("copy", ""),
                        "math_explanation": f"Adoption rate: {int(item_sig.get('adoption_rate', 0) * 100)}% of similar carts.",
                        "asin": None,
                        "affected_asin": None,
                        "fix_action": "suggest_add",
                        "fix_details": {
                            "category": item_sig.get("category"),
                            "adoption_rate": item_sig.get("adoption_rate"),
                        },
                    })

    # ── CAP: 4 FLAGS MAX, sorted by priority ─────────────────────────────────
    flags.sort(key=_flag_sort_key)
    flags = flags[:4]
    # Re-assign animate_at_ms after capping
    for i, flag in enumerate(flags):
        flag["animate_at_ms"] = (i + 1) * 1500

    # ── BUILD REPAIRED CART ───────────────────────────────────────────────────
    repaired_cart = list(cart_items)

    for flag in flags:
        fix = flag.get("fix_action")
        details = flag.get("fix_details", {})

        if flag["type"] == "missing_accessory":
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

        elif fix == "increase_quantity":
            # Fix 6: actually update the item quantity in repaired_cart
            needed_packs = details.get("needed_packs")
            if needed_packs:
                affected_asin = flag.get("affected_asin")
                for rc_item in repaired_cart:
                    if rc_item.get("asin") == affected_asin:
                        rc_item["user_quantity"] = needed_packs
                        rc_item["suggested_quantity"] = needed_packs
                        rc_item["quantity"] = needed_packs
                        break

        elif fix == "budget_repair":
            # Fix 7: remove lowest-priority optional items until within budget
            if budget_max:
                optional_items = [i for i in repaired_cart if i.get("priority") == "optional"]
                optional_items.sort(key=lambda x: x.get("price_inr", x.get("price", 0)), reverse=True)
                for opt_item in optional_items:
                    current_total = sum(
                        i.get("price_inr", i.get("price", 0)) * i.get("quantity", 1)
                        for i in repaired_cart
                    )
                    if current_total <= budget_max * 1.05:
                        break
                    repaired_cart = [
                        i for i in repaired_cart if i.get("asin") != opt_item.get("asin")
                    ]

    original_total = sum(
        i.get("price_inr", i.get("price", 0)) * i.get("quantity", 1)
        for i in cart_items
    )
    repaired_total = sum(
        i.get("price_inr", i.get("price", 0)) * i.get("quantity", 1)
        for i in repaired_cart
    )

    coverage = compute_coverage_score(repaired_cart, occasion_type, OCCASION_TAXONOMY)

    return {
        "flags": flags,
        "original_cart": cart_items,
        "repaired_cart": repaired_cart,
        "original_total": round(original_total, 2),
        "repaired_total": round(repaired_total, 2),
        "coverage_score": coverage["display"],
        "coverage_detail": coverage,
        "all_amazon_now": all(
            i.get("amazon_now_eligible", True) for i in repaired_cart
        ),
        "analysis_stats": {
            "items_checked": len(cart_items),
            "flags_found": len(flags),
            "items_repaired": len([f for f in flags if f["type"] not in ("quantity_error", "social_completeness")]),
            "engine": "constraint_based_v2",
        },
    }
