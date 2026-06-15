"""
Comparison Engine Orchestrator.
Calls all phases in order, builds audit trace.
"""

from uuid import uuid4
from app.services.comparison.classifier import classify_mission
from app.services.comparison.constraints import check_constraints
from app.services.comparison.scorer import compute_score, compute_quantity
from app.services.comparison.evidence import apply_evidence
from app.services.comparison.explainer import generate_explanation


async def evaluate_comparison(request: dict) -> dict:
    """Full comparison pipeline.

    Steps:
    1. Classify mission
    2-3. Check constraints for both products
    4. Handle elimination cases
    5. Score both products
    6. Apply evidence
    7. Determine winner + confidence
    8. Generate explanation
    9. Build audit trace
    """
    product_a = request["product_a"]
    product_b = request["product_b"]
    spec = request.get("mission_spec", {})
    audit_trace_id = str(uuid4())

    # Step 1: Classify mission
    classification = classify_mission(spec)
    weights = classification["weights"]
    safety_tag = classification["safety_tag_needed"]

    # Compute packs needed for budget check
    headcount = spec.get("headcount") or 1
    budget_remaining = spec.get("budget_remaining") or spec.get("budget_max") or 5000

    qty_a = compute_quantity(
        product_a.get("category", ""),
        product_a.get("pack_size", 1),
        headcount,
    )
    qty_b = compute_quantity(
        product_b.get("category", ""),
        product_b.get("pack_size", 1),
        headcount,
    )

    # Steps 2-3: Constraints
    constraints_a = check_constraints(
        product_a, spec, qty_a["packs_needed"], budget_remaining, safety_tag
    )
    constraints_b = check_constraints(
        product_b, spec, qty_b["packs_needed"], budget_remaining, safety_tag
    )

    # Step 4: Handle elimination
    a_passes = constraints_a["passes"]
    b_passes = constraints_b["passes"]

    eliminations = []
    if not a_passes:
        eliminations.append({"product": "a", "reasons": constraints_a["eliminations"]})
    if not b_passes:
        eliminations.append({"product": "b", "reasons": constraints_b["eliminations"]})

    # Both eliminated
    if not a_passes and not b_passes:
        return {
            "winner": None,
            "confidence": None,
            "error": "Both products fail constraints for this mission",
            "score_a": None,
            "score_b": None,
            "dominant_factor": None,
            "near_tie": False,
            "explanation": "Neither product meets the requirements for this mission. Try different products.",
            "explanation_source": "system",
            "comparison_rows": [],
            "eliminations": eliminations,
            "evidence": None,
            "audit_trace_id": audit_trace_id,
            "classification": classification,
        }

    # One eliminated — survivor wins without scoring
    if not a_passes and b_passes:
        return {
            "winner": "b",
            "confidence": "strong",
            "score_a": {"eliminated": True, "reasons": constraints_a["eliminations"]},
            "score_b": None,
            "dominant_factor": "constraint_elimination",
            "near_tie": False,
            "explanation": (
                f"{product_b.get('title', 'Product B')} wins because "
                f"{product_a.get('title', 'Product A')} fails constraints: "
                f"{constraints_a['eliminations'][0]['reason']}"
            ),
            "explanation_source": "system",
            "comparison_rows": [],
            "eliminations": eliminations,
            "evidence": None,
            "audit_trace_id": audit_trace_id,
            "classification": classification,
        }

    if a_passes and not b_passes:
        return {
            "winner": "a",
            "confidence": "strong",
            "score_a": None,
            "score_b": {"eliminated": True, "reasons": constraints_b["eliminations"]},
            "dominant_factor": "constraint_elimination",
            "near_tie": False,
            "explanation": (
                f"{product_a.get('title', 'Product A')} wins because "
                f"{product_b.get('title', 'Product B')} fails constraints: "
                f"{constraints_b['eliminations'][0]['reason']}"
            ),
            "explanation_source": "system",
            "comparison_rows": [],
            "eliminations": eliminations,
            "evidence": None,
            "audit_trace_id": audit_trace_id,
            "classification": classification,
        }

    # Step 5: Score both
    score_a = compute_score(product_a, spec, weights)
    score_b = compute_score(product_b, spec, weights)

    # Step 6: Apply evidence
    occasion_type = spec.get("occasion") or spec.get("occasion_type") or "general"
    evidence_a = apply_evidence(
        score_a["mission_fit_score"], product_a.get("category", ""), occasion_type
    )
    evidence_b = apply_evidence(
        score_b["mission_fit_score"], product_b.get("category", ""), occasion_type
    )

    adj_a = evidence_a["evidence_adjusted_score"]
    adj_b = evidence_b["evidence_adjusted_score"]

    # Step 7: Winner + confidence
    score_gap = abs(adj_a - adj_b)
    if score_gap >= 0.08:
        confidence = "strong"
    elif score_gap >= 0.03:
        confidence = "moderate"
    else:
        confidence = "near_tie"

    winner = "a" if adj_a >= adj_b else "b"
    near_tie = confidence == "near_tie"

    # Step 8: Explanation
    winner_product = product_a if winner == "a" else product_b
    loser_product = product_b if winner == "a" else product_a
    score_winner = score_a if winner == "a" else score_b
    score_loser = score_b if winner == "a" else score_a

    mission_context = {
        "headcount": headcount,
        "deadline_hours": spec.get("deadline_hours", 24),
        "budget_remaining": budget_remaining,
        "occasion_type": occasion_type,
    }

    explanation_result = await generate_explanation(
        winner_product, loser_product,
        score_winner, score_loser,
        mission_context, confidence,
    )

    # Comparison rows for UI
    eta_display = {"now_20min": "⚡ Now · 20 min", "today": "Today", "tomorrow": "Tomorrow", "2_days": "2 days", "3_plus": "3+ days"}
    comparison_rows = [
        {
            "label": "Quantity fit",
            "a_value": f"{score_a['packs_needed']} pack(s) · {qty_a['units_covered']} units",
            "b_value": f"{score_b['packs_needed']} pack(s) · {qty_b['units_covered']} units",
            "winner": "a" if score_a["quantity_score"] >= score_b["quantity_score"] else "b",
        },
        {
            "label": "Total mission cost",
            "a_value": f"₹{score_a['total_cost']:.0f} for {score_a['packs_needed']} pack(s)",
            "b_value": f"₹{score_b['total_cost']:.0f} for {score_b['packs_needed']} pack(s)",
            "winner": "a" if score_a["total_cost"] <= score_b["total_cost"] else "b",
        },
        {
            "label": "Delivery speed",
            "a_value": eta_display.get(product_a.get("delivery_eta", ""), product_a.get("delivery_eta", "Unknown")),
            "b_value": eta_display.get(product_b.get("delivery_eta", ""), product_b.get("delivery_eta", "Unknown")),
            "winner": "a" if score_a["delivery_score"] > score_b["delivery_score"] else "b" if score_b["delivery_score"] > score_a["delivery_score"] else "tie",
        },
    ]

    return {
        "winner": winner,
        "confidence": confidence,
        "score_a": {**score_a, "evidence": evidence_a},
        "score_b": {**score_b, "evidence": evidence_b},
        "dominant_factor": explanation_result["dominant_factor"],
        "near_tie": near_tie,
        "explanation": explanation_result["explanation"],
        "explanation_source": explanation_result["source"],
        "comparison_rows": comparison_rows,
        "eliminations": eliminations,
        "evidence": {
            "a": evidence_a,
            "b": evidence_b,
            "simulated_data": True,
        },
        "audit_trace_id": audit_trace_id,
        "classification": classification,
    }
