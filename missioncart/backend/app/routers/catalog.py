import json
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Query
from uuid import uuid4

router = APIRouter()

DATA_PATH = Path(__file__).parent.parent / "data" / "catalog.json"


def _load_catalog():
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


@router.get("/")
async def catalog_root():
    return {"message": "Catalog router ready"}


@router.get("/products")
async def get_products(
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    catalog = _load_catalog()
    if category:
        catalog = [p for p in catalog if p.get("category", "") == category]
    if search:
        q = search.lower()
        catalog = [
            p for p in catalog
            if q in p.get("title", "").lower()
            or q in p.get("category", "").lower()
            or q in p.get("brand", "").lower()
        ]
    total = len(catalog)
    page = catalog[offset: offset + limit]
    return {
        "success": True,
        "data": page,
        "total": total,
        "limit": limit,
        "offset": offset,
        "error": None,
        "request_id": str(uuid4()),
    }


@router.get("/categories")
async def get_categories():
    catalog = _load_catalog()
    cats: dict = {}
    for p in catalog:
        c = p.get("category", "")
        if c:
            cats[c] = cats.get(c, 0) + 1
    return {
        "success": True,
        "data": [{"category": k, "count": v} for k, v in sorted(cats.items())],
        "error": None,
        "request_id": str(uuid4()),
    }
