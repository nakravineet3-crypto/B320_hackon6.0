import json
import time
from pathlib import Path
from collections import Counter
from fastapi import APIRouter, Query
from uuid import uuid4

router = APIRouter()

_SIMULATED_PATH = Path(__file__).parent.parent / "data" / "simulated"

# ── Helpers ────────────────────────────────────────────────


def _load_json(filename: str):
    """Load a JSON file from simulated/ directory. Returns None on failure."""
    try:
        with open(_SIMULATED_PATH / filename, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


@router.get("/scenarios")
async def get_demo_scenarios():
    scenario_path = Path(__file__).parent.parent / "data" / "demo_scenarios" / "sneha_broken_cart.json"
    with open(scenario_path, encoding="utf-8") as f:
        data = json.load(f)
    return {"success": True, "data": data, "error": None, "request_id": str(uuid4())}


@router.get("/occasions")
async def get_occasion_cards(user_id: str = Query(default="U001")):
    from app.services.occasion_engine import get_occasion_feed

    # Resolve cluster_id from user_cluster_map for the given user
    cluster_id = "office_gym_dad"  # default for U001 demo
    try:
        cluster_path = Path(__file__).parent.parent / "data" / "user_cluster_map.json"
        with open(cluster_path, encoding="utf-8") as f:
            cluster_map = json.load(f)
        user_entry = cluster_map.get(user_id, {})
        cluster_id = user_entry.get("cluster_id", cluster_id)
    except Exception:
        pass

    cards = get_occasion_feed(cluster_id=cluster_id, limit=6)

    # Enrich with recurrence alerts from occasion_history for personalisation
    occasion_history = _load_json("occasion_history.json")
    if occasion_history:
        u_occasions = occasion_history.get(user_id, [])
        recurrence_map = {}
        for occ in u_occasions:
            if occ.get("recurrence_date") and occ.get("repeat_next_year"):
                occ_type = occ.get("occasion_type", "")
                days_until = occ.get("days_until_recurrence")
                if days_until and days_until < 365:
                    if occ_type not in recurrence_map or days_until < recurrence_map[occ_type]["days_until_recurrence"]:
                        recurrence_map[occ_type] = {
                            "days_until_recurrence": days_until,
                            "occasion_label": occ.get("occasion_label"),
                            "last_headcount": occ.get("headcount"),
                            "last_budget": occ.get("budget_used"),
                        }
        for card in cards:
            rec = recurrence_map.get(card["occasion_type"])
            if rec:
                card["recurrence_alert"] = (
                    f"{card['title']} in {rec['days_until_recurrence']} days — "
                    f"rebuild last year's mission?"
                )
                card["last_headcount"] = rec.get("last_headcount")
                card["last_budget"] = rec.get("last_budget")

    return {"success": True, "data": cards, "error": None, "request_id": str(uuid4())}


@router.get("/reorder-alerts")
async def get_reorder_alerts():
    # Load real depletion alerts from simulated dataset
    alerts_data = _load_json("depletion_alerts.json")
    if alerts_data:
        u001_alerts = alerts_data.get("U001", [])
        # Return top 3 urgent/soon alerts sorted by urgency then days_remaining
        urgency_order = {"urgent": 0, "soon": 1, "normal": 2, "low": 3}
        sorted_alerts = sorted(
            u001_alerts,
            key=lambda a: (urgency_order.get(a.get("reorder_urgency", "low"), 3), a.get("days_remaining", 99)),
        )
        # Return all items with days_remaining <= 2 (urgent), fallback to top 3
        urgent = [a for a in sorted_alerts if a.get("days_remaining", 99) <= 2]
        selected = urgent if urgent else sorted_alerts[:3]
        data = [
            {
                "id": alert.get("asin", f"r{i}"),
                "asin": alert.get("asin"),
                "item_name": alert.get("title"),
                "quantity": alert.get("suggested_quantity", 1),
                "unit": "packs" if alert.get("suggested_quantity", 1) > 1 else "pack",
                "price_inr": alert.get("price", 0),
                "amazon_now_eligible": alert.get("amazon_now_eligible", True),
                "days_remaining": alert.get("days_remaining"),
                "confidence": alert.get("confidence", "high"),
                "reorder_urgency": alert.get("reorder_urgency", "normal"),
                "last_purchased": alert.get("last_purchased"),
                "purchase_count": alert.get("purchase_count", 0),
            }
            for i, alert in enumerate(selected)
        ]
        return {"success": True, "data": data, "error": None, "request_id": str(uuid4())}

    # Fallback to hardcoded
    data = [
        {"id": "r1", "item_name": "Tata Salt 1kg", "quantity": 2, "unit": "packs", "price_inr": 42, "amazon_now_eligible": True, "days_remaining": 2.8},
        {"id": "r2", "item_name": "Surf Excel 1kg", "quantity": 1, "unit": "pack", "price_inr": 189, "amazon_now_eligible": True, "days_remaining": 4.7},
        {"id": "r3", "item_name": "Parle-G 800g", "quantity": 3, "unit": "packs", "price_inr": 105, "amazon_now_eligible": True, "days_remaining": 1.0},
    ]
    return {"success": True, "data": data, "error": None, "request_id": str(uuid4())}


@router.get("/hinglish-examples")
async def get_hinglish_examples():
    data = [
        {
            "input": "12 bachon ki birthday party kal \u20b94000 mein",
            "parsed": {
                "domain": "event",
                "occasion": "kids_birthday",
                "headcount": 12,
                "deadline_hours": 18,
                "budget_max": 4000,
                "safety_context": "child_safe",
            },
            "language_detected": "hinglish",
        },
        {
            "input": "naya ghar setup karna hai is weekend \u20b915000 tak",
            "parsed": {
                "domain": "home_setup",
                "headcount": None,
                "deadline_hours": 48,
                "budget_max": 15000,
                "safety_context": None,
            },
            "language_detected": "hinglish",
        },
        {
            "input": "dosto ke saath trek 4 log \u20b95000 mein",
            "parsed": {
                "domain": "travel",
                "headcount": 4,
                "deadline_hours": 48,
                "budget_max": 5000,
                "safety_context": None,
            },
            "language_detected": "hinglish",
        },
        {
            "input": "Diwali ke liye ghar sajana hai 8 log \u20b95000 budget",
            "parsed": {
                "domain": "event",
                "occasion": "festival",
                "headcount": 8,
                "deadline_hours": 24,
                "budget_max": 5000,
                "safety_context": None,
            },
            "language_detected": "hinglish",
        },
        {
            "input": "office mein potluck hai aaj 20 logo ke liye \u20b92000",
            "parsed": {
                "domain": "event",
                "occasion": "office_event",
                "headcount": 20,
                "deadline_hours": 8,
                "budget_max": 2000,
                "safety_context": None,
            },
            "language_detected": "hinglish",
        },
    ]
    return {"success": True, "data": data, "error": None, "request_id": str(uuid4())}


@router.get("/cache-stats")
def get_cache_stats():
    from app.services.llm.prompt_cache import prompt_cache
    from app.services.llm.factory import llm_client

    return {
        "success": True,
        "data": {
            "cache": prompt_cache.stats(),
            "provider": (
                llm_client.__class__.__name__ if llm_client else "None"
            ),
        },
    }


@router.get("/user-profile")
async def get_user_profile():
    """Returns U001 profile + computed stats for home screen."""
    # Load all simulated data
    users = _load_json("users.json")
    purchase_history = _load_json("purchase_history.json")
    occasion_history = _load_json("occasion_history.json")
    depletion_alerts = _load_json("depletion_alerts.json")

    # Find U001 user
    user = None
    if users:
        user = next((u for u in users if u.get("user_id") == "U001"), None)
    if not user:
        user = {"user_id": "U001", "name": "Sneha Sharma", "city": "Bangalore"}

    # Compute stats from purchase history
    u001_orders = purchase_history.get("U001", []) if purchase_history else []
    total_orders = len(u001_orders)
    total_spent = sum(order.get("total", 0) for order in u001_orders)

    # Most common occasion tag
    occasion_tags = [order.get("occasion_tag", "") for order in u001_orders if order.get("occasion_tag")]
    most_common_occasion = Counter(occasion_tags).most_common(1)[0][0] if occasion_tags else "routine_grocery"

    # Occasion history stats
    u001_occasions = occasion_history.get("U001", []) if occasion_history else []
    total_occasions = len(u001_occasions)
    outcome_ratings = [occ.get("outcome_rating", 0) for occ in u001_occasions if occ.get("outcome_rating")]
    avg_rating = sum(outcome_ratings) / len(outcome_ratings) if outcome_ratings else 0

    # Depletion urgent count
    u001_alerts = depletion_alerts.get("U001", []) if depletion_alerts else []
    urgent_count = sum(1 for a in u001_alerts if a.get("reorder_urgency") == "urgent")

    # Upcoming recurrence. The Diwali countdown is pinned for the demo flow.
    upcoming_recurrence = None
    repeatable_occasions = [
        occ for occ in u001_occasions
        if occ.get("recurrence_date") and occ.get("repeat_next_year")
    ]
    repeatable_occasions.sort(
        key=lambda occ: (
            occ.get("occasion_type") != "festival",
            occ.get("days_until_recurrence", 999),
        )
    )
    if repeatable_occasions:
        occ = repeatable_occasions[0]
        is_diwali_demo = occ.get("occasion_type") == "festival"
        days_until = 24 if is_diwali_demo else occ.get("days_until_recurrence")
        alert_label = "Diwali" if is_diwali_demo else occ.get("occasion_label")
        upcoming_recurrence = {
            "occasion_label": occ.get("occasion_label"),
            "occasion_type": occ.get("occasion_type"),
            "budget_used": occ.get("budget_used", 0),
            "headcount": occ.get("headcount", 0),
            "coverage_score": occ.get("coverage_score", ""),
            "days_until_recurrence": days_until,
            "recurrence_date": occ.get("recurrence_date"),
            "recurrence_alert": (
                occ.get("recurrence_alert")
                or f"{alert_label} in {days_until} days - rebuild last year's mission?"
            ),
        }

    data = {
        "user": user,
        "stats": {
            "total_orders": total_orders,
            "total_occasions": total_occasions,
            "total_spent": total_spent,
            "most_common_occasion": most_common_occasion,
            "avg_mission_rating": round(avg_rating, 1),
            "depletion_alerts_urgent": urgent_count,
        },
        "upcoming_recurrence": upcoming_recurrence,
    }

    return {"success": True, "data": data, "error": None, "request_id": str(uuid4())}


@router.post("/warm")
async def warm_cache():
    """Pre-warms the cache with demo goals.
    Call this once before the demo to ensure instant response times.
    """
    import time
    from app.services.mission_parser import parse_mission
    from app.services.domain_router import route_and_decompose
    from app.services.cart_builder import build_cart
    from app.routers.mission import _build_cache, _parse_cache

    demo_goals = [
        ("Birthday party for 12 kids tomorrow under 4000", 4000),
        ("New flat setup this weekend under 15000", 15000),
        ("Road trip for 4 people this weekend under 5000", 5000),
    ]

    results = []
    for goal, budget in demo_goals:
        start = time.time()
        try:
            spec = await parse_mission(goal, budget)
            needs = route_and_decompose(spec)
            result = build_cart(spec, needs)

            # Populate the endpoint caches so live calls are instant.
            # Key must match the build endpoint exactly: budget is a float there.
            cache_key = f"{goal}_{float(budget)}"
            _build_cache[cache_key] = result
            _parse_cache[cache_key] = {
                "mission_id": spec.mission_id,
                "raw_goal": spec.raw_goal,
                "goal": spec.goal or spec.raw_goal,
                "domain": spec.domain,
                "occasion": spec.occasion,
                "headcount": spec.headcount,
                "deadline_hours": spec.deadline_hours,
                "budget_max": spec.budget_max,
                "safety_context": spec.safety_context,
                "needs_clarification": spec.needs_clarification,
                "clarification_question": spec.clarification_question,
            }

            elapsed = (time.time() - start) * 1000
            results.append({
                "goal": goal[:40],
                "status": "warmed",
                "items": len(result.get("cart_items", [])),
                "latency_ms": round(elapsed),
            })
        except Exception as e:
            results.append({
                "goal": goal[:40],
                "status": f"error: {str(e)[:30]}",
                "latency_ms": 0,
            })

    return {
        "success": True,
        "data": {
            "warmed": len([r for r in results if r["status"] == "warmed"]),
            "results": results,
        },
    }


@router.get("/voice-input-example")
async def get_voice_input_example():
    data = {
        "transcript": "Bees bachon ki birthday party kal chaar hazar mein",
        "detected_language": "hinglish",
        "confidence": 0.94,
        "parsed": {
            "domain": "event",
            "occasion": "kids_birthday",
            "headcount": 20,
            "deadline_hours": 18,
            "budget_max": 4000,
            "safety_context": "child_safe",
        },
        "processing_time_ms": 340,
    }
    return {"success": True, "data": data, "error": None, "request_id": str(uuid4())}


@router.get("/seller-insights")
async def get_seller_insights():
    data = {
        "seller_id": "SELLER001",
        "seller_name": "Party Supplies India",
        "insights": [
            {
                "occasion_type": "kids_birthday",
                "city": "Bangalore",
                "upcoming_missions": 847,
                "avg_budget": 3850,
                "top_needed_categories": [
                    {"category": "plates", "demand_index": 0.94, "avg_quantity": 3},
                    {"category": "balloon_set", "demand_index": 0.87, "avg_quantity": 2},
                    {"category": "return_gifts", "demand_index": 0.71, "avg_quantity": 1},
                ],
                "peak_days": ["Friday", "Saturday", "Sunday"],
                "advance_notice_days": 2.3,
            },
            {
                "occasion_type": "festival",
                "city": "Bangalore",
                "upcoming_missions": 312,
                "avg_budget": 4200,
                "top_needed_categories": [
                    {"category": "festival_lights", "demand_index": 0.96, "avg_quantity": 3},
                    {"category": "decoration", "demand_index": 0.82, "avg_quantity": 2},
                ],
                "peak_days": ["Wednesday", "Thursday"],
                "advance_notice_days": 5.1,
            },
        ],
        "total_addressable_missions_this_month": 2847,
        "estimated_gmv_opportunity": 1094950,
    }
    return {"success": True, "data": data, "error": None, "request_id": str(uuid4())}


@router.get("/mission-share-card")
async def get_mission_share_card():
    data = {
        "mission_id": "M0012",
        "share_title": "Riya's Birthday Party",
        "planned_by": "Sneha Sharma",
        "occasion_date": "2026-06-20",
        "headcount": 12,
        "total_cost": 3850,
        "coverage": "9/9",
        "items_summary": [
            "24 plates",
            "30 cups",
            "60 balloons",
            "1 pump",
            "12 return gifts",
            "candles",
        ],
        "all_amazon_now": True,
        "delivery_time": "20 mins",
        "share_url": "https://missioncart.in/share/M0012",
        "qr_code_url": None,
        "message": (
            "I planned Riya's birthday on MissionCart! "
            "Full party kit in 45 seconds. All arriving via "
            "Amazon Now in 20 mins."
        ),
    }
    return {"success": True, "data": data, "error": None, "request_id": str(uuid4())}


@router.get("/notification-content")
async def get_notification_content():
    """Returns push notification content computed from real depletion alerts."""
    alerts_data = _load_json("depletion_alerts.json")

    if not alerts_data:
        # Hardcoded fallback
        return {
            "success": True,
            "data": {
                "title": "🛒 Your daily reorder is ready",
                "body": "Tata Salt, Surf Excel, Parle-G — Tap to approve ⚡",
                "items": [],
                "urgency": "high",
                "total_price": 399,
                "item_count": 3,
            },
            "error": None,
            "request_id": str(uuid4()),
        }

    u001_alerts = alerts_data.get("U001", [])

    # Sort by urgency then days_remaining
    urgency_order = {"urgent": 0, "soon": 1, "normal": 2, "low": 3}
    sorted_alerts = sorted(
        u001_alerts,
        key=lambda a: (
            urgency_order.get(a.get("reorder_urgency", "low"), 3),
            a.get("days_remaining", 99),
        ),
    )
    # Use same urgent filter: all items with days_remaining <= 2
    urgent = [a for a in sorted_alerts if a.get("days_remaining", 99) <= 2]
    selected = urgent if urgent else sorted_alerts[:3]

    # Build items list
    items = []
    for alert in selected:
        qty = alert.get("suggested_quantity", 1)
        price = alert.get("price", 0)
        items.append({
            "name": alert.get("title", "Item"),
            "quantity": qty,
            "unit": "bottles" if "milk" in alert.get("title", "").lower() else "packs",
            "price_inr": price * qty,
            "days_remaining": alert.get("days_remaining", 0),
        })

    # Build notification body — first 3 names + "+N more" if more
    names = [item["name"] for item in items]
    if len(names) == 1:
        body = f"{names[0]} — Tap to approve & order ⚡"
    elif len(names) == 2:
        body = f"{names[0]}, {names[1]} — Tap to approve ⚡"
    elif len(names) == 3:
        body = f"{names[0]}, {names[1]}, {names[2]} — Tap to approve ⚡"
    else:
        body = f"{names[0]}, {names[1]}, {names[2]} +{len(names) - 3} more — Tap to approve ⚡"

    # Determine urgency
    has_urgent = any(a.get("reorder_urgency") == "urgent" for a in selected)
    urgency = "high" if has_urgent else "medium"

    total_price = sum(item["price_inr"] for item in items)

    data = {
        "title": "🛒 Your daily reorder is ready",
        "body": body,
        "items": items,
        "urgency": urgency,
        "total_price": total_price,
        "item_count": len(items),
    }

    return {"success": True, "data": data, "error": None, "request_id": str(uuid4())}
