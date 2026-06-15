import math
from typing import List, Tuple

ETA_DAYS = {
    "now_20min": 0,
    "today": 0,
    "tomorrow": 1,
    "2_days": 2,
    "3_plus": 99,
}


def check_all_constraints(
    product: dict,
    spec,
    remaining_budget: float,
    packs_needed: int,
    cart_categories: List[str],
) -> Tuple[bool, List[str]]:
    """8 constraint checks. Returns (passes, failed_checks).
    All 8 must pass for sponsored products.
    Checks 1-7 for non-sponsored.
    """
    failures = []
    price = product.get("price", 0) if isinstance(product, dict) else getattr(product, "price", 0)
    cost = price * packs_needed

    # CHECK 1: Budget headroom
    if cost > remaining_budget * 1.1:
        failures.append(
            f"budget: ₹{cost:.0f} exceeds ₹{remaining_budget:.0f} remaining"
        )

    # CHECK 2: Delivery deadline
    deadline_hours = getattr(spec, "deadline_hours", None)
    if deadline_hours:
        eta_str = product.get("delivery_eta", "3_plus") if isinstance(product, dict) else getattr(product, "delivery_eta", "3_plus")
        eta = ETA_DAYS.get(eta_str, 99)
        deadline_days = math.ceil(deadline_hours / 24)
        if eta > deadline_days:
            failures.append(
                f"delivery: arrives in {eta} days, need by day {deadline_days}"
            )

    # CHECK 3: Amazon Now eligibility
    if deadline_hours and deadline_hours <= 24:
        now_eligible = product.get("amazon_now_eligible", False) if isinstance(product, dict) else getattr(product, "amazon_now_eligible", False)
        if not now_eligible:
            failures.append("amazon_now: not eligible for same-day delivery")

    # CHECK 4: Compatibility
    incompatible = product.get("incompatible_with", []) if isinstance(product, dict) else getattr(product, "incompatible_with", [])
    conflicts = [c for c in incompatible if c in cart_categories]
    if conflicts:
        failures.append(
            f"compatibility: conflicts with {', '.join(conflicts)}"
        )

    # CHECK 5: Return risk
    return_risk = product.get("return_risk", 0) if isinstance(product, dict) else getattr(product, "return_risk", 0)
    threshold = 0.40 if remaining_budget < 500 else 0.30
    if return_risk > threshold:
        failures.append(
            f"return_risk: {return_risk:.0%} exceeds {threshold:.0%} limit"
        )

    # CHECK 6: Quality floor
    rating = product.get("rating", 0) if isinstance(product, dict) else getattr(product, "rating", 0)
    if rating < 3.5:
        failures.append(f"quality: {rating}★ below 3.5★ minimum")

    # CHECK 7: Safety constraints
    safety = getattr(spec, "safety_context", None)
    if safety and safety != "general":
        safety_tags = product.get("safety_tags", []) if isinstance(product, dict) else getattr(product, "safety_tags", [])
        if safety not in safety_tags:
            failures.append(f"safety: missing {safety} certification")

    # CHECK 8: Sponsored validity
    sponsored = product.get("sponsored", False) if isinstance(product, dict) else getattr(product, "sponsored", False)
    if sponsored and len(failures) > 0:
        failures.append("sponsored_blocked: failed constraint checks")

    return len(failures) == 0, failures


def relax_and_recheck(
    product: dict,
    spec,
    remaining_budget: float,
    packs_needed: int,
    cart_categories: List[str],
) -> Tuple[bool, List[str]]:
    """Relaxed constraints for when strict checks find no products."""
    failures = []
    price = product.get("price", 0) if isinstance(product, dict) else getattr(product, "price", 0)
    cost = price * packs_needed

    # Relaxed budget: 1.3x instead of 1.1x
    if cost > remaining_budget * 1.3:
        failures.append("budget: too expensive even with relaxation")

    # Relaxed quality: 3.0 instead of 3.5
    rating = product.get("rating", 0) if isinstance(product, dict) else getattr(product, "rating", 0)
    if rating < 3.0:
        failures.append("quality: below 3.0 minimum")

    # Keep safety and sponsored checks strict
    safety = getattr(spec, "safety_context", None)
    if safety and safety != "general":
        safety_tags = product.get("safety_tags", []) if isinstance(product, dict) else getattr(product, "safety_tags", [])
        if safety not in safety_tags:
            failures.append(f"safety: missing {safety}")

    sponsored = product.get("sponsored", False) if isinstance(product, dict) else getattr(product, "sponsored", False)
    if sponsored and len(failures) > 0:
        failures.append("sponsored_blocked")

    return len(failures) == 0, failures
