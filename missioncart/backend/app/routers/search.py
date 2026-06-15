from fastapi import APIRouter
from uuid import uuid4
import json
from pathlib import Path
from app.services.badge_engine import badge_engine

router = APIRouter()

DATA_PATH = Path(__file__).parent.parent / "data"


def load_catalog():
    path = DATA_PATH / "catalog.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return []


CATALOG = load_catalog()


@router.get("/products")
async def search_products(
    q: str = "",
    occasion: str = "general",
    limit: int = 30,
    with_badges: bool = True,
):
    """Search products with optional badge overlay."""
    results = CATALOG

    # Filter by query
    if q:
        q_lower = q.lower()
        results = [
            p for p in results
            if q_lower in p.get("title", "").lower()
            or q_lower in p.get("category", "").lower()
            or q_lower in p.get("subcategory", "").lower()
        ]

    # Sort: Now-eligible first, then by rating
    results = sorted(
        results,
        key=lambda p: (
            -int(p.get("amazon_now_eligible", False)),
            -p.get("rating", 0),
        ),
    )[:limit]

    # Attach badges
    if with_badges:
        results = badge_engine.get_products_with_badges(results, occasion)

    return {
        "success": True,
        "data": {
            "products": results,
            "total": len(results),
            "query": q,
            "occasion": occasion,
            "badges_active": with_badges,
        },
        "error": None,
        "request_id": str(uuid4()),
    }


@router.get("/badge/{asin}")
async def get_product_badge(asin: str):
    """Get badge for a single product by ASIN."""
    badge = badge_engine.get_badge(asin)
    return {
        "success": True,
        "data": badge,
        "error": None,
        "request_id": str(uuid4()),
    }


@router.get("/suggest")
async def suggest_queries(q: str = ""):
    """Autocomplete suggestions from catalog."""
    if not q or len(q) < 2:
        categories = list(set(
            p.get("category", "") for p in CATALOG if p.get("category")
        ))[:8]
        return {
            "success": True,
            "data": {"suggestions": categories},
            "error": None,
            "request_id": str(uuid4()),
        }

    q_lower = q.lower()
    suggestions = []

    # Category matches
    cat_matches = list(set(
        p.get("category", "")
        for p in CATALOG
        if q_lower in p.get("category", "").lower()
    ))
    suggestions.extend(cat_matches[:3])

    # Title matches (first 4 words)
    title_matches = list(set(
        " ".join(p.get("title", "").split()[:4])
        for p in CATALOG
        if q_lower in p.get("title", "").lower()
    ))
    suggestions.extend(title_matches[:3])

    return {
        "success": True,
        "data": {"suggestions": list(dict.fromkeys(suggestions))[:6]},
        "error": None,
        "request_id": str(uuid4()),
    }
