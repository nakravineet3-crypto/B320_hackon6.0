import json
import re
import os
from app.models.mission import MissionSpec
from app.services.llm.factory import llm_client
from app.services.llm.prompt_cache import prompt_cache
from app.services.llm.prompt_templates import (
    MISSION_PARSE_SYSTEM,
    build_parse_prompt,
)


def extract_fallback(raw_goal: str) -> dict:
    text = raw_goal.lower()
    result = {
        "goal": raw_goal,
        "domain": "general",
        "occasion": None,
        "headcount": None,
        "deadline_hours": 24,
        "budget_max": None,
        "safety_context": None,
        "needs_clarification": False,
        "clarification_question": None,
    }

    # ── HINGLISH PATTERNS ──────────────────────────────────
    HINGLISH_DOMAIN = {
        "naya ghar": "home_setup",
        "ghar setup": "home_setup",
        "ghar sajana": "home_setup",
        "trek": "travel",
        "safar": "travel",
        "birthday": "event",
        "janamdin": "event",
        "potluck": "event",
        "office party": "event",
        "diwali": "event",
        "tyohar": "event",
        "pooja": "event",
        "puja": "event",
        "shaadi": "event",
    }

    HINGLISH_OCCASION = {
        "birthday": "kids_birthday",
        "janamdin": "kids_birthday",
        "diwali": "festival",
        "tyohar": "festival",
        "pooja": "religious_event",
        "puja": "religious_event",
        "potluck": "office_event",
        "office party": "office_event",
        "shaadi": "wedding_event",
        "naya ghar": "home_setup",
        "ghar setup": "home_setup",
        "ghar sajana": "home_setup",
    }

    HINGLISH_DEADLINE = {
        "kal": 18,
        "aaj": 8,
        "abhi": 2,
        "is weekend": 48,
        "agli week": 120,
        "is hafte": 120,
    }

    HINGLISH_SAFETY = ["bachon", "bacche", "chote"]

    HINGLISH_HEADCOUNT_PATTERNS = [
        r'(\d+)\s*(?:bachon?|bacche|logo?n?|dosto?n?|jan|members?)',
        r'(\d+)\s*(?:log\b|logo\b)',
    ]

    HINGLISH_BUDGET_PATTERNS = [
        r'[₹]?\s*(\d+(?:,\d+)*)\s*(?:mein|tak|ka budget|ke andar|rupaye)',
        r'(\d+(?:,\d+)*)\s*budget',
    ]

    # ── DOMAIN DETECTION (Hinglish first, then English) ────
    domain_matched = False
    for phrase, domain in HINGLISH_DOMAIN.items():
        if phrase in text:
            result["domain"] = domain
            if phrase in HINGLISH_OCCASION:
                result["occasion"] = HINGLISH_OCCASION[phrase]
            domain_matched = True
            break

    if not domain_matched:
        # English domain detection
        if any(
            w in text
            for w in ["birthday", "party", "celebration", "kids", "children"]
        ):
            result["domain"] = "event"
            result["occasion"] = "kids_birthday"
        elif any(
            w in text
            for w in [
                "flat", "home", "house", "apartment", "hostel",
                "setup", "new place", "moving", "furnish",
            ]
        ):
            result["domain"] = "home_setup"
        elif any(
            w in text
            for w in [
                "trek", "travel", "trip", "road", "hike",
                "camping", "outdoor", "journey",
            ]
        ):
            result["domain"] = "travel"
        elif any(
            w in text
            for w in [
                "diwali", "holi", "festival", "navratri",
                "christmas", "eid", "puja",
            ]
        ):
            result["domain"] = "event"
            result["occasion"] = "festival"
        elif any(w in text for w in ["baby", "infant", "newborn", "toddler"]):
            result["domain"] = "baby_care"
            result["safety_context"] = "baby_safe"
        elif any(
            w in text
            for w in ["office", "work", "colleague", "team", "corporate", "potluck"]
        ):
            result["domain"] = "event"
            result["occasion"] = "office_event"

    # ── HEADCOUNT DETECTION (Hinglish first, then English) ─
    headcount_found = False
    for pattern in HINGLISH_HEADCOUNT_PATTERNS:
        match = re.search(pattern, text)
        if match:
            result["headcount"] = int(match.group(1))
            headcount_found = True
            break

    if not headcount_found:
        english_headcount_patterns = [
            r"(\d+)\s*(?:kids?|children|child)",
            r"(\d+)\s*(?:people|persons?|guests?|friends?|members?|colleagues?)",
            r"for\s+(\d+)",
            r"(\d+)\s*(?:of us)",
        ]
        for pattern in english_headcount_patterns:
            match = re.search(pattern, text)
            if match:
                result["headcount"] = int(match.group(1))
                break

    # ── SAFETY CONTEXT ─────────────────────────────────────
    if any(w in text for w in HINGLISH_SAFETY):
        result["safety_context"] = "child_safe"
    elif result["domain"] == "event" and result.get("occasion") == "kids_birthday":
        result["safety_context"] = "child_safe"
    elif any(w in text for w in ["kid", "child", "children", "baby", "toddler"]):
        result["safety_context"] = "child_safe"

    # ── BUDGET DETECTION (Hinglish first, then English) ────
    budget_found = False
    for pattern in HINGLISH_BUDGET_PATTERNS:
        match = re.search(pattern, text)
        if match:
            result["budget_max"] = float(match.group(1).replace(",", ""))
            budget_found = True
            break

    if not budget_found:
        english_budget_patterns = [
            r"(?:under|below|within|upto|up to|rs\.?|₹)\s*(\d+(?:,\d+)*)",
            r"(\d+(?:,\d+)*)\s*(?:rupees|rs|inr|budget)",
            r"budget\s+(?:of\s+)?(?:rs\.?|₹)?\s*(\d+(?:,\d+)*)",
        ]
        for pattern in english_budget_patterns:
            match = re.search(pattern, text)
            if match:
                result["budget_max"] = float(match.group(1).replace(",", ""))
                break

    # ── DEADLINE DETECTION (Hinglish first, then English) ──
    deadline_found = False
    for phrase, hours in HINGLISH_DEADLINE.items():
        if phrase in text:
            result["deadline_hours"] = hours
            deadline_found = True
            break

    if not deadline_found:
        if any(w in text for w in ["now", "immediately", "asap", "urgent"]):
            result["deadline_hours"] = 2
        elif any(w in text for w in ["today", "tonight", "this evening"]):
            result["deadline_hours"] = 8
        elif any(w in text for w in ["tomorrow", "tmrw"]):
            result["deadline_hours"] = 18
        elif any(w in text for w in ["this weekend", "weekend"]):
            result["deadline_hours"] = 48
        elif any(w in text for w in ["this week", "in a week"]):
            result["deadline_hours"] = 120

    # ── UNSUPPORTED GOAL DETECTION ─────────────────────────
    UNSUPPORTED_KEYWORDS = [
        "football", "cricket", "basketball", "tennis",
        "badminton", "hockey", "sports", "jersey",
        "iphone", "laptop", "phone", "mobile",
        "tv", "television", "refrigerator", "washing machine",
        "car", "bike", "motorcycle", "vehicle",
        "medicine", "tablet", "prescription",
        "furniture", "sofa", "table", "chair",
        "clothes", "shirt", "dress", "shoes",
        "gold", "jewellery", "jewelry",
    ]
    for keyword in UNSUPPORTED_KEYWORDS:
        if keyword in text:
            result["domain"] = "unsupported"
            result["unsupported_reason"] = (
                f"'{keyword.title()}' items are not available "
                f"on Amazon Now through MissionCart. "
                f"Try searching Amazon directly for the best selection."
            )
            result["needs_clarification"] = False
            return result

    # ── CLARIFICATION NEEDED ───────────────────────────────
    # Single word or very short ambiguous goal
    if len(raw_goal.strip().split()) <= 2 and result["domain"] == "general":
        result["needs_clarification"] = True
        result["clarification_question"] = (
            "Could you tell me more? For example: "
            "'Football kit for 5 players under ₹3000' "
            "or 'Birthday party for 12 kids tomorrow'"
        )
        result["clarification_type"] = "goal_unclear"
        return result

    # Missing budget for events
    if result["domain"] == "event" and not result.get("budget_max"):
        result["needs_clarification"] = True
        result["clarification_question"] = (
            "What is your budget for this occasion?"
        )
        result["clarification_type"] = "budget"

    return result


