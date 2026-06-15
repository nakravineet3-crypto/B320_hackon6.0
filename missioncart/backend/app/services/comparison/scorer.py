"""
Deterministic mission fit scoring.
All math. No LLM. Every number traceable.
"""

import math
import json
from pathlib import Path

ETA_SCORE_MAP = {
    "now_20min": 1.0,
    "today": 0.8,
    "tomorrow": 0.5,
    "2_days": 0.2,
    "3_plus": 0.0,
}

CATEGORY_BUDGET_RATIO = {
    "plates": 0.12,
    "cups": 0.08,
    "napkins": 0.05,
    "balloon_set": 0.15,
    "candles": 0.04,
    "return_gifts": 0.12,
    "decorations": 0.10,
    "snacks": 0.15,
    "mattress": 0.30,
    "bedsheet": 0.12,
    "water_bottle": 0.08,
    "first_aid": 0.06,
    "backpack": 0.25,
}

# Load quantity rules
_RULES_PATH = Path(__file__).parent.parent.parent / "data" / "quantity_rules.json"
_QUANTITY_RULES = {}
try:
    with open(_RULES_PATH, encoding="utf-8") as f:
        _QUANTITY_RULES = json.load(f)
except Exception:
    pass


def _get_usage_rate(category: str) -> tuple:
    """Returns (usage_rate, buffer) for a category."""
    # Direct match
    rule = _QUANTITY_RULES.get(category)
    if rule:
        # Parse formula to extract rate
        formula = rule.get("formula", "1")
        buffer = 1.0
        if "headcount" in formula:
            # Extract multiplier: e.g. "headcount * 2.0 * 1.10"
            parts = formula.replace("headcount", "").replace("*", "").split()
            try:
                rate = float(parts[0]) if parts else 1.0
                buffer = float(parts[1]) if len(parts) > 1 else 1.0
            except (ValueError, IndexError):
                rate = 1.0
        else:
            rate = 1.0
        return rate, buffer
    return 1.0, 1.0


def compute_quantity(category: str, pack_size: int, headcount: int) -> dict:
    """Compute quantity needed for this category/headcount."""
    pack_size = max(1, pack_size)
    headcount = max(1, headcount)

    rate, buffer = _get_usage_rate(category)
    quantity_needed = math.ceil(headcount * rate * buffer)
    packs_needed = math.ceil(quantity_needed / pack_size)
    units_covered = packs_needed * pack_size
    overage_ratio = units_covered / quantity_needed if quantity_needed > 0 else 1.0

    return {
        "quantity_needed": quantity_needed,
        "packs_needed": packs_needed,
        "units_covered": units_covered,
        "overage_ratio": round(overage_ratio, 3),
        "usage_rate": rate,
        "buffer": buffer,
    }


def compute_score(product: dict, spec: dict, weights: dict) -> dict:
    """Full deterministic scoring with trace."""
    category = product.get("category", "")
    pack_size = product.get("pack_size", 1)
    headcount = spec.get("headcount") or 1
    budget_max = spec.get("budget_max") or 5000
    price = product.get("price", 0)
    rating = product.get("rating", 3.5)
    return_risk = product.get("return_risk", 0.1)
    delivery_eta = product.get("delivery_eta", "3_plus")

    # Quantity calculation
    qty = compute_quantity(category, pack_size, headcount)
    packs_needed = qty["packs_needed"]
    total_cost = price * packs_needed
    overage_ratio = qty["overage_ratio"]

    # Delivery score
    delivery_score = ETA_SCORE_MAP.get(delivery_eta, 0.0)

    # Price score
    budget_ratio = CATEGORY_BUDGET_RATIO.get(category, 0.15)
    budget_allocated = budget_max * budget_ratio
    if budget_allocated > 0:
        price_score = max(0.0, min(1.0, 1.0 - (total_cost / budget_allocated)))
    else:
        price_score = 0.5

    # Quantity score (overage buckets)
    if overage_ratio < 1.0:
        quantity_score = 0.0  # under-coverage
    elif overage_ratio <= 1.25:
        quantity_score = 1.0  # excellent
    elif overage_ratio <= 1.75:
        quantity_score = 0.7  # mild waste
    else:
        quantity_score = 0.4  # significant waste

    # Quality score
    rating_normalized = max(0.0, min(1.0, (rating - 3.5) / 1.5))
    return_risk_score = 1.0 - return_risk
    quality_score = (rating_normalized * 0.6) + (return_risk_score * 0.4)

    # Weighted total
    mission_fit_score = (
        delivery_score * weights.get("delivery", 0.30)
        + price_score * weights.get("price", 0.30)
        + quantity_score * weights.get("quantity", 0.25)
        + quality_score * weights.get("quality", 0.15)
    )

    return {
        "mission_fit_score": round(mission_fit_score, 4),
        "delivery_score": round(delivery_score, 3),
        "price_score": round(price_score, 3),
        "quantity_score": round(quantity_score, 3),
        "quality_score": round(quality_score, 3),
        "quantity_needed": qty["quantity_needed"],
        "packs_needed": packs_needed,
        "total_cost": round(total_cost, 2),
        "overage_ratio": overage_ratio,
        "calculation_trace": {
            "category": category,
            "pack_size": pack_size,
            "headcount": headcount,
            "usage_rate": qty["usage_rate"],
            "buffer": qty["buffer"],
            "units_covered": qty["units_covered"],
            "budget_allocated": round(budget_allocated, 2),
            "rating_normalized": round(rating_normalized, 3),
            "return_risk_score": round(return_risk_score, 3),
            "weights_applied": weights,
        },
    }
