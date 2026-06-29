"""
community.py — Community feature router
========================================
All endpoints are deterministic mathematics. No LLM calls.
All responses carry simulated_data: true.

Scale notes are in community_engine.py and build_community_data.py.
"""

import json
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Body, Query
from pydantic import BaseModel
from uuid import uuid4
from typing import List, Optional

from app.services.community_engine import community_engine, get_group_products as engine_get_group_products

# ---------------------------------------------------------------------------
# Path to the goal pages data file
# ---------------------------------------------------------------------------
_GOAL_PAGES_PATH = Path(__file__).parent.parent / "data" / "community_goal_pages.json"


def _load_goal_pages() -> list[dict]:
    """Load community goal pages from JSON. Returns empty list on error."""
    try:
        with open(_GOAL_PAGES_PATH) as f:
            data = json.load(f)
        return data.get("goal_pages", [])
    except Exception:
        return []


def _save_goal_pages(pages: list[dict]) -> None:
    """Persist goal pages back to JSON."""
    with open(_GOAL_PAGES_PATH, "w") as f:
        json.dump({"goal_pages": pages}, f, indent=2)


def _days_until(target_date_str: str) -> int:
    """Return calendar days until target_date_str (YYYY-MM-DD). Negative = past."""
    try:
        target = date.fromisoformat(target_date_str)
        return (target - date.today()).days
    except Exception:
        return 0


def _compute_coverage(items: list[dict]) -> int:
    """Recompute coverage percentage from claimed items."""
    if not items:
        return 0
    claimed = sum(1 for it in items if it.get("status") == "claimed")
    return round(claimed * 100 / len(items))


# ---------------------------------------------------------------------------
# Pydantic models for POST /api/community/goals
# ---------------------------------------------------------------------------
class GoalPageCreateRequest(BaseModel):
    title: str
    occasion_type: str
    occasion_emoji: Optional[str] = "🎉"
    target_date: str                     # YYYY-MM-DD
    budget_total: int
    participant_names: List[str] = []
    created_by: str = "U001"

router = APIRouter()


def _get_identity_group_asins(
    group_id: str,
    catalog_map: dict,
    products_list: list,
    limit: int = 12,
) -> list[str]:
    """
    Return top-rated, non-sponsored catalog ASINs for a given identity group.
    Filters by category, sorts by rating descending, returns up to `limit` ASINs.
    Falls back to an empty list when the group_id is unknown or no products match.
    """
    GROUP_CATEGORIES: dict[str, list[str]] = {
        "office_gym_dad": ["outdoor_sports", "stationery", "household", "snacks", "beverages"],
        "jee_student": ["stationery", "snacks", "beverages", "personal_care"],
        "college_girl": ["personal_care", "home_decor", "snacks", "stationery"],
        "home_chef": ["food_beverages", "spices", "condiments", "household", "storage"],
    }
    cats = GROUP_CATEGORIES.get(group_id, [])
    if not cats:
        return []
    candidates = [
        p for p in products_list
        if p.get("category") in cats
        and not p.get("sponsored", False)
        and p.get("stock_available", True)
    ]
    candidates.sort(key=lambda x: x.get("rating", 0), reverse=True)
    return [p["asin"] for p in candidates[:limit]]


def _envelope(data, error=None) -> dict:
    """Standard API response envelope used across all MissionCart routes."""
    return {
        "success":        error is None,
        "data":           data,
        "error":          error,
        "request_id":     str(uuid4()),
        "simulated_data": True,
    }


# ── GET /api/community/my-group ───────────────────────────────────────────────
@router.get("/my-group")
def my_group(user_id: str = Query(..., description="User ID, e.g. U001")):
    """
    Return the user's behavioral cohort with member-specific context.

    Response includes:
      - group_name, group_size, your_rank
      - top_products from cohort
      - occasion_specialty (dominant occasion type in this cluster)
      - member_activity count for today
    """
    result = community_engine.get_user_community(user_id)
    if not result:
        return _envelope(
            None,
            error=f"No community data found for user {user_id}"
        )
    return _envelope(result)


# ── GET /api/community/groups ─────────────────────────────────────────────────
@router.get("/groups")
def list_groups():
    """
    Return all community groups with activity indicators.

    Response is a list of groups including:
      - group_id, group_name, member_count
      - top_occasion, active_right_now (deterministic simulation)
    """
    groups = community_engine.get_all_groups()
    return _envelope(groups)


