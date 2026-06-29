import os
import time
from fastapi import APIRouter
from app.services.profile_engine import profile_engine
from pydantic import BaseModel
from typing import List, Optional
from uuid import uuid4
from cachetools import TTLCache

router = APIRouter()

# Simple in-memory caches for hot demo paths
_build_cache = TTLCache(maxsize=50, ttl=3600)
_parse_cache = TTLCache(maxsize=50, ttl=3600)


# ---------------------------------------------------------------------------
# Domain-aware fallback carts — used when the pipeline throws any exception.
# These are returned instead of the old hardcoded birthday cart for all goals.
# ---------------------------------------------------------------------------

_BIRTHDAY_FALLBACK_ITEMS = [
    {"cart_item_id": "fb_b1", "need_label": "Plates & utensils", "asin": "B0PARTY001", "title": "Disposable Paper Plates (Pack of 25)", "category": "plates", "price": 89, "pack_size": 25, "packs_quantity": 2, "units_total": 50, "total_cost": 178, "delivery_eta": "now_20min", "prime": True, "amazon_now_eligible": True, "rating": 4.2, "explanation": "50 plates — 2 per person × 20 guests", "is_sponsored": False, "mission_fit_score": 0.82},
    {"cart_item_id": "fb_b2", "need_label": "Cups & drinks", "asin": "B0PARTY005", "title": "Disposable Paper Cups (Pack of 50)", "category": "cups", "price": 99, "pack_size": 50, "packs_quantity": 1, "units_total": 50, "total_cost": 99, "delivery_eta": "now_20min", "prime": True, "amazon_now_eligible": True, "rating": 4.1, "explanation": "50 cups — 2.5 per person × 20 guests", "is_sponsored": False, "mission_fit_score": 0.80},
    {"cart_item_id": "fb_b3", "need_label": "Balloons & decorations", "asin": "B0PARTY013", "title": "Multicolor Balloon Set (Pack of 50)", "category": "balloon_set", "price": 199, "pack_size": 50, "packs_quantity": 2, "units_total": 100, "total_cost": 398, "delivery_eta": "now_20min", "prime": True, "amazon_now_eligible": True, "rating": 4.3, "explanation": "100 balloons — 3 per person × 20 with buffer", "is_sponsored": False, "mission_fit_score": 0.84},
    {"cart_item_id": "fb_b4", "need_label": "Balloon pump", "asin": "B0PARTY019", "title": "Balloon Hand Pump Double Action", "category": "balloon_pump", "price": 99, "pack_size": 1, "packs_quantity": 1, "units_total": 1, "total_cost": 99, "delivery_eta": "now_20min", "prime": True, "amazon_now_eligible": True, "rating": 4.0, "explanation": "Required accessory for balloon set", "is_sponsored": False, "mission_fit_score": 0.90},
    {"cart_item_id": "fb_b5", "need_label": "Candles & cake knife", "asin": "B0PARTY021", "title": "Birthday Candles Number Set", "category": "candles", "price": 49, "pack_size": 1, "packs_quantity": 1, "units_total": 1, "total_cost": 49, "delivery_eta": "now_20min", "prime": True, "amazon_now_eligible": True, "rating": 4.2, "explanation": "1 pack of candles", "is_sponsored": False, "mission_fit_score": 0.78},
    {"cart_item_id": "fb_b6", "need_label": "Napkins", "asin": "B0PARTY009", "title": "Paper Napkins White (Pack of 100)", "category": "napkins", "price": 79, "pack_size": 100, "packs_quantity": 1, "units_total": 100, "total_cost": 79, "delivery_eta": "now_20min", "prime": True, "amazon_now_eligible": True, "rating": 4.0, "explanation": "100 napkins for 20 guests", "is_sponsored": False, "mission_fit_score": 0.77},
    {"cart_item_id": "fb_b7", "need_label": "Return gifts", "asin": "B0PARTY033", "title": "Return Gift Bags Printed (Pack of 12)", "category": "return_gifts", "price": 179, "pack_size": 12, "packs_quantity": 2, "units_total": 24, "total_cost": 358, "delivery_eta": "now_20min", "prime": True, "amazon_now_eligible": True, "rating": 4.3, "explanation": "24 return gifts — 1 per child × 20 with buffer", "is_sponsored": False, "mission_fit_score": 0.81},
    {"cart_item_id": "fb_b8", "need_label": "Birthday banner", "asin": "B0PARTY031", "title": "Happy Birthday Banner Glitter Gold", "category": "banner", "price": 99, "pack_size": 1, "packs_quantity": 1, "units_total": 1, "total_cost": 99, "delivery_eta": "now_20min", "prime": True, "amazon_now_eligible": True, "rating": 4.4, "explanation": "1 birthday banner for decoration", "is_sponsored": False, "mission_fit_score": 0.83},
]

