"""
Mission type classification for comparison engine.
Determines which weight matrix drives scoring.
"""

WEIGHT_MATRIX = {
    "deadline_critical": {"delivery": 0.45, "price": 0.20, "quantity": 0.25, "quality": 0.10},
    "budget_critical": {"delivery": 0.20, "price": 0.45, "quantity": 0.25, "quality": 0.10},
    "balanced": {"delivery": 0.30, "price": 0.30, "quantity": 0.25, "quality": 0.15},
}

SAFETY_CONTEXTS = {"child_safe", "baby_safe", "pet_safe"}


def classify_mission(spec: dict) -> dict:
    """Classify mission type from spec. Drives weight selection.

    Precedence:
    1. Safety is always a gate (filter), not a type
    2. deadline_hours <= 18 → deadline_critical
    3. budget_remaining < budget_max × 0.20 → budget_critical
    4. Otherwise → balanced
    """
    safety_context = spec.get("safety_context") or "general"
    safety_required = safety_context in SAFETY_CONTEXTS
    safety_tag_needed = safety_context if safety_required else None

    deadline_hours = spec.get("deadline_hours") or 999
    budget_max = spec.get("budget_max") or 0
    budget_remaining = spec.get("budget_remaining") or budget_max

    # Classification by precedence
    if deadline_hours <= 18:
        mission_type = "deadline_critical"
    elif budget_max > 0 and budget_remaining < (budget_max * 0.20):
        mission_type = "budget_critical"
    else:
        mission_type = "balanced"

    return {
        "mission_type": mission_type,
        "weights": WEIGHT_MATRIX[mission_type],
        "safety_required": safety_required,
        "safety_tag_needed": safety_tag_needed,
    }