async def parse_mission(raw_goal: str, budget: float = None) -> MissionSpec:
    """Parse a goal string into a MissionSpec.

    Uses three-tier approach:
    1. Check prompt cache (instant)
    2. Try LLM provider (Groq/Anthropic/Bedrock/Gemini)
    3. Regex fallback (always works)
    """
    user_message = build_parse_prompt(raw_goal)

    # Step 1: Check cache first
    cached = prompt_cache.get(MISSION_PARSE_SYSTEM, user_message)
    if cached:
        try:
            data = json.loads(cached)
            data["raw_goal"] = raw_goal
            if budget is not None and data.get("budget_max") is None:
                data["budget_max"] = budget
            return MissionSpec(**data)
        except Exception:
            pass

    # Step 2: Try LLM provider
    if llm_client:
        try:
            response = await llm_client.complete(
                system_prompt=MISSION_PARSE_SYSTEM,
                user_message=user_message,
                max_tokens=500,
                temperature=0.1,
            )

            # Clean response text
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()

            # Cache the raw response text
            prompt_cache.set(MISSION_PARSE_SYSTEM, user_message, text)

            data = json.loads(text)
            data["raw_goal"] = raw_goal
            if budget is not None and data.get("budget_max") is None:
                data["budget_max"] = budget

            # Log provider + latency for debugging
            print(
                f"LLM [{response.provider}] "
                f"{response.latency_ms:.0f}ms "
                f"cached={response.cached} "
                f"tokens={response.tokens_used}"
            )

            return MissionSpec(**data)
        except json.JSONDecodeError as e:
            print(f"LLM JSON parse error: {e}")
        except Exception as e:
            print(f"LLM error [{type(e).__name__}]: {e}")

    # Step 3: Regex fallback — always works
    print("Using regex fallback parser")
    data = extract_fallback(raw_goal)
    data["raw_goal"] = raw_goal
    if budget is not None and data.get("budget_max") is None:
        data["budget_max"] = budget
    return MissionSpec(**data)


# Synchronous wrapper for backward compatibility
def parse_mission_sync(raw_goal: str, budget: float = None) -> MissionSpec:
    """Synchronous version of parse_mission for non-async contexts."""
    import asyncio

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Already in async context — use fallback directly
            data = extract_fallback(raw_goal)
            data["raw_goal"] = raw_goal
            if budget is not None and data.get("budget_max") is None:
                data["budget_max"] = budget
            return MissionSpec(**data)
    except RuntimeError:
        pass

    return asyncio.run(parse_mission(raw_goal, budget))