_TREK_FALLBACK_ITEMS = [
    {"cart_item_id": "fb_t1", "need_label": "Backpack", "asin": "B0TREK001", "title": "Trekking Backpack 40L", "category": "backpack", "price": 1499, "pack_size": 1, "packs_quantity": 1, "units_total": 1, "total_cost": 1499, "delivery_eta": "today", "prime": True, "amazon_now_eligible": True, "rating": 4.3, "explanation": "1 backpack per person", "is_sponsored": False, "mission_fit_score": 0.88},
    {"cart_item_id": "fb_t2", "need_label": "Water bottles", "asin": "B0TREK002", "title": "Stainless Steel Water Bottle 1L", "category": "water_bottle", "price": 399, "pack_size": 1, "packs_quantity": 1, "units_total": 1, "total_cost": 399, "delivery_eta": "today", "prime": True, "amazon_now_eligible": True, "rating": 4.4, "explanation": "1 water bottle per person", "is_sponsored": False, "mission_fit_score": 0.86},
    {"cart_item_id": "fb_t3", "need_label": "First aid kit", "asin": "B0TREK003", "title": "First Aid Kit 63-Piece", "category": "first_aid_kit", "price": 349, "pack_size": 1, "packs_quantity": 1, "units_total": 1, "total_cost": 349, "delivery_eta": "today", "prime": True, "amazon_now_eligible": True, "rating": 4.2, "explanation": "1 first aid kit per group", "is_sponsored": False, "mission_fit_score": 0.85},
    {"cart_item_id": "fb_t4", "need_label": "Rain jacket", "asin": "B0TREK004", "title": "Waterproof Rain Jacket Unisex", "category": "rain_jacket", "price": 799, "pack_size": 1, "packs_quantity": 1, "units_total": 1, "total_cost": 799, "delivery_eta": "today", "prime": True, "amazon_now_eligible": True, "rating": 4.1, "explanation": "1 rain jacket per person", "is_sponsored": False, "mission_fit_score": 0.83},
    {"cart_item_id": "fb_t5", "need_label": "Trekking socks", "asin": "B0TREK005", "title": "Trekking Socks Anti-Blister (Pack of 3)", "category": "trekking_socks", "price": 299, "pack_size": 3, "packs_quantity": 1, "units_total": 3, "total_cost": 299, "delivery_eta": "today", "prime": True, "amazon_now_eligible": True, "rating": 4.3, "explanation": "1 pack of trekking socks per person", "is_sponsored": False, "mission_fit_score": 0.82},
    {"cart_item_id": "fb_t6", "need_label": "Torch / headlamp", "asin": "B0TREK006", "title": "LED Torch Handheld 200 Lumens", "category": "torch", "price": 249, "pack_size": 1, "packs_quantity": 1, "units_total": 1, "total_cost": 249, "delivery_eta": "today", "prime": True, "amazon_now_eligible": True, "rating": 4.2, "explanation": "1 torch per 2 people", "is_sponsored": False, "mission_fit_score": 0.80},
    {"cart_item_id": "fb_t7", "need_label": "Energy snacks", "asin": "B0TREK007", "title": "Energy Bar Assorted Pack of 6", "category": "energy_bar", "price": 299, "pack_size": 6, "packs_quantity": 1, "units_total": 6, "total_cost": 299, "delivery_eta": "today", "prime": True, "amazon_now_eligible": True, "rating": 4.1, "explanation": "Energy bars for the trek", "is_sponsored": False, "mission_fit_score": 0.79},
]