# ── GET /api/community/trending ───────────────────────────────────────────────
@router.get("/trending")
def trending(
    user_id: str = Query(..., description="User ID"),
    occasion: Optional[str] = Query(None, description="Filter by occasion type"),
    limit: int = Query(10, ge=1, le=30),
):
    """
    Return trending items for the user's community group.

    Each item includes:
      - asin, title, category
      - adoption_rate_in_community: how often cohort buys this
      - community_adoption_vs_global: cohort rate / global rate (momentum signal)
    """
    items = community_engine.get_community_trending(
        user_id=user_id, occasion=occasion, limit=limit
    )
    return _envelope({
        "user_id": user_id,
        "occasion_filter": occasion,
        "trending_items": items,
        "count": len(items),
    })


# ── GET /api/community/activity ───────────────────────────────────────────────
@router.get("/activity")
def activity_feed(
    user_id: str = Query(..., description="User ID"),
    limit: int = Query(5, ge=1, le=20),
):
    """
    Return a simulated real-time community activity feed.

    Feed items show what people like the user are doing right now:
      - "42 people in Bangalore are planning Diwali this week"
      - "12 members of your cohort approved morning reorder today"

    The feed is deterministic (seeded by user_id + today's date) so it's
    stable within a day but changes daily — giving a "live" feeling without
    real-time infrastructure.

    Scale note: At production scale replace with Kafka + Redis sorted set
    reads (ZREVRANGE user:city:occasion 0 N).
    """
    items = community_engine.get_activity_feed(user_id=user_id, limit=limit)
    return _envelope({
        "user_id": user_id,
        "feed": items,
        "count": len(items),
        "simulated_realtime": True,
    })


# ── GET /api/community/occasion-insights/{occasion_type} ─────────────────────
@router.get("/occasion-insights/{occasion_type}")
def occasion_insights(
    occasion_type: str,
    city: Optional[str] = Query(None, description="City for local comparison"),
):
    """
    Return rich ML-computed insights for a given occasion type.

    Includes:
      - sessions_analyzed: number of community sessions powering this insight
      - top_items: categories with adoption_rate across sessions
      - coverage_gaps: items frequently missed
      - avg_budget, avg_headcount, success_rate
      - city_comparison (if city param provided)
    """
    insight = community_engine.get_occasion_insights(
        occasion_type=occasion_type, city=city
    )
    if not insight:
        return _envelope(
            None,
            error=f"No insights found for occasion type '{occasion_type}'"
        )
    return _envelope(insight)


# ── GET /api/community/coverage-gaps/{occasion_type} ─────────────────────────
@router.get("/coverage-gaps/{occasion_type}")
def coverage_gaps(occasion_type: str):
    """
    Return items that community data shows are frequently missed for this occasion.

    Each gap item includes:
      - category, asin, title
      - miss_rate: fraction of sessions that skipped this item
      - why_matters: human-readable explanation of the gap's impact

    This powers the "Don't forget..." nudge in the UI.
    """
    gaps = community_engine.get_coverage_gaps(occasion_type=occasion_type)
    return _envelope({
        "occasion_type": occasion_type,
        "gaps": gaps,
        "count": len(gaps),
    })


