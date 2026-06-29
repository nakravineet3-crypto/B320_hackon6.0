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
    # Party / event
    "plates": 0.12,
    "cups": 0.08,
    "napkins": 0.05,
    "balloon_set": 0.15,
    "candles": 0.04,
    "return_gifts": 0.12,
    "decorations": 0.10,
    "party_supplies": 0.15,
    # Grocery / daily
    "snacks": 0.15,
    "snacks_namkeen": 0.15,
    "biscuits_cookies": 0.08,
    "instant_food_noodles": 0.10,
    "dairy_eggs": 0.12,
    "atta_rice_dal": 0.20,
    "cooking_oil_ghee": 0.12,
    "masalas_spices": 0.06,
    "beverages_tea_coffee": 0.10,
    "cold_drinks_water": 0.08,
    "chocolates_sweets": 0.08,
    "dry_fruits_nuts": 0.10,
    # Home setup
    "mattress": 0.30,
    "bedsheet": 0.12,
    "home_furnishing": 0.20,
    "home_electricals": 0.15,
    "kitchen_appliances": 0.20,
    # Personal
    "water_bottle": 0.08,
    "first_aid": 0.06,
    "backpack": 0.25,
    "personal_care": 0.10,
    "health_otc": 0.08,
    "feminine_baby_hygiene": 0.12,
    "baby_food_formula": 0.15,
    # Other
    "household_cleaning": 0.08,
    "stationery_office": 0.08,
    "mobile_accessories": 0.10,
    "pet_food": 0.12,
    "gifting": 0.20,
    "pooja_festive": 0.10,
}

# Bayesian rating smoothing constants
_CATEGORY_AVG_RATING = 4.0
_BAYESIAN_MIN_REVIEWS = 50

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
    rule = _QUANTITY_RULES.get(category)
    if rule:
        formula = rule.get("formula", "1")
        buffer = 1.0
        if "headcount" in formula:
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


def _bayesian_rating(rating: float, review_count: int) -> float:
    """Bayesian-smoothed rating — shrinks toward category avg for low review counts.

    Formula: (v / (v + m)) * item_rating + (m / (v + m)) * category_avg
    where m = minimum confidence threshold (50 reviews).
    """
    v = max(0, review_count)
    m = _BAYESIAN_MIN_REVIEWS
    return (v / (v + m)) * rating + (m / (v + m)) * _CATEGORY_AVG_RATING


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
    """Full deterministic scoring with trace.

    Returns raw price_per_unit so the engine can do pairwise normalization
    after scoring both products.
    """
    category = product.get("category", "")
    pack_size = max(1, product.get("pack_size", 1))
    headcount = spec.get("headcount") or 1
    budget_max = spec.get("budget_max") or 5000
    price = product.get("price", 0)
    rating = product.get("rating", 3.5)
    review_count = product.get("review_count", 0)
    return_risk = product.get("return_risk", 0.1)
    delivery_eta = product.get("delivery_eta", "3_plus")

    # Quantity
    qty = compute_quantity(category, pack_size, headcount)
    packs_needed = qty["packs_needed"]
    total_cost = price * packs_needed
    overage_ratio = qty["overage_ratio"]

    # Price per unit (raw — pairwise normalization done in engine)
    price_per_unit = price / pack_size if pack_size > 0 else price

    # Delivery score
    delivery_score = ETA_SCORE_MAP.get(delivery_eta, 0.0)

    # Budget-relative price score (kept for backward compat, used in weights["price"])
    budget_ratio = CATEGORY_BUDGET_RATIO.get(category, 0.15)
    budget_allocated = budget_max * budget_ratio
    if budget_allocated > 0:
        budget_price_score = max(0.0, min(1.0, 1.0 - (total_cost / budget_allocated)))
    else:
        budget_price_score = 0.5

    # Quantity score (overage buckets)
    if overage_ratio < 1.0:
        quantity_score = 0.0
    elif overage_ratio <= 1.25:
        quantity_score = 1.0
    elif overage_ratio <= 1.75:
        quantity_score = 0.7
    else:
        quantity_score = 0.4

    # Quality score — Bayesian-smoothed rating + return risk
    adjusted_rating = _bayesian_rating(rating, review_count)
    rating_normalized = max(0.0, min(1.0, (adjusted_rating - 3.5) / 1.5))
    return_risk_score = 1.0 - return_risk
    quality_score = (rating_normalized * 0.6) + (return_risk_score * 0.4)

    # Weighted total (price_per_unit_score placeholder = budget_price_score;
    # engine replaces it with pairwise-normalised value after scoring both)
    mission_fit_score = (
        delivery_score * weights.get("delivery", 0.30)
        + budget_price_score * weights.get("price_per_unit", weights.get("price", 0.30))
        + quantity_score * weights.get("quantity", 0.25)
        + quality_score * weights.get("quality", 0.15)
    )

    return {
        "mission_fit_score": round(mission_fit_score, 4),
        "delivery_score": round(delivery_score, 3),
        "price_score": round(budget_price_score, 3),
        "price_per_unit": round(price_per_unit, 4),
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
            "raw_rating": rating,
            "review_count": review_count,
            "adjusted_rating": round(adjusted_rating, 3),
            "rating_normalized": round(rating_normalized, 3),
            "return_risk_score": round(return_risk_score, 3),
            "weights_applied": weights,
        },
    }