_HOME_FALLBACK_ITEMS = [
    {"cart_item_id": "fb_h1", "need_label": "Mattress & bedding", "asin": "B0HOME001", "title": "Single Mattress 3 inch Memory Foam", "category": "mattress", "price": 4999, "pack_size": 1, "packs_quantity": 1, "units_total": 1, "total_cost": 4999, "delivery_eta": "tomorrow", "prime": True, "amazon_now_eligible": False, "rating": 4.3, "explanation": "1 mattress", "is_sponsored": False, "mission_fit_score": 0.88},
    {"cart_item_id": "fb_h2", "need_label": "Bedsheet", "asin": "B0HOME002", "title": "Cotton Bedsheet Set with 2 Pillow Covers", "category": "bedsheet", "price": 699, "pack_size": 1, "packs_quantity": 1, "units_total": 1, "total_cost": 699, "delivery_eta": "today", "prime": True, "amazon_now_eligible": True, "rating": 4.2, "explanation": "1 bedsheet set", "is_sponsored": False, "mission_fit_score": 0.84},
    {"cart_item_id": "fb_h3", "need_label": "Water purifier", "asin": "B0HOME_WP001", "title": "Pureit Gravity Water Purifier 10L", "category": "water_purifier", "price": 4999, "pack_size": 1, "packs_quantity": 1, "units_total": 1, "total_cost": 4999, "delivery_eta": "today", "prime": True, "amazon_now_eligible": True, "rating": 4.2, "explanation": "1 gravity water purifier", "is_sponsored": False, "mission_fit_score": 0.86},
    {"cart_item_id": "fb_h4", "need_label": "Induction cooktop", "asin": "B0HOME003", "title": "Havells Induction Cooktop 1600W", "category": "induction_cooktop", "price": 1799, "pack_size": 1, "packs_quantity": 1, "units_total": 1, "total_cost": 1799, "delivery_eta": "today", "prime": True, "amazon_now_eligible": True, "rating": 4.3, "explanation": "1 induction cooktop", "is_sponsored": False, "mission_fit_score": 0.85},
    {"cart_item_id": "fb_h5", "need_label": "Cooking vessel", "asin": "B0HOME004", "title": "Induction Compatible Kadai 2L", "category": "induction_compatible_vessel", "price": 599, "pack_size": 1, "packs_quantity": 1, "units_total": 1, "total_cost": 599, "delivery_eta": "today", "prime": True, "amazon_now_eligible": True, "rating": 4.1, "explanation": "Induction compatible vessel", "is_sponsored": False, "mission_fit_score": 0.82},
    {"cart_item_id": "fb_h6", "need_label": "Towels", "asin": "B0HOME005", "title": "Cotton Bath Towels (Pack of 2)", "category": "towels", "price": 499, "pack_size": 2, "packs_quantity": 1, "units_total": 2, "total_cost": 499, "delivery_eta": "today", "prime": True, "amazon_now_eligible": True, "rating": 4.2, "explanation": "2 bath towels", "is_sponsored": False, "mission_fit_score": 0.81},
    {"cart_item_id": "fb_h7", "need_label": "Extension board", "asin": "B0HOME006", "title": "Anchor Extension Board 4-Socket 2m", "category": "extension_board", "price": 349, "pack_size": 1, "packs_quantity": 1, "units_total": 1, "total_cost": 349, "delivery_eta": "now_20min", "prime": True, "amazon_now_eligible": True, "rating": 4.4, "explanation": "1 extension board", "is_sponsored": False, "mission_fit_score": 0.80},
    {"cart_item_id": "fb_h8", "need_label": "LED bulbs", "asin": "B0HOME007", "title": "Philips LED Bulb 9W (Pack of 4)", "category": "led_bulb", "price": 299, "pack_size": 4, "packs_quantity": 1, "units_total": 4, "total_cost": 299, "delivery_eta": "now_20min", "prime": True, "amazon_now_eligible": True, "rating": 4.5, "explanation": "4 LED bulbs", "is_sponsored": False, "mission_fit_score": 0.83},
]


