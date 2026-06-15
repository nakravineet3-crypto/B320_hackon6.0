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
    near_tie: bool,
) -> str:
    """Template fallback when LLM unavailable."""
    w_title = winner.get("title", "Product")[:35]
    l_title = loser.get("title", "Product")[:35]
    headcount = mission_context.get("headcount", 1)
    packs = score_winner.get("packs_needed", 1)
    total_cost = score_winner.get("total_cost", 0)

    if near_tie:
        return (
            f"Both {w_title} and {l_title} are strong choices for "
            f"{headcount} guests. {w_title} edges ahead slightly on "
            f"{dominant_factor.replace('_', ' ')} — ₹{total_cost:.0f} "
            f"for {packs} pack(s)."
        )

    factor_explanations = {
        "delivery": f"it arrives via Amazon Now in 20 minutes",
        "price": f"₹{total_cost:.0f} total for {packs} pack(s) is more budget-efficient",
        "quantity": f"{packs} pack(s) covers {headcount} guests with minimal waste",
        "quality": f"it has higher ratings and lower return risk",
    }
    factor_text = factor_explanations.get(
        dominant_factor, f"it scores higher on {dominant_factor}"
    )

    return (
        f"{w_title} is the better pick for {headcount} guests because "
        f"{factor_text}. "
        f"{l_title} falls short on {dominant_factor.replace('_', ' ')} "
        f"for this mission."
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

    # Determine dominant factor (largest score gap)
    dimensions = ["delivery_score", "price_score", "quantity_score", "quality_score"]
    gaps = {}
    for dim in dimensions:
        gaps[dim.replace("_score", "")] = (
            score_winner.get(dim, 0) - score_loser.get(dim, 0)
        )
    dominant_factor = max(gaps, key=lambda k: gaps[k])
    near_tie = confidence == "near_tie"

    # Try LLM
    from app.services.llm.factory import llm_client
    from app.services.llm.prompt_cache import prompt_cache

    if llm_client:
        system = (
            "You are a shopping advisor for Amazon Now India. "
            "Compare two products for a specific mission. "
            "Write exactly 2 short sentences. "
            "Reference actual numbers (₹, pack counts, headcount). "
            "Use the real product titles — never say 'Product A'. "
            "Never say 'overall' or 'generally'. "
            "If near_tie is true, acknowledge both are valid choices."
        )
        user_msg = (
            f"Winner: {winner.get('title', '')}\n"
            f"Loser: {loser.get('title', '')}\n"
            f"Mission: {mission_context.get('occasion_type', 'general')} "
            f"for {mission_context.get('headcount', 1)} people\n"
            f"Deadline: {mission_context.get('deadline_hours', 24)} hours\n"
            f"Budget remaining: ₹{mission_context.get('budget_remaining', 0):.0f}\n"
            f"Winner delivery: {score_winner.get('delivery_score', 0)} "
            f"(eta: {winner.get('delivery_eta', 'unknown')})\n"
            f"Winner price: ₹{score_winner.get('total_cost', 0):.0f} "
            f"for {score_winner.get('packs_needed', 1)} pack(s)\n"
            f"Winner quantity: {score_winner.get('quantity_score', 0)} "
            f"({score_winner.get('packs_needed', 1)} packs, "
            f"{score_winner.get('quantity_needed', 1)} units needed)\n"
            f"Winner quality: {score_winner.get('quality_score', 0)}\n"
            f"Loser delivery: {score_loser.get('delivery_score', 0)}\n"
            f"Loser price: ₹{score_loser.get('total_cost', 0):.0f}\n"
            f"Loser quantity: {score_loser.get('quantity_score', 0)}\n"
            f"Loser quality: {score_loser.get('quality_score', 0)}\n"
            f"Dominant factor: {dominant_factor}\n"
            f"Near tie: {near_tie}\n"
            f"Explain in 2 sentences why {winner.get('title', '')} wins."
        )

        cached = prompt_cache.get(system, user_msg)
        if cached:
            return {
                "explanation": cached,
                "source": "groq_cached",
                "dominant_factor": dominant_factor,
                "near_tie": near_tie,
            }

        try:
            response = await llm_client.complete(
                system_prompt=system,
                user_message=user_msg,
                max_tokens=120,
                temperature=0.3,
            )
            explanation = response.text.strip()
            prompt_cache.set(system, user_msg, explanation)
            return {
                "explanation": explanation,
                "source": "groq",
                "dominant_factor": dominant_factor,
                "near_tie": near_tie,
            }
        except Exception:
            pass

    # Template fallback
    explanation = _template_explanation(
        winner, loser, score_winner, score_loser,
        mission_context, dominant_factor, near_tie,
    )
    return {
        "explanation": explanation,
        "source": "template",
        "dominant_factor": dominant_factor,
        "near_tie": near_tie,
    }
