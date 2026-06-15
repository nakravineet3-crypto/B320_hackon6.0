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
async def get_products(search: Optional[str] = Query(None)):
    catalog = _load_catalog()
    if search:
        q = search.lower()
        catalog = [
            p for p in catalog
            if q in p.get("title", "").lower()
            or q in p.get("category", "").lower()
        ]
    return {
        "success": True,
        "data": catalog[:50],  # Cap at 50 results
        "error": None,
        "request_id": str(uuid4()),
    }