def _domain_fallback(goal: str, budget: float) -> dict:
    """Return domain-appropriate fallback cart when pipeline fails.
    Never returns birthday items for a non-birthday goal.
    """
    goal_lower = goal.lower()

    if any(k in goal_lower for k in ["trek", "travel", "trip", "coorg", "camping", "hike", "outdoor"]):
        fallback_items = _TREK_FALLBACK_ITEMS
    elif any(k in goal_lower for k in ["flat", "hostel", "home", "setup", "pg", "room", "house", "furnish", "moving"]):
        fallback_items = _HOME_FALLBACK_ITEMS
    else:
        fallback_items = _BIRTHDAY_FALLBACK_ITEMS

    total_cost = sum(item["total_cost"] for item in fallback_items)
    return {
        "success": True,
        "data": {
            "mission_id": str(uuid4()),
            "cart_items": fallback_items,
            "total_cost": total_cost,
            "budget_remaining": budget - total_cost,
            "coverage_score": {
                "fraction": 1.0,
                "covered": len(fallback_items),
                "total": len(fallback_items),
                "display": f"{len(fallback_items)}/{len(fallback_items)}",
                "all_must_haves_covered": True,
                "missing": [],
            },
            "delivery_status": {
                "all_on_time": True,
                "all_amazon_now": True,
                "bottleneck_items": [],
                "message": "All items available on Amazon Now",
            },
            "repair_summary": None,
            "flags": [],
            "amazon_cart_url": "",
            "warnings": ["Cart built from fallback template — pipeline error occurred"],
            "simulated_data": True,
            "fallback": True,
            "coverage_score_label": "Estimated",
        },
        "error": None,
        "request_id": str(uuid4()),
    }


OCCASION_KEYWORDS = {
    'diwali': 'diwali_celebration',
    'holi': 'holi_celebration',
    'birthday': 'kids_birthday',
    'grihapravesh': 'grihapravesh',
    'griha pravesh': 'grihapravesh',
    'housewarming': 'grihapravesh',
    'potluck': 'office_potluck',
    'office': 'office_potluck',
    'trek': 'travel_trek',
    'travel': 'travel_trek',
    'onam': 'onam',
    'navratri': 'navratri',
    'dussehra': 'dussehra',
    'raksha': 'raksha_bandhan',
    'monsoon': 'monsoon_prep',
    'baby shower': 'baby_shower',
    'baby_shower': 'baby_shower',
}


def _detect_occasion_from_goal(goal: str) -> Optional[str]:
    """Keyword-based occasion detection. Used as fallback when LLM parse fails."""
    goal_lower = goal.lower()
    for keyword, occasion_type in OCCASION_KEYWORDS.items():
        if keyword in goal_lower:
            return occasion_type
    return None


def _has_api_key() -> bool:
    key = os.getenv("ANTHROPIC_API_KEY")
    return bool(key and key != "your_key_here")


class AuditRequest(BaseModel):
    cart_items: list = []
    existing_cart: list = []
    # Upgraded fields — None means "unknown / not provided"
    headcount: Optional[int] = None
    occasion_type: Optional[str] = None
    occasion: Optional[str] = None          # deprecated alias for occasion_type
    goal: str = ""
    budget_inr: Optional[float] = None
    budget_max: Optional[float] = None      # deprecated alias for budget_inr
    deadline_hours: Optional[int] = None
    safety_context: str = "general"


class ParseRequest(BaseModel):
    goal: str
    budget: float = 3000.0


class BuildRequest(BaseModel):
    goal: str
    budget: float = 3000.0


