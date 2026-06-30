"""
Comparison Engine Orchestrator.
Calls all phases in order, builds audit trace.
"""

import json
from pathlib import Path
from uuid import uuid4

from app.services.comparison.classifier import classify_mission
from app.services.comparison.constraints import check_constraints
from app.services.comparison.scorer import compute_score, compute_quantity
from app.services.comparison.evidence import apply_evidence
from app.services.comparison.explainer import generate_explanation

# ── Data loaders ─────────────────────────────────────────────────────────────

_DATA_DIR = Path(__file__).parent.parent.parent / "data"

_COHORT_WEIGHTS: dict = {}
try:
    with open(_DATA_DIR / "cohort_weights.json", encoding="utf-8") as _f:
        _COHORT_WEIGHTS = json.load(_f)
except Exception:
    pass

_USER_CLUSTER_MAP: dict = {}
try:
    with open(_DATA_DIR / "user_cluster_map.json", encoding="utf-8") as _f:
        _USER_CLUSTER_MAP = json.load(_f)
except Exception:
    pass


# ── Weight helpers ────────────────────────────────────────────────────────────

def _user_cohort_weights(user_id: str) -> dict:
    """Weighted average of all cohort profiles the user belongs to."""
    user_data = _USER_CLUSTER_MAP.get(user_id)
    if not user_data:
        return _COHORT_WEIGHTS.get("default", {}).get("weights", {})

    memberships: dict = user_data.get("memberships", {})
    if not memberships:
        return _COHORT_WEIGHTS.get("default", {}).get("weights", {})

    total_membership = sum(memberships.values())
    if total_membership == 0:
        return _COHORT_WEIGHTS.get("default", {}).get("weights", {})

    dims = ["price_per_unit", "quantity", "delivery", "quality"]
    blended = {d: 0.0 for d in dims}

    for cohort_id, membership_weight in memberships.items():
        cohort_profile = _COHORT_WEIGHTS.get(cohort_id, {}).get("weights", {})
        norm_w = membership_weight / total_membership
        for d in dims:
            blended[d] += norm_w * cohort_profile.get(d, 0.25)

    return blended


def _blend_weights(mission_weights: dict, cohort_weights: dict, mission_type: str) -> dict:
    """Blend mission and cohort weights.

    Mission confidence is higher for strong signals (deadline/budget critical).
    Cohort confidence is higher for balanced/generic missions.
    """
    if mission_type == "deadline_critical":
        m_conf, u_conf = 0.70, 0.30
    elif mission_type == "budget_critical":
        m_conf, u_conf = 0.55, 0.45
    else:
        m_conf, u_conf = 0.40, 0.60

    dims = ["price_per_unit", "quantity", "delivery", "quality"]

    # Classifier uses "price" key — normalise to "price_per_unit"
    mw = {
        "price_per_unit": mission_weights.get("price", mission_weights.get("price_per_unit", 0.25)),
        "quantity": mission_weights.get("quantity", 0.25),
        "delivery": mission_weights.get("delivery", 0.30),
        "quality": mission_weights.get("quality", 0.20),
    }

    raw = {d: m_conf * mw.get(d, 0.25) + u_conf * cohort_weights.get(d, 0.25) for d in dims}
    total = sum(raw.values())
    return {d: round(raw[d] / total, 4) for d in dims} if total > 0 else raw


def _safe_personalization_reason(user_id: str) -> str:
    """Behaviour-based explanation phrase. Never exposes cohort identity labels."""
    user_data = _USER_CLUSTER_MAP.get(user_id, {})
    memberships = user_data.get("memberships", {})
    if not memberships:
        return "Based on typical value preferences."

    primary = max(memberships, key=memberships.get)
    profile = _COHORT_WEIGHTS.get(primary, {})
    sensitivity = profile.get("price_sensitivity", "medium")
    weights = profile.get("weights", {})
    top_dim = max(weights, key=weights.get) if weights else "price_per_unit"

    messages = {
        ("high", "price_per_unit"): "Based on your usual value-pack preference.",
        ("high", "quantity"): "Based on your bulk-buying pattern.",
        ("low", "quality"): "Based on your preference for higher-rated products.",
        ("low", "delivery"): "Based on your usual focus on product quality over speed.",
        ("medium", "delivery"): "Based on your delivery-first shopping pattern.",
        ("medium", "quantity"): "Based on your quantity-planning preference.",
    }
    return messages.get((sensitivity, top_dim), "Based on your shopping pattern.")


