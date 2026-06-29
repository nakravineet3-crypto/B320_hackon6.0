"""
LLM explanation layer. Translates score breakdown into language.
The LLM receives FACTS ONLY. Cannot change the winner.
"""


def _template_explanation(
    winner: dict,
    loser: dict,
    score_winner: dict,
    score_loser: dict,
    mission_context: dict,
    dominant_factor: str,
) -> str:
    """Template fallback when LLM unavailable."""
    w_title = winner.get("title", "Product")[:35]
    headcount = mission_context.get("headcount", 1)
    packs = score_winner.get("packs_needed", 1)
    total_cost = score_winner.get("total_cost", 0)
    ppu = score_winner.get("price_per_unit", 0)

    factor_explanations = {
        "delivery": "it arrives via Amazon Now in 20 minutes",
        "price": f"₹{total_cost:.0f} total for {packs} pack(s) is more budget-efficient",
        "price_per_unit": f"₹{ppu:.2f}/unit gives better value than the alternative",
        "quantity": f"{packs} pack(s) covers {headcount} guests with minimal waste",
        "quality": "it has higher ratings and lower return risk",
    }
    factor_text = factor_explanations.get(dominant_factor, f"it scores higher on {dominant_factor.replace('_', ' ')}")

    return (
        f"{w_title} is the better pick for {headcount} {'guests' if headcount > 1 else 'person'} "
        f"because {factor_text}. "
        f"It leads on {dominant_factor.replace('_', ' ')} for this mission."
    )


async def generate_explanation(
    winner: dict,
    loser: dict,
    score_winner: dict,
    score_loser: dict,
    mission_context: dict,
    confidence: str,
) -> dict:
    """Generate 2-sentence explanation. LLM first, template fallback."""

    # Dominant factor — prefer price_per_unit_score if available
    dimensions = ["price_per_unit_score", "delivery_score", "price_score", "quantity_score", "quality_score"]
    gaps = {}
    for dim in dimensions:
        key = dim.replace("_score", "")
        gaps[key] = score_winner.get(dim, 0) - score_loser.get(dim, 0)
    dominant_factor = max(gaps, key=lambda k: gaps[k])

    # Try LLM
    try:
        from app.services.llm.factory import llm_client
        from app.services.llm.prompt_cache import prompt_cache
    except Exception:
        llm_client = None
        prompt_cache = None

    if llm_client:
        system = (
            "You are a shopping advisor for Amazon Now India. "
            "Compare two products for a specific mission. "
            "Write exactly 2 short sentences. "
            "Reference actual numbers (₹ price per unit, pack counts, headcount). "
            "Use the real product titles — never say 'Product A'. "
            "Never say 'overall' or 'generally'. "
            "Be decisive. One product clearly wins."
        )
        user_msg = (
            f"Winner: {winner.get('title', '')}\n"
            f"Loser: {loser.get('title', '')}\n"
            f"Mission: {mission_context.get('occasion_type', 'general')} "
            f"for {mission_context.get('headcount', 1)} people\n"
            f"Deadline: {mission_context.get('deadline_hours', 24)} hours\n"
            f"Budget remaining: ₹{mission_context.get('budget_remaining', 0):.0f}\n"
            f"Winner price/unit: ₹{score_winner.get('price_per_unit', 0):.2f}\n"
            f"Winner total: ₹{score_winner.get('total_cost', 0):.0f} for {score_winner.get('packs_needed', 1)} pack(s)\n"
            f"Winner delivery: {winner.get('delivery_eta', 'unknown')}\n"
            f"Winner quality score: {score_winner.get('quality_score', 0):.2f}\n"
            f"Loser price/unit: ₹{score_loser.get('price_per_unit', 0):.2f}\n"
            f"Loser total: ₹{score_loser.get('total_cost', 0):.0f}\n"
            f"Loser delivery: {loser.get('delivery_eta', 'unknown')}\n"
            f"Loser quality score: {score_loser.get('quality_score', 0):.2f}\n"
            f"Dominant factor: {dominant_factor}\n"
            f"Explain in 2 sentences why {winner.get('title', '')} wins."
        )

        cached = prompt_cache.get(system, user_msg)
        if cached:
            return {"explanation": cached, "source": "groq_cached", "dominant_factor": dominant_factor}

        try:
            response = await llm_client.complete(
                system_prompt=system,
                user_message=user_msg,
                max_tokens=120,
                temperature=0.3,
            )
            explanation = response.text.strip()
            prompt_cache.set(system, user_msg, explanation)
            return {"explanation": explanation, "source": "groq", "dominant_factor": dominant_factor}
        except Exception:
            pass

    explanation = _template_explanation(winner, loser, score_winner, score_loser, mission_context, dominant_factor)
    return {"explanation": explanation, "source": "template", "dominant_factor": dominant_factor}