# ── GET /api/community/groups/{group_id}/products ─────────────────────────────
@router.get("/groups/{group_id}/products")
async def get_group_products(group_id: str, limit: int = 12):
    """
    Return curated non-sponsored products for a given identity group.

    For the four identity groups (office_gym_dad, jee_student, college_girl,
    home_chef) the ASIN list is resolved dynamically from the real catalog by
    category. For community cluster IDs that appear in community_groups.json
    the top_categories drive catalog lookup. Falls back to non-sponsored
    items if nothing matches.
    """
    # Category → color mapping for image placeholder
    CATEGORY_COLORS: dict[str, str] = {
        "protein_supplements": "#4A90D9", "electronics": "#5C6BC0",
        "kitchen": "#E57373", "books": "#66BB6A", "sports": "#26A69A",
        "clothing": "#AB47BC", "food_beverages": "#FFA726", "home_decor": "#8D6E63",
        "personal_care": "#EC407A", "stationery": "#42A5F5", "plates": "#FF7043",
        "balloon_set": "#7E57C2", "candles": "#FFCA28", "decorations": "#26C6DA",
        "water_bottle": "#29B6F6", "backpack": "#66BB6A", "first_aid_kit": "#EF5350",
        "cups": "#FF8A65", "napkins": "#A5D6A7", "tablecloth": "#CE93D8",
        "return_gifts": "#80CBC4", "banner": "#FFD54F", "cake_knife": "#B0BEC5",
        "disposable_cups": "#FF8A65", "cupcake_liners": "#F48FB1",
        "balloon_pump": "#80DEEA", "decoration_streamers": "#FFCC02",
        "disposable_spoons": "#CFD8DC", "disposable_forks": "#CFD8DC",
    }

    try:
        catalog_path = Path(__file__).parent.parent / "data" / "catalog.json"
        with open(catalog_path) as f:
            catalog_data = json.load(f)

        products_list: list[dict] = (
            catalog_data.get("products", catalog_data)
            if isinstance(catalog_data, dict)
            else catalog_data
        )
        catalog_map: dict[str, dict] = {
            p.get("asin", p.get("product_id", "")): p for p in products_list
        }

        # Dynamically resolve identity group ASINs from real catalog
        asin_list = _get_identity_group_asins(group_id, catalog_map, products_list, limit) or None

        # Bug 5 wire-in: for community cluster IDs (grp_* old format, or bare
        # identity group IDs like office_gym_dad, jee_student, etc.) prefer the
        # engine's lift-ranked affinity results over the raw top_categories scan.
        # engine_get_group_products() already filters sponsored=False.
        _is_cluster_id = (
            group_id.startswith("grp_")
            or group_id in ("office_gym_dad", "jee_student", "college_girl", "home_chef")
        )
        if not asin_list and _is_cluster_id:
            engine_products = engine_get_group_products(group_id, limit=limit)
            if engine_products:
                result_products_from_engine = []
                for p in engine_products:
                    asin = p.get("asin", "")
                    # Resolve full catalog entry if available; fall back to what engine gave
                    full_p = catalog_map.get(asin, p)
                    if full_p.get("sponsored", False):
                        continue
                    cat = full_p.get("category", "")
                    result_products_from_engine.append({
                        "asin":                asin,
                        "title":               full_p.get("title", asin),
                        "price_inr":           full_p.get("price_inr", full_p.get("price", 0)),
                        "rating":              full_p.get("rating", 4.0),
                        "category":            cat,
                        "amazon_now_eligible": full_p.get("amazon_now_eligible", False),
                        "image_placeholder":   CATEGORY_COLORS.get(cat, "#9E9E9E"),
                        "adoption_copy":       p.get("adoption_copy", ""),
                        "lift":                p.get("lift", 1.0),
                    })
                if result_products_from_engine:
                    return {
                        "success":        True,
                        "data":           {"products": result_products_from_engine, "group_id": group_id},
                        "error":          None,
                        "request_id":     str(uuid4()),
                        "simulated_data": True,
                    }

        if not asin_list:
            # Fall back to community_groups.json top_categories
            groups_path = Path(__file__).parent.parent / "data" / "community_groups.json"
            with open(groups_path) as f:
                groups_raw = json.load(f)

            groups: list[dict] = (
                groups_raw.get("groups", groups_raw)
                if isinstance(groups_raw, dict)
                else groups_raw
            )
            group_record: dict | None = None
            for g in groups:
                if g.get("group_id") == group_id or g.get("id") == group_id:
                    group_record = g
                    break

            if group_record:
                top_cats = [
                    tc["category"]
                    for tc in group_record.get("top_categories", [])
                ]
                asin_list = [
                    p["asin"]
                    for p in products_list
                    if p.get("category") in top_cats and not p.get("sponsored", False)
                ][:limit]
            else:
                # No match at all — return first non-sponsored items
                asin_list = [
                    p["asin"]
                    for p in products_list
                    if not p.get("sponsored", False)
                ][:limit]

        result_products = []
        for asin in asin_list[:limit]:
            p = catalog_map.get(asin)
            if not p:
                continue
            if p.get("sponsored", False):
                continue
            cat = p.get("category", "")
            result_products.append({
                "asin": asin,
                "title": p.get("title", p.get("name", asin)),
                "price_inr": p.get("price_inr", p.get("price", 0)),
                "rating": p.get("rating", p.get("quality_score", 4.0)),
                "category": cat,
                "amazon_now_eligible": p.get("amazon_now_eligible", False),
                "image_placeholder": CATEGORY_COLORS.get(cat, "#9E9E9E"),
            })

        # If hardcoded ASINs didn't resolve (they're demo stubs not in catalog),
        # fall through to non-sponsored catalog items for a non-empty grid.
        if not result_products:
            fallback_items = [
                p for p in products_list if not p.get("sponsored", False)
            ][:limit]
            for p in fallback_items:
                cat = p.get("category", "")
                result_products.append({
                    "asin": p.get("asin", ""),
                    "title": p.get("title", p.get("name", "")),
                    "price_inr": p.get("price_inr", p.get("price", 0)),
                    "rating": p.get("rating", p.get("quality_score", 4.0)),
                    "category": cat,
                    "amazon_now_eligible": p.get("amazon_now_eligible", False),
                    "image_placeholder": CATEGORY_COLORS.get(cat, "#9E9E9E"),
                })

        group_display_names: dict[str, str] = {
            "office_gym_dad": "Office Gym Dad",
            "jee_student": "JEE Student",
            "college_girl": "College Girl",
            "home_chef": "Home Chef",
        }

        return {
            "group_id": group_id,
            "group_name": group_display_names.get(group_id, group_id),
            "product_count": len(result_products),
            "products": result_products[:limit],
        }
    except Exception:
        return {
            "group_id": group_id,
            "group_name": group_id,
            "product_count": 0,
            "products": [],
        }


