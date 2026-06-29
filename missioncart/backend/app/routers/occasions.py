"""
Occasions router — GET /api/occasions/feed

Returns a ranked, time-aware occasion intelligence feed for a given user.
All scoring is deterministic (see occasion_engine.py). No LLM calls.
"""
import json
from pathlib import Path
from fastapi import APIRouter, Query
from uuid import uuid4

router = APIRouter()

_DATA_DIR = Path(__file__).parent.parent / "data"


def _load_cluster_map() -> dict:
    try:
        with open(_DATA_DIR / "user_cluster_map.json", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


_CLUSTER_MAP: dict = {}


def _get_cluster_id(user_id: str) -> str:
    global _CLUSTER_MAP
    if not _CLUSTER_MAP:
        _CLUSTER_MAP = _load_cluster_map()
    entry = _CLUSTER_MAP.get(user_id, {})
    return entry.get("cluster_id", "office_gym_dad")


@router.get("/feed")
async def get_occasion_feed_endpoint(
    user_id: str = Query(default="U001", description="User ID for cluster-aware personalisation"),
    limit: int = Query(default=6, ge=1, le=20, description="Maximum number of occasion cards"),
):
    """
    Returns a ranked occasion intelligence feed.

    Ordering:
    - Date-bound occasions (festivals, holidays) appear first, sorted by days_until ascending.
    - Recurring / evergreen occasions (birthday, potluck, trek) appear after, sorted by
      relevance_score descending.

    Each card includes: occasion_type, title, emoji, days_until, urgency_state,
    urgency_label, estimated_budget, headcount, community_signal, tap_goal, relevance_score.
    """
    try:
        from app.services.occasion_engine import get_occasion_feed
        cluster_id = _get_cluster_id(user_id)
        cards = get_occasion_feed(cluster_id=cluster_id, limit=limit)
        return {
            "success": True,
            "data": {
                "occasions": cards,
                "user_id": user_id,
                "cluster_id": cluster_id,
                "count": len(cards),
            },
            "error": None,
            "request_id": str(uuid4()),
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": {"message": str(e), "code": "OCCASION_FEED_ERROR"},
            "request_id": str(uuid4()),
        }