# ── Pairwise price-per-unit normalization ─────────────────────────────────────

def _apply_ppu_normalization(score_a: dict, score_b: dict, ppu_weight: float) -> tuple:
    """Replace placeholder price_score with pairwise-normalised price_per_unit_score.

    best_ppu / ppu_x — lower unit cost scores closer to 1.0.
    Both scores bounded [0, 1]. Rebuilds mission_fit_score accordingly.
    """
    ppu_a = score_a.get("price_per_unit", 1.0)
    ppu_b = score_b.get("price_per_unit", 1.0)

    if ppu_a <= 0 or ppu_b <= 0:
        ppu_score_a, ppu_score_b = 0.5, 0.5
    else:
        best = min(ppu_a, ppu_b)
        ppu_score_a = round(best / ppu_a, 4)
        ppu_score_b = round(best / ppu_b, 4)

    def _rebuild(score: dict, ppu_score: float) -> dict:
        s = dict(score)
        old_contrib = s.get("price_score", 0.5) * ppu_weight
        new_contrib = ppu_score * ppu_weight
        s["price_per_unit_score"] = ppu_score
        s["mission_fit_score"] = round(s["mission_fit_score"] - old_contrib + new_contrib, 4)
        return s

    return _rebuild(score_a, ppu_score_a), _rebuild(score_b, ppu_score_b)


# ── Tiebreaker cascade ────────────────────────────────────────────────────────

def _tiebreaker(
    score_a: dict, score_b: dict,
    product_a: dict, product_b: dict,
    mission_type: str, user_id: str,
) -> tuple:
    """Deterministic cascade when gap < 0.03. Always returns (winner, reason).

    Order:
      TB1 — Mission constraint (deadline → faster delivery wins)
      TB2 — Cohort price sensitivity (high→price, low→quality)
      TB3 — Price per unit (absolute)
      TB4 — Return risk (lower is better)
      TB5 — Quality score
      TB7 — Total cost (last resort, always decisive)
    """
    # TB1 — delivery if deadline-critical
    if mission_type == "deadline_critical":
        if score_a["delivery_score"] > score_b["delivery_score"]:
            return "a", "faster delivery (deadline-critical mission)"
        if score_b["delivery_score"] > score_a["delivery_score"]:
            return "b", "faster delivery (deadline-critical mission)"

    # TB2 — cohort price sensitivity
    user_data = _USER_CLUSTER_MAP.get(user_id, {})
    memberships = user_data.get("memberships", {})
    primary_cohort = max(memberships, key=memberships.get) if memberships else None
    sensitivity = _COHORT_WEIGHTS.get(primary_cohort or "", {}).get("price_sensitivity", "medium")

    if sensitivity == "high":
        ppu_sa = score_a.get("price_per_unit_score", 0.5)
        ppu_sb = score_b.get("price_per_unit_score", 0.5)
        if abs(ppu_sa - ppu_sb) > 0.01:
            return ("a" if ppu_sa > ppu_sb else "b"), "lower unit cost (matches value-pack preference)"
    elif sensitivity == "low":
        if abs(score_a["quality_score"] - score_b["quality_score"]) > 0.01:
            return ("a" if score_a["quality_score"] > score_b["quality_score"] else "b"), "higher quality (matches premium preference)"

    # TB3 — price per unit
    ppu_a = score_a.get("price_per_unit_score", 0.5)
    ppu_b = score_b.get("price_per_unit_score", 0.5)
    if abs(ppu_a - ppu_b) > 0.02:
        return ("a" if ppu_a > ppu_b else "b"), "lower price per unit"

    # TB4 — return risk
    rr_a = product_a.get("return_risk", 0.1)
    rr_b = product_b.get("return_risk", 0.1)
    if abs(rr_a - rr_b) > 0.02:
        return ("a" if rr_a < rr_b else "b"), "lower return risk"

    # TB5 — quality
    if abs(score_a["quality_score"] - score_b["quality_score"]) > 0.01:
        return ("a" if score_a["quality_score"] > score_b["quality_score"] else "b"), "higher quality"

    # TB7 — total cost, always decisive
    return ("a" if score_a["total_cost"] <= score_b["total_cost"] else "b"), "lower total cost"


# ── Main engine ───────────────────────────────────────────────────────────────

