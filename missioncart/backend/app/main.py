from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from uuid import uuid4
import os
from dotenv import load_dotenv

load_dotenv()

from app.routers import mission, catalog, demo, reorder, intelligence, comparison, search, hive


@asynccontextmanager
async def lifespan(app):
    # Startup: warm the cache with demo goals
    print("Warming demo cache...")
    try:
        from app.services.mission_parser import parse_mission
        from app.services.domain_router import route_and_decompose
        from app.services.cart_builder import build_cart

        demo_goals = [
            ("Birthday party for 12 kids tomorrow under 4000", 4000),
            ("New flat setup this weekend under 15000", 15000),
            ("Trek to Coorg for 4 people this weekend under 5000", 5000),
        ]
        for goal, budget in demo_goals:
            try:
                spec = await parse_mission(goal, budget)
                needs = route_and_decompose(spec)
                result = build_cart(spec, needs)
                # Store in endpoint cache
                cache_key = f"{goal}_{float(budget)}"
                mission._build_cache[cache_key] = result
                print(f"  Warmed: {goal[:40]} ({len(result.get('cart_items', []))} items)")
            except Exception as e:
                print(f"  Skip: {goal[:30]} — {e}")
        print("Cache warm complete")
    except Exception as e:
        print(f"Cache warm failed (non-fatal): {e}")
    yield
    # Shutdown: nothing needed


app = FastAPI(title="MissionCart API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(mission.router, prefix="/api/mission", tags=["mission"])
app.include_router(catalog.router, prefix="/api/catalog", tags=["catalog"])
app.include_router(reorder.router, prefix="/api/reorder", tags=["reorder"])
app.include_router(demo.router, prefix="/api/demo", tags=["demo"])
app.include_router(intelligence.router, prefix="/api/intelligence", tags=["intelligence"])
app.include_router(comparison.router, prefix="/api/comparison", tags=["comparison"])
app.include_router(search.router, prefix="/api/search", tags=["search"])
app.include_router(hive.router, prefix="/api/quorum", tags=["quorum"])


@app.get("/health")
def health():
    return {
        "success": True,
        "data": {"status": "ok", "service": "missioncart-backend"},
        "error": None,
        "request_id": str(uuid4()),
    }
