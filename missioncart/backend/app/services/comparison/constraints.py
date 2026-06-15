"""
Hard elimination rules. Binary pass/fail before scoring.
"""

ETA_HOURS_MAP = {
    "now_20min": 0.33,
    "today": 8,
    "tomorrow": 24,
    "2_days": 48,
    "3_plus": 99,
}


def check_constraints(
    product: dict,
    spec: dict,
    packs_needed: int,
    budget_remaining: float,
    safety_tag: str | None,
) -> dict:
    """Run 6 elimination rules in order.

    Returns: {passes, eliminations, sponsored_failed_gate}
    """
    eliminations = []
    deadline_hours = spec.get("deadline_hours") or 999
    delivery_eta = product.get("delivery_eta", "3_plus")

    # E1 — Stock
    if not product.get("stock_available", True):
        eliminations.append({"rule": "E1_stock", "reason": "Product out of stock"})

    # E2 — Delivery deadline
    if deadline_hours <= 24:
        now_eligible = product.get("amazon_now_eligible", False)
        if not now_eligible and delivery_eta not in ("now_20min", "today"):
            eliminations.append({
                "rule": "E2_delivery",
                "reason": f"Deadline {deadline_hours}h requires Now/Today delivery. Product ETA: {delivery_eta}",
            })
    elif deadline_hours <= 48:
        if delivery_eta == "3_plus":
            eliminations.append({
                "rule": "E2_delivery",
                "reason": f"Deadline {deadline_hours}h but product arrives 3+ days",
            })

    # E3 — Safety (absolute, no relaxation)
    if safety_tag:
        safety_tags = product.get("safety_tags", [])
        if safety_tag not in safety_tags:
            eliminations.append({
                "rule": "E3_safety",
                "reason": f"Missing required '{safety_tag}' certification. Tags: {safety_tags}",
            })

    # E4 — Rating floor (3.5, relaxed to 3.0 handled by caller)
    rating = product.get("rating", 0)
    if rating < 3.5:
        eliminations.append({
            "rule": "E4_rating",
            "reason": f"Rating {rating}★ below 3.5★ minimum",
        })

    # E5 — Sponsored trust gate
    sponsored_failed_gate = False
    if product.get("sponsored", False):
        if len(eliminations) > 0:
            sponsored_failed_gate = True
            eliminations.append({
                "rule": "E5_sponsored",
                "reason": "Sponsored product failed prior constraints — trust gate triggered",
            })

    # E6 — Budget impossibility
    price = product.get("price", 0)
    total_cost = price * packs_needed
    if budget_remaining > 0 and total_cost > budget_remaining * 1.10:
        eliminations.append({
            "rule": "E6_budget",
            "reason": f"Total cost ₹{total_cost:.0f} exceeds budget remaining ₹{budget_remaining:.0f} × 1.10",
        })

    return {
        "passes": len(eliminations) == 0,
        "eliminations": eliminations,
        "sponsored_failed_gate": sponsored_failed_gate,
    }
