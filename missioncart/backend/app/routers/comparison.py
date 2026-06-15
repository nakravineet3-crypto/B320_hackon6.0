from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from uuid import uuid4
import os

router = APIRouter()


class CompareRequest(BaseModel):
    product_a: dict
    product_b: dict
    mission_goal: str = ""
    occasion_type: str = "general"
    headcount: int = 1
    budget_remaining: float = 0
    user_id: str = "U001"


def deterministic_score(
    product: dict,
    headcount: int,
    budget_remaining: float,
    occasion_type: str,
) -> dict:
    """Score product on 5 dimensions.
    Returns scores and winner flags.
    """
    price = product.get("price", 0)
    pack_size = product.get("pack_size", 1)
    rating = product.get("rating", 3.5)
    now = product.get("amazon_now_eligible", False)
    sponsored = product.get("is_sponsored", False)

    # Quantity fit: how well does pack_size serve headcount
    if headcount > 1:
        units_per_person = pack_size / headcount
        qty_score = min(1.0, units_per_person / 2.0)
    else:
        qty_score = 0.8

    # Price value: lower price relative to budget
    if budget_remaining > 0:
        price_score = max(0, 1.0 - (price / budget_remaining))
    else:
        price_score = 0.5

    # Delivery speed
    delivery_score = 1.0 if now else 0.3

    # Quality
    quality_score = min(1.0, rating / 5.0)

    # Trust (penalize sponsored)
    trust_score = 0.6 if sponsored else 1.0

    # Weighted total
    total = (
        qty_score * 0.30
        + price_score * 0.25
        + delivery_score * 0.20
        + quality_score * 0.15
        + trust_score * 0.10
    )

    return {
        "total": round(total, 3),
        "quantity_fit": round(qty_score, 2),
        "price_value": round(price_score, 2),
        "delivery_speed": round(delivery_score, 2),
        "quality": round(quality_score, 2),
        "trust": round(trust_score, 2),
    }