@router.post("/audit")
async def audit_cart(request: AuditRequest):
    from app.services.audit_engine import (
        is_demo_cart,
        run_real_audit,
        DEMO_FLAGS,
        DEMO_REPAIRED_CART,
    )

    cart_items = request.existing_cart or request.cart_items or []

    # EMPTY CART GUARD
    if not cart_items:
        return {
            "success": False,
            "data": None,
            "error": "Cart is empty — add items to audit",
            "request_id": str(uuid4()),
        }

    # Backward-compatible field resolution
    occasion_type = request.occasion_type or request.occasion or None
    headcount = request.headcount                       # None means unknown
    budget_inr = request.budget_inr or request.budget_max or None
    deadline_hours = request.deadline_hours             # None means no deadline

    # DEMO PATH — preserved exactly
    if is_demo_cart(cart_items, occasion_type=occasion_type or "", session_goal=request.goal):
        return {
            "success": True,
            "data": {
                "flags": DEMO_FLAGS,
                "original_cart": [
                    {"product_id": "P001", "name": "Paper Plates 10pc", "quantity": 1, "price_inr": 120, "amazon_now_eligible": True, "sponsored": False},
                    {"product_id": "P002", "name": "Balloon Set 20pc", "quantity": 1, "price_inr": 180, "amazon_now_eligible": True, "sponsored": False},
                    {"product_id": "P003", "name": "Streamers 5pc", "quantity": 2, "price_inr": 90, "amazon_now_eligible": False, "sponsored": False},
                    {"product_id": "P004", "name": "Party Cups 10pc", "quantity": 2, "price_inr": 95, "amazon_now_eligible": True, "sponsored": True},
                ],
                "repaired_cart": DEMO_REPAIRED_CART,
                "original_total": 4340,
                "repaired_total": 3850,
                "coverage_score": "9/9",
                "all_amazon_now": True,
                "is_demo": True,
                "analysis_stats": {
                    "items_checked": 4,
                    "flags_found": 4,
                    "items_repaired": 3,
                    "engine": "demo_path",
                },
            },
            "error": None,
            "request_id": str(uuid4()),
        }

    # REAL AUDIT PATH
    result = run_real_audit(
        cart_items=cart_items,
        occasion_type=occasion_type or "general",
        headcount=headcount,          # may be None — engine handles gracefully
        budget_max=budget_inr,        # may be None
        deadline_hours=deadline_hours,  # may be None
        safety_context=request.safety_context or "general",
    )
    return {"success": True, "data": result, "error": None, "request_id": str(uuid4())}