# ── GET /api/community/goals ──────────────────────────────────────────────────
@router.get("/goals")
def list_goal_pages():
    """
    Return all active community goal pages with summary fields for the
    Discover tab horizontal scroll section.

    Each summary includes:
      - goal_id, title, occasion_type, occasion_emoji
      - participant_count
      - items_claimed / items_total (for the progress bar)
      - coverage_pct
      - days_until (derived from target_date vs today)
      - community_signal
    """
    pages = _load_goal_pages()
    summaries = []
    for page in pages:
        items = page.get("items", [])
        claimed = sum(1 for it in items if it.get("status") == "claimed")
        summaries.append({
            "goal_id": page["goal_id"],
            "title": page["title"],
            "occasion_type": page["occasion_type"],
            "occasion_emoji": page.get("occasion_emoji", "🎉"),
            "participant_count": len(page.get("participants", [])),
            "items_total": len(items),
            "items_claimed": claimed,
            "coverage_pct": _compute_coverage(items),
            "days_until": _days_until(page.get("target_date", "")),
            "community_signal": page.get("community_signal", ""),
        })
    return _envelope({"goals": summaries, "count": len(summaries)})


# ── GET /api/community/goals/{goal_id} ────────────────────────────────────────
@router.get("/goals/{goal_id}")
def get_goal_page(goal_id: str):
    """
    Return full detail for a single community goal page.

    Includes all items with claimed_by_name, participant list,
    budget breakdown, and days_until derived fresh from today's date.
    """
    pages = _load_goal_pages()
    page = next((p for p in pages if p["goal_id"] == goal_id), None)
    if page is None:
        return _envelope(None, error=f"Goal page '{goal_id}' not found")

    items = page.get("items", [])
    detail = {
        **page,
        "items_total": len(items),
        "items_claimed": sum(1 for it in items if it.get("status") == "claimed"),
        "coverage_pct": _compute_coverage(items),
        "days_until": _days_until(page.get("target_date", "")),
    }
    return _envelope(detail)


# ── POST /api/community/goals ─────────────────────────────────────────────────
@router.post("/goals")
def create_goal_page(request: GoalPageCreateRequest):
    """
    Create a new community goal page.

    No authentication required for hackathon demo — created_by defaults to U001.
    The new page is appended to community_goal_pages.json and immediately
    visible in GET /api/community/goals.

    Items list starts empty; participants can add items via future PUT endpoints.
    For the hackathon, the page is created with a skeleton structure that the
    frontend can display immediately.
    """
    pages = _load_goal_pages()

    # Build participant list — always include creator
    participants = [request.created_by]
    participant_names = [request.participant_names[0] if request.participant_names else "You"]

    budget_per_person = (
        request.budget_total // len(participants)
        if participants else request.budget_total
    )

    new_page: dict = {
        "goal_id": f"goal_{request.occasion_type}_{str(uuid4())[:8]}",
        "title": request.title,
        "occasion_type": request.occasion_type,
        "occasion_emoji": request.occasion_emoji or "🎉",
        "created_by": request.created_by,
        "participants": participants,
        "participant_names": participant_names,
        "target_date": request.target_date,
        "budget_total": request.budget_total,
        "budget_per_person": budget_per_person,
        "items": [],
        "coverage_pct": 0,
        "community_signal": "Be the first to add items and invite friends to coordinate!",
    }

    pages.append(new_page)
    try:
        _save_goal_pages(pages)
    except Exception:
        # If write fails (read-only FS in Railway), still return the created page
        pass

    detail = {
        **new_page,
        "items_total": 0,
        "items_claimed": 0,
        "days_until": _days_until(request.target_date),
    }
    return _envelope(detail)