def generate_comparison_rows(
    product_a: dict,
    product_b: dict,
    score_a: dict,
    score_b: dict,
    headcount: int,
) -> list:
    rows = []

    # Row 1: Quantity fit
    a_units = product_a.get("pack_size", 1)
    b_units = product_b.get("pack_size", 1)
    a_packs_needed = max(1, -(-headcount * 2 // a_units)) if headcount > 1 else 1
    b_packs_needed = max(1, -(-headcount * 2 // b_units)) if headcount > 1 else 1
    a_total_cost = product_a.get("price", 0) * a_packs_needed
    b_total_cost = product_b.get("price", 0) * b_packs_needed

    rows.append({
        "label": "Quantity fit",
        "a_value": f"{a_units} per pack · {a_packs_needed} pack(s) needed",
        "b_value": f"{b_units} per pack · {b_packs_needed} pack(s) needed",
        "winner": "a" if a_total_cost <= b_total_cost else "b",
    })

    # Row 2: Price value
    rows.append({
        "label": "Price value",
        "a_value": f"₹{product_a.get('price', 0)} (₹{a_total_cost} total)",
        "b_value": f"₹{product_b.get('price', 0)} (₹{b_total_cost} total)",
        "winner": "a" if a_total_cost <= b_total_cost else "b",
    })

    # Row 3: Delivery speed
    a_now = product_a.get("amazon_now_eligible", False)
    b_now = product_b.get("amazon_now_eligible", False)
    rows.append({
        "label": "Delivery speed",
        "a_value": "⚡ Now · 20 min" if a_now else "Tomorrow",
        "b_value": "⚡ Now · 20 min" if b_now else "Tomorrow",
        "winner": "a" if a_now and not b_now else "b" if b_now and not a_now else "tie",
    })

    return rows


async def generate_ai_insight(
    product_a: dict,
    product_b: dict,
    score_a: dict,
    score_b: dict,
    winner: str,
    mission_goal: str,
    headcount: int,
    budget_remaining: float,
    occasion_type: str,
) -> str:
    """Generate 2-sentence Groq explanation.
    Falls back to template if Groq fails.
    """
    winner_product = product_a if winner == "a" else product_b
    loser_product = product_b if winner == "a" else product_a

    # Template fallback
    def template_insight():
        w_price = winner_product.get("price", 0)
        w_pack = winner_product.get("pack_size", 1)
        w_now = winner_product.get("amazon_now_eligible", False)
        return (
            f"{winner_product.get('title', 'Option')[:30]} is better for your goal — "
            f"₹{w_price} for {w_pack} units "
            f"{'with Amazon Now delivery' if w_now else ''}. "
            f"It scores higher on quantity fit and price value for "
            f"{headcount} {'guests' if headcount > 1 else 'person'}."
        )

    # Try Groq
    from app.services.llm.factory import llm_client
    from app.services.llm.prompt_cache import prompt_cache

    if not llm_client:
        return template_insight()

    system = (
        "You are a shopping advisor for Amazon Now India. "
        "Compare two products for a specific shopping goal. "
        "Write exactly 2 short sentences. "
        "Be specific about quantities, prices, and the goal. "
        "Never use bullet points. Never say 'Overall'."
    )

    user_msg = (
        f"Goal: {mission_goal}\n"
        f"Occasion: {occasion_type} for {headcount} people\n"
        f"Budget remaining: ₹{budget_remaining:.0f}\n\n"
        f"Product A: {product_a.get('title', '')} — "
        f"₹{product_a.get('price', 0)}, "
        f"{product_a.get('pack_size', 1)} per pack, "
        f"{'Now eligible' if product_a.get('amazon_now_eligible') else 'Standard delivery'}\n"
        f"Product B: {product_b.get('title', '')} — "
        f"₹{product_b.get('price', 0)}, "
        f"{product_b.get('pack_size', 1)} per pack, "
        f"{'Now eligible' if product_b.get('amazon_now_eligible') else 'Standard delivery'}\n\n"
        f"Winner based on scoring: {'Product A' if winner == 'a' else 'Product B'}\n\n"
        f"Explain in 2 sentences why "
        f"{'Product A' if winner == 'a' else 'Product B'} "
        f"is better for this specific goal."
    )

    # Check cache first
    cached = prompt_cache.get(system, user_msg)
    if cached:
        return cached

    try:
        response = await llm_client.complete(
            system_prompt=system,
            user_message=user_msg,
            max_tokens=120,
            temperature=0.3,
        )
        insight = response.text.strip()
        prompt_cache.set(system, user_msg, insight)
        return insight
    except Exception:
        return template_insight()


@router.post("/compare")
async def compare_products(req: CompareRequest):
    """Compare two products for a specific mission goal.
    Returns deterministic scores + AI explanation.
    """
    score_a = deterministic_score(
        req.product_a, req.headcount, req.budget_remaining, req.occasion_type
    )
    score_b = deterministic_score(
        req.product_b, req.headcount, req.budget_remaining, req.occasion_type
    )

    winner = "a" if score_a["total"] >= score_b["total"] else "b"

    rows = generate_comparison_rows(
        req.product_a, req.product_b, score_a, score_b, req.headcount
    )

    insight = await generate_ai_insight(
        req.product_a, req.product_b, score_a, score_b,
        winner, req.mission_goal, req.headcount,
        req.budget_remaining, req.occasion_type,
    )

    # Determine insight source
    from app.services.llm.factory import llm_client
    source = "template"
    if llm_client:
        client_name = type(llm_client).__name__.lower()
        if "groq" in client_name:
            source = "groq"
        elif "anthropic" in client_name:
            source = "anthropic"
        elif "gemini" in client_name:
            source = "gemini"
        else:
            source = "llm"

    return {
        "success": True,
        "data": {
            "winner": winner,
            "score_a": score_a,
            "score_b": score_b,
            "comparison_rows": rows,
            "ai_insight": insight,
            "insight_source": source,
            "recommendation": f"Pick {'A' if winner == 'a' else 'B'}",
        },
        "error": None,
        "request_id": str(uuid4()),
    }


# ── ADVANCED COMPARISON ENGINE ─────────────────────────────


class EvaluateRequest(BaseModel):
    product_a: dict
    product_b: dict
    mission_spec: dict = {}
    user_id: str = "U001"


@router.post("/evaluate")
async def evaluate_comparison_endpoint(req: EvaluateRequest):
    """Advanced comparison with full audit trace.

    Uses the 7-phase comparison engine:
    classify → constraints → score → evidence → explain
    """
    from app.services.comparison.engine import evaluate_comparison

    result = await evaluate_comparison({
        "product_a": req.product_a,
        "product_b": req.product_b,
        "mission_spec": req.mission_spec,
        "user_id": req.user_id,
    })

    return {
        "success": True,
        "data": result,
        "error": result.get("error"),
        "request_id": str(uuid4()),
    }