async def evaluate_comparison(request: dict) -> dict:
    """Full comparison pipeline.

    Phases:
      0  Context — cohort membership, blended weights
      1  Quantities for constraint check
      2  Hard constraint elimination
      3  Score both products
      4  Pairwise price-per-unit normalisation
      5  Community evidence boost
      6  Winner determination + tiebreaker cascade
      7  Substitution check (both score < 0.45)
      8  LLM explanation
      9  Build response with decision_type
    """
    product_a = request["product_a"]
    product_b = request["product_b"]
    spec = request.get("mission_spec", {})
    user_id = request.get("user_id", "default")
    audit_trace_id = str(uuid4())

    # Phase 0 — context
    classification = classify_mission(spec)
    mission_weights = classification["weights"]
    mission_type = classification["mission_type"]
    safety_tag = classification["safety_tag_needed"]

    cohort_weights = _user_cohort_weights(user_id)
    final_weights = _blend_weights(mission_weights, cohort_weights, mission_type)
    safe_reason = _safe_personalization_reason(user_id)

    headcount = spec.get("headcount") or 1
    budget_remaining = spec.get("budget_remaining") or spec.get("budget_max") or 5000

    # Phase 1 — quantities
    qty_a = compute_quantity(product_a.get("category", ""), product_a.get("pack_size", 1), headcount)
    qty_b = compute_quantity(product_b.get("category", ""), product_b.get("pack_size", 1), headcount)

    # Phase 2 — hard constraints
    constraints_a = check_constraints(product_a, spec, qty_a["packs_needed"], budget_remaining, safety_tag)
    constraints_b = check_constraints(product_b, spec, qty_b["packs_needed"], budget_remaining, safety_tag)

    a_passes = constraints_a["passes"]
    b_passes = constraints_b["passes"]

    eliminations = []
    if not a_passes:
        eliminations.append({"product": "a", "reasons": constraints_a["eliminations"]})
    if not b_passes:
        eliminations.append({"product": "b", "reasons": constraints_b["eliminations"]})

    def _suppressed_response(reason: str) -> dict:
        return {
            "decision_type": "comparison_suppressed",
            "winner": None,
            "confidence": None,
            "headline": "Neither product meets the requirements",
            "reason": reason,
            "safe_personalization_reason": safe_reason,
            "score_a": None,
            "score_b": None,
            "dominant_factor": None,
            "explanation": reason + " Try different products.",
            "explanation_source": "system",
            "comparison_rows": [],
            "eliminations": eliminations,
            "substitute": None,
            "audit_trace_id": audit_trace_id,
            "classification": classification,
            "weights_used": final_weights,
            "simulated_data": True,
        }

    if not a_passes and not b_passes:
        return _suppressed_response("Both options fail constraints for this mission.")

    def _constraint_winner(winner: str, winner_product: dict, loser_product: dict, loser_constraints: dict) -> dict:
        reason = loser_constraints["eliminations"][0]["reason"]
        w_title = winner_product.get("title", f"Product {winner.upper()}")[:40]
        return {
            "decision_type": "winner_selected",
            "winner": winner,
            "confidence": "strong",
            "headline": f"{w_title} is the pick",
            "reason": f"Other option fails: {reason}",
            "safe_personalization_reason": safe_reason,
            "score_a": None if winner == "b" else {},
            "score_b": None if winner == "a" else {},
            "dominant_factor": "constraint_elimination",
            "explanation": f"{w_title} wins because the other option fails: {reason}",
            "explanation_source": "system",
            "comparison_rows": [],
            "eliminations": eliminations,
            "substitute": None,
            "audit_trace_id": audit_trace_id,
            "classification": classification,
            "weights_used": final_weights,
            "simulated_data": True,
        }

    if not a_passes:
        return _constraint_winner("b", product_b, product_a, constraints_a)
    if not b_passes:
        return _constraint_winner("a", product_a, product_b, constraints_b)

    # Phase 3 — score
    score_a = compute_score(product_a, spec, final_weights)
    score_b = compute_score(product_b, spec, final_weights)

    # Phase 4 — pairwise ppu normalisation
    ppu_weight = final_weights.get("price_per_unit", 0.25)
    score_a, score_b = _apply_ppu_normalization(score_a, score_b, ppu_weight)

    # Phase 5 — evidence
    occasion_type = spec.get("occasion") or spec.get("occasion_type") or "general"
    evidence_a = apply_evidence(score_a["mission_fit_score"], product_a.get("category", ""), occasion_type)
    evidence_b = apply_evidence(score_b["mission_fit_score"], product_b.get("category", ""), occasion_type)

    adj_a = evidence_a["evidence_adjusted_score"]
    adj_b = evidence_b["evidence_adjusted_score"]

    # Phase 6 — winner
    score_gap = abs(adj_a - adj_b)
    tiebreak_reason = None

    if score_gap >= 0.08:
        confidence = "clear_winner"
        winner = "a" if adj_a >= adj_b else "b"
    elif score_gap >= 0.03:
        confidence = "slight_edge"
        winner = "a" if adj_a >= adj_b else "b"
    else:
        winner, tiebreak_reason = _tiebreaker(
            score_a, score_b, product_a, product_b, mission_type, user_id
        )
        confidence = "slight_edge"

    # Phase 7 — substitution check
    max_score = max(adj_a, adj_b)
    decision_type = "winner_selected"
    substitution = None
    if max_score < 0.45:
        decision_type = "substitution_suggested"
        substitution = {
            "reason": "Both options score below the quality threshold for this mission.",
            "action": "suggest_better",
            "max_score_seen": round(max_score, 3),
        }

    # Phase 8 — explanation
    winner_product = product_a if winner == "a" else product_b
    loser_product = product_b if winner == "a" else product_a
    score_winner = score_a if winner == "a" else score_b
    score_loser = score_b if winner == "a" else score_a

    explanation_result = await generate_explanation(
        winner_product, loser_product,
        score_winner, score_loser,
        {"headcount": headcount, "deadline_hours": spec.get("deadline_hours", 24),
         "budget_remaining": budget_remaining, "occasion_type": occasion_type},
        confidence,
    )

    dominant = explanation_result["dominant_factor"]
    if tiebreak_reason:
        dominant = tiebreak_reason.split("(")[0].strip().replace(" ", "_")

    # Comparison rows
    eta_display = {
        "now_20min": "⚡ 20 min", "today": "Today",
        "tomorrow": "Tomorrow", "2_days": "2 days", "3_plus": "3+ days",
    }
    ppu_a = score_a.get("price_per_unit", 0)
    ppu_b = score_b.get("price_per_unit", 0)
    comparison_rows = [
        {
            "label": "Price per unit",
            "a_value": f"₹{ppu_a:.2f}/unit",
            "b_value": f"₹{ppu_b:.2f}/unit",
            "winner": "a" if score_a.get("price_per_unit_score", 0.5) >= score_b.get("price_per_unit_score", 0.5) else "b",
        },
        {
            "label": "Mission total cost",
            "a_value": f"₹{score_a['total_cost']:.0f} for {score_a['packs_needed']} pack(s)",
            "b_value": f"₹{score_b['total_cost']:.0f} for {score_b['packs_needed']} pack(s)",
            "winner": "a" if score_a["total_cost"] <= score_b["total_cost"] else "b",
        },
        {
            "label": "Delivery",
            "a_value": eta_display.get(product_a.get("delivery_eta", ""), "Unknown"),
            "b_value": eta_display.get(product_b.get("delivery_eta", ""), "Unknown"),
            "winner": (
                "a" if score_a["delivery_score"] > score_b["delivery_score"]
                else "b" if score_b["delivery_score"] > score_a["delivery_score"]
                else "tie"
            ),
        },
        {
            "label": "Quality",
            "a_value": f"{product_a.get('rating', 0)}★ · {product_a.get('review_count', 0):,} reviews",
            "b_value": f"{product_b.get('rating', 0)}★ · {product_b.get('review_count', 0):,} reviews",
            "winner": "a" if score_a["quality_score"] >= score_b["quality_score"] else "b",
        },
    ]

    winner_title = winner_product.get("title", "Product")[:40]
    headline = (
        f"{winner_title} is the better pick"
        if decision_type == "winner_selected"
        else "Neither option is ideal for your goal"
    )

    return {
        "decision_type": decision_type,
        "winner": winner if decision_type == "winner_selected" else None,
        "confidence": confidence,
        "headline": headline,
        "reason": tiebreak_reason or dominant.replace("_", " "),
        "safe_personalization_reason": safe_reason,
        "dominant_factor": dominant,
        "score_a": {**score_a, "evidence": evidence_a},
        "score_b": {**score_b, "evidence": evidence_b},
        "explanation": explanation_result["explanation"],
        "explanation_source": explanation_result["source"],
        "comparison_rows": comparison_rows,
        "eliminations": eliminations,
        "substitute": substitution,
        "audit_trace_id": audit_trace_id,
        "classification": classification,
        "weights_used": final_weights,
        "simulated_data": True,
    }