@router.post("/parse")
async def parse_goal(request: ParseRequest):
    cache_key = f"{request.goal}_{request.budget}"
    if cache_key in _parse_cache:
        cached = dict(_parse_cache[cache_key])
        cached["_cached"] = True
        return {"success": True, "data": cached, "error": None, "request_id": str(uuid4())}

    try:
        from app.services.mission_parser import parse_mission
        spec = await parse_mission(request.goal, request.budget)
        data = {
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
        _parse_cache[cache_key] = data
        return {"success": True, "data": data, "error": None, "request_id": str(uuid4())}
    except Exception:
        pass

    # Keyword-based fallback — detect occasion from goal text before defaulting
    detected_occasion = _detect_occasion_from_goal(request.goal or "")
    occasion_type = detected_occasion or "kids_birthday"

    # Derive a sensible domain from the detected occasion
    _OCCASION_TO_DOMAIN = {
        "travel_trek": "travel",
        "grihapravesh": "home_setup",
    }
    domain = _OCCASION_TO_DOMAIN.get(occasion_type, "event")

    # Safety context: birthday and baby_shower are child_safe by default
    safety_context = "child_safe" if occasion_type in ("kids_birthday", "baby_shower") else "general"

    data = {
        "mission_id": str(uuid4()),
        "raw_goal": request.goal,
        "goal": request.goal or f"{occasion_type.replace('_', ' ').title()} under ₹{int(request.budget)}",
        "domain": domain,
        "occasion": occasion_type,
        "headcount": 20 if occasion_type == "kids_birthday" else 6,
        "deadline_hours": 18,
        "budget_max": request.budget,
        "safety_context": safety_context,
        "needs_clarification": False,
        "clarification_question": None,
    }
    return {"success": True, "data": data, "error": None, "request_id": str(uuid4())}


@router.post("/build")
async def build_cart_endpoint(request: BuildRequest):
    # Preliminary cache key (goal + budget only) for a quick pre-parse hit
    _prelim_key = f"{request.goal.strip().lower()}_{request.budget}"
    if _prelim_key in _build_cache:
        cached = dict(_build_cache[_prelim_key])
        cached["_cached"] = True
        return {"success": True, "data": cached, "error": None, "request_id": str(uuid4())}

    # Always use the full pipeline: parse → decompose → build
    try:
        from app.services.mission_parser import parse_mission
        from app.services.domain_router import route_and_decompose
        from app.services.cart_builder import build_cart

        spec = await parse_mission(request.goal, request.budget)

        # ── Post-parse overrides ─────────────────────────────────────────────
        goal_lower = request.goal.lower()

        # 1. Festival goals: LLM sometimes routes to home_setup — force event
        _FESTIVAL_KEYS = [
            "diwali", "holi", "navratri", "dussehra", "onam", "eid",
            "christmas", "durga puja", "ganesh", "raksha bandhan", "ugadi",
        ]
        if any(kw in goal_lower for kw in _FESTIVAL_KEYS):
            spec.domain = "event"
            if not spec.occasion or spec.occasion in ("home_setup", "general", ""):
                spec.occasion = next(
                    (kw.replace(" ", "_") + "_celebration"
                     for kw in _FESTIVAL_KEYS if kw in goal_lower),
                    "festival"
                )

        # 2. Goals with budget + headcount extracted don't need clarification
        if getattr(spec, "needs_clarification", False):
            _has_budget = bool(spec.budget_max)
            _has_headcount = bool(spec.headcount)
            _has_occasion = spec.domain not in ("general", "unsupported", "")
            # If budget + headcount are both known, or budget + clear occasion, proceed
            if (_has_budget and _has_headcount) or (_has_budget and _has_occasion and spec.domain in ("event", "travel", "home_setup", "grocery", "baby_care", "pet_care")):
                spec.needs_clarification = False

        # Handle unsupported domain
        if spec.domain == "unsupported":
            reason = getattr(spec, "unsupported_reason", None) or (
                "This type of item is not available on Amazon Now"
            )
            return {
                "success": False,
                "data": {
                    "unsupported": True,
                    "unsupported_reason": reason,
                    "suggestion": "Try searching Amazon.in directly",
                    "amazon_search_url": (
                        f"https://www.amazon.in/s?k="
                        f"{request.goal.replace(' ', '+')}"
                    ),
                    "supported_goals": [
                        "Birthday party for 12 kids under ₹4000",
                        "New flat setup this weekend",
                        "Trek to Coorg for 4 people",
                        "Diwali celebration at home",
                        "Weekly grocery restock",
                    ],
                },
                "error": "Goal not supported by MissionCart",
                "request_id": str(uuid4()),
            }

        # Handle needs clarification
        if getattr(spec, "needs_clarification", False):
            return {
                "success": False,
                "data": {
                    "needs_clarification": True,
                    "clarification_question": getattr(
                        spec, "clarification_question",
                        "Could you provide more details?"
                    ),
                    "clarification_type": getattr(
                        spec, "clarification_type", "goal_unclear"
                    ),
                    "partial_spec": {
                        "domain": spec.domain,
                        "goal": spec.raw_goal,
                        "detected": {
                            "headcount": spec.headcount,
                            "budget": spec.budget_max,
                            "deadline": spec.deadline_hours,
                        },
                    },
                    "suggestions": [
                        f"Try: '{spec.raw_goal} for 10 people'",
                        f"Try: '{spec.raw_goal} under ₹3000'",
                        f"Try: '{spec.raw_goal} tomorrow'",
                    ],
                },
                "error": "Need more information to build cart",
                "request_id": str(uuid4()),
            }

        if os.getenv("USE_PROFILE_ENGINE", "false").lower() == "true":
            needs = await profile_engine.get_needs(spec, user_id="U001")
        else:
            needs = route_and_decompose(spec)
        result = build_cart(spec, needs)

        # Add retrieval metadata
        from app.services.retrieval_engine import retrieval_engine as _re
        result["retrieval_method"] = (
            "blair_faiss" if _re.index is not None else "keyword_category"
        )
        result["embedding_model"] = (
            "hyp1231/blair-roberta-large" if _re.index is not None else "none"
        )

        # Enrich result with spec metadata — required by API contract
        result.setdefault("domain", spec.domain)
        result.setdefault("occasion", spec.occasion)
        result.setdefault("headcount", spec.headcount)
        result.setdefault("budget_max", spec.budget_max)
        result["simulated_data"] = True

        # Cache under headcount-inclusive key so "Birthday for 6" and "Birthday
        # for 12" never collide even at the same budget.
        headcount_val = getattr(spec, "headcount", None) or 0
        cache_key = f"{request.goal.strip().lower()}_{request.budget}_{headcount_val}"
        _build_cache[cache_key] = result
        # Also write the preliminary key so the pre-parse fast path is warm.
        _build_cache[_prelim_key] = result
        return {"success": True, "data": result, "error": None, "request_id": str(uuid4())}
    except Exception as e:
        print(f"[build] pipeline error for goal='{request.goal}': {type(e).__name__}: {e}")
        return _domain_fallback(request.goal, request.budget)
