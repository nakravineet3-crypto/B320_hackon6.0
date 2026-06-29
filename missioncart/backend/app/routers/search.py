from fastapi import APIRouter
from uuid import uuid4
import json
from pathlib import Path
from app.services.badge_engine import badge_engine
from app.services.retrieval_engine import retrieval_engine

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

    if q:
        q_lower = q.lower()
        # Exact/substring matches first (title, category, subcategory)
        exact_results = [
            p for p in results
            if q_lower in p.get("title", "").lower()
            or q_lower in p.get("category", "").lower()
            or q_lower in p.get("subcategory", "").lower()
        ]

        if len(exact_results) >= 5:
            results = exact_results
        else:
            # Fall back to semantic search via FAISS retrieval engine catalog
            try:
                # The retrieval engine holds an embedded catalog that may be
                # broader than the local CATALOG. Search it with substring
                # matching on title/category so we get semantically related
                # products even when the query word isn't in the title.
                engine_catalog = retrieval_engine.catalog or []
                semantic_results = [
                    p for p in engine_catalog
                    if q_lower in p.get("title", "").lower()
                    or q_lower in p.get("category", "").lower()
                    or q_lower in p.get("subcategory", "").lower()
                    or q_lower in p.get("tags", [])  # tags field if present
                ]

                # Also try category centroid search if FAISS index is loaded
                if retrieval_engine.index and retrieval_engine._category_centroids:
                    # Find categories whose names are semantically close to the query
                    matching_categories = [
                        cat for cat in retrieval_engine._category_centroids
                        if q_lower in cat.lower()
                        or cat.lower() in q_lower
                    ]
                    if matching_categories:
                        faiss_results = retrieval_engine._faiss_retrieve(
                            category_candidates=matching_categories,
                            budget_ceiling=999999,
                            top_k=20,
                        )
                        # Merge semantic_results with faiss_results
                        seen_asins = {p.get("asin") for p in semantic_results}
                        for p in faiss_results:
                            if p.get("asin") not in seen_asins:
                                semantic_results.append(p)
                                seen_asins.add(p.get("asin"))

                # Merge: exact results first, then semantic extras (dedup by asin)
                seen_asins = {p.get("asin") for p in exact_results}
                semantic_extras = [
                    p for p in semantic_results
                    if p.get("asin") not in seen_asins
                ]
                results = exact_results + semantic_extras
            except Exception:
                results = exact_results  # fallback to exact if FAISS fails

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


def clean_suggestion(s: str) -> str:
    return s.replace("_", " ").strip().title()


@router.get("/suggest")
async def suggest_queries(q: str = ""):
    """Autocomplete suggestions from catalog."""
    if not q or len(q) < 2:
        raw_categories = list(set(
            p.get("category", "") for p in CATALOG if p.get("category")
        ))[:8]
        suggestions = [clean_suggestion(s) for s in raw_categories if s]
        suggestions = list(dict.fromkeys(suggestions))[:6]
        return {
            "success": True,
            "data": {"suggestions": suggestions},
            "error": None,
            "request_id": str(uuid4()),
        }

    q_lower = q.lower()
    raw_suggestions = []

    # Category matches
    cat_matches = list(set(
        p.get("category", "")
        for p in CATALOG
        if q_lower in p.get("category", "").lower()
    ))
    raw_suggestions.extend(cat_matches[:3])

    # Title matches (first 4 words)
    title_matches = list(set(
        " ".join(p.get("title", "").split()[:4])
        for p in CATALOG
        if q_lower in p.get("title", "").lower()
    ))
    raw_suggestions.extend(title_matches[:3])

    suggestions = [clean_suggestion(s) for s in raw_suggestions if s]
    suggestions = list(dict.fromkeys(suggestions))[:6]

    return {
        "success": True,
        "data": {"suggestions": suggestions},
        "error": None,
        "request_id": str(uuid4()),
    }
