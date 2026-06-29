"""
ProfileEngine — Two-layer adaptive occasion profile system for MissionCart.

Layer 1: occasion_need_taxonomy.json  — human-curated, loaded at startup, never overwritten
Layer 2: occasion_profiles_cache.json — LLM-generated on cache miss, written atomically

ADR references: ADR-001 through ADR-008 in goal-cart-adaptive-final-arch.md
"""

import asyncio
import hashlib
import json
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Optional

from app.models.mission import MissionSpec, NeedItem

# ---------------------------------------------------------------------------
# File paths
# ---------------------------------------------------------------------------

DATA_PATH = Path(__file__).parent.parent / "data"
TAXONOMY_PATH = DATA_PATH / "occasion_need_taxonomy.json"
CACHE_PATH = DATA_PATH / "occasion_profiles_cache.json"
USER_SIGNALS_PATH = DATA_PATH / "user_need_signals.json"

# ---------------------------------------------------------------------------
# EWMA learning rates  (ADR-003)
# ---------------------------------------------------------------------------

ALPHA_NEGATIVE = 0.30   # removal: strong signal, learn fast
ALPHA_POSITIVE = 0.08   # keep: weak signal, learn slow
ALPHA_ADDED    = 0.20   # user manually added: discovery signal

# ---------------------------------------------------------------------------
# Priority promotion/demotion thresholds from community signals
# ---------------------------------------------------------------------------

COMMUNITY_MUST_HAVE_THRESHOLD = 0.85
COMMUNITY_OPTIONAL_THRESHOLD  = 0.30

# ---------------------------------------------------------------------------
# Flush policy
# ---------------------------------------------------------------------------

FLUSH_EVERY_N       = 50   # flush after this many buffered events
FLUSH_EVERY_SECONDS = 60   # or after this many seconds since last flush

# ---------------------------------------------------------------------------
# Safety blocklists  (applied during LLM output validation)
# ---------------------------------------------------------------------------

BLOCKED_CATEGORIES = {
    "alcohol", "beer", "wine", "spirits", "tobacco", "cigarettes",
    "medicine", "prescription", "contraceptives", "adult_content",
    "fireworks", "weapons", "knives",
}

CHILD_SAFE_BLOCKED = {
    "alcohol", "beer", "wine", "caffeinated_drinks", "energy_drinks",
    "tobacco", "adult_games", "poker_chips",
}

_CHILD_INDICATORS = {"kids", "children", "baby", "toddler", "infant", "school"}

# Regex: only digits, +, -, *, /, (, ), spaces, and the two allowed variable names
_ALLOWED_FORMULA_CHARS = re.compile(
    r'^[\d\.\+\-\*\/\(\)\s]*(headcount|days)?[\d\.\+\-\*\/\(\)\s]*$'
)

# ---------------------------------------------------------------------------
# Generic fallback needs  (absolute last resort — always produces some cart)
# ---------------------------------------------------------------------------

_GENERIC_FALLBACK_NEEDS = [
    {
        "need_id": "primary_items",
        "priority": "must_have",
        "qty_formula": "headcount * 2",
        "category_candidates": ["plates", "cups"],
        "budget_fraction": 0.40,
        "clamp_floor": 0.0,
        "notes": "Generic fallback",
    },
    {
        "need_id": "accessories",
        "priority": "should_have",
        "qty_formula": "headcount * 3",
        "category_candidates": ["napkins"],
        "budget_fraction": 0.30,
        "clamp_floor": 0.0,
        "notes": "Generic fallback",
    },
    {
        "need_id": "extras",
        "priority": "optional",
        "qty_formula": "2",
        "category_candidates": ["decoration_streamers"],
        "budget_fraction": 0.20,
        "clamp_floor": 0.0,
        "notes": "Generic fallback",
    },
]

# ---------------------------------------------------------------------------
# LLM system prompt for need generation  (ADR-002)
# ---------------------------------------------------------------------------

_NEED_GENERATION_SYSTEM_PROMPT = (
    "You are a structured need decomposition system for Amazon Now "
    "(20-minute delivery in India).\n"
    "You generate shopping need lists for Indian occasions. "
    "Your output is always a JSON array.\n"
    "You know Indian culture, Indian regional variations, and what categories of "
    "items are available on quick-commerce.\n"
    "You NEVER include alcohol, tobacco, medicines, prescription drugs, adult items, "
    "fireworks, or weapons.\n"
    "You NEVER output prose, headers, or markdown. Only the JSON array.\n"
    "When safety_context is \"child_safe\", also exclude: caffeinated_drinks, "
    "energy_drinks, adult_games, poker_chips.\n"
    "\n"
    "Every need object has exactly five fields:\n"
    "  need_id: snake_case category name, max 3 words\n"
    "  priority: one of \"must_have\" | \"should_have\" | \"optional\"\n"
    "  qty_formula: safe math using ONLY headcount, days, +, -, *, /, "
    "integer/float literals. No function calls.\n"
    "  category_candidates: JSON array of snake_case category strings\n"
    "  notes: one sentence explaining why this item is needed for this specific occasion\n"
    "\n"
    "Produce 5 to 12 needs. At least 2 must_have, at least 1 optional.\n"
    "Return ONLY the JSON array.\n"
    "\n"
    "EXAMPLE — diwali_puja:\n"
    "[\n"
    '  {"need_id": "diyas", "priority": "must_have", "qty_formula": "headcount * 5", '
    '"category_candidates": ["diyas"], "notes": "Central ritual act of Diwali"},\n'
    '  {"need_id": "puja_thali", "priority": "must_have", "qty_formula": "1", '
    '"category_candidates": ["puja_thali"], "notes": "Single decorated thali holds all puja items"},\n'
    '  {"need_id": "agarbatti", "priority": "must_have", "qty_formula": "2", '
    '"category_candidates": ["agarbatti"], "notes": "Incense mandatory for puja rituals"},\n'
    '  {"need_id": "rangoli_colors", "priority": "should_have", "qty_formula": "1", '
    '"category_candidates": ["rangoli_colors"], "notes": "Rangoli at entrance near-universal for Diwali"},\n'
    '  {"need_id": "festival_lights", "priority": "should_have", "qty_formula": "2", '
    '"category_candidates": ["festival_lights"], "notes": "LED string lights for decoration"},\n'
    '  {"need_id": "dry_fruits", "priority": "should_have", "qty_formula": "headcount * 1", '
    '"category_candidates": ["dry_fruits"], "notes": "Gifting dry fruits is a Diwali social norm"},\n'
    '  {"need_id": "mithai_box", "priority": "optional", "qty_formula": "headcount / 4", '
    '"category_candidates": ["sweets_box"], "notes": "Sweet boxes for visiting guest families"}\n'
    "]\n"
    "\n"
    "EXAMPLE — kids_birthday:\n"
    "[\n"
    '  {"need_id": "plates", "priority": "must_have", "qty_formula": "headcount * 2", '
    '"category_candidates": ["plates"], "notes": "Kids double-plate at parties"},\n'
    '  {"need_id": "cups", "priority": "must_have", "qty_formula": "headcount * 2", '
    '"category_candidates": ["cups"], "notes": "Juice and cold drinks served separately"},\n'
    '  {"need_id": "candles", "priority": "must_have", "qty_formula": "1", '
    '"category_candidates": ["candles"], "notes": "One candle set per cake"},\n'
    '  {"need_id": "balloon_set", "priority": "should_have", "qty_formula": "headcount * 3", '
    '"category_candidates": ["balloon_set"], "notes": "Primary visual decor for kids birthday"},\n'
    '  {"need_id": "balloon_pump", "priority": "should_have", "qty_formula": "1", '
    '"category_candidates": ["balloon_pump"], "notes": "Required dependency for balloon set"},\n'
    '  {"need_id": "return_gifts", "priority": "should_have", "qty_formula": "headcount * 1", '
    '"category_candidates": ["return_gifts"], "notes": "Standard expectation at Indian kids birthday"},\n'
    '  {"need_id": "streamers", "priority": "optional", "qty_formula": "2", '
    '"category_candidates": ["decoration_streamers"], "notes": "Additional decor, not functionally required"}\n'
    "]\n"
    "\n"
    "EXAMPLE — monsoon_prep:\n"
    "[\n"
    '  {"need_id": "umbrella", "priority": "must_have", "qty_formula": "headcount * 1", '
    '"category_candidates": ["umbrella"], "notes": "Primary rain protection per person"},\n'
    '  {"need_id": "mosquito_repellent", "priority": "must_have", "qty_formula": "2", '
    '"category_candidates": ["mosquito_repellent"], "notes": "Peak mosquito season in Indian monsoon"},\n'
    '  {"need_id": "raincoat", "priority": "should_have", "qty_formula": "headcount * 1", '
    '"category_candidates": ["raincoat"], "notes": "Required for two-wheeler commuters"},\n'
    '  {"need_id": "waterproof_footwear", "priority": "should_have", "qty_formula": "headcount * 1", '
    '"category_candidates": ["waterproof_footwear"], "notes": "Regular footwear deteriorates in monsoon"},\n'
    '  {"need_id": "antifungal_powder", "priority": "should_have", "qty_formula": "headcount * 1", '
    '"category_candidates": ["antifungal_powder"], "notes": "Prevents humidity-caused skin infections"},\n'
    '  {"need_id": "instant_noodles", "priority": "optional", "qty_formula": "headcount * 3", '
    '"category_candidates": ["instant_noodles"], "notes": "Rainy day comfort food"}\n'
    "]"
)

# ---------------------------------------------------------------------------
# Keyword maps for parent-fallback and occasion inference
# ---------------------------------------------------------------------------

_PARENT_KEYWORD_MAP = {
    "puja": "grihapravesh",      "chaturthi": "grihapravesh",
    "navratri": "diwali_celebration", "diwali": "diwali_celebration",
    "holi": "holi_celebration",  "festival": "diwali_celebration",
    "birthday": "kids_birthday", "party": "kids_birthday",
    "kids": "kids_birthday",     "adult": "adult_birthday",
    "trek": "travel_trek",       "camping": "travel_trek",
    "trip": "travel_trek",       "travel": "travel_trek",
    "setup": "home_setup",       "hostel": "home_setup",
    "home": "home_setup",
    "potluck": "office_potluck", "office": "office_potluck",
    "shower": "baby_shower",     "baby": "baby_shower",
    "cricket": "cricket_viewing_party",
    "monsoon": "monsoon_prep",
}

_PARENT_INFER_MAP = {
    "puja": "festival",     "chaturthi": "festival", "navratri": "festival",
    "birthday": "birthday", "party": "social",
    "trek": "travel",       "trip": "travel",
    "setup": "home_setup",
    "potluck": "social",
}


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _make_event_id(user_id: str, occasion_type: str) -> str:
    """Idempotency key: user + occasion + current minute (truncated SHA-256)."""
    minute = int(time.time() // 60)
    raw = f"{user_id}:{occasion_type}:{minute}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _atomic_write_json(path: Path, data) -> None:
    """Atomic write: temp file then os.replace.  Prevents torn reads."""
    dir_ = path.parent
    dir_.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", dir=dir_, suffix=".tmp", delete=False, encoding="utf-8"
    ) as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        tmp_path = f.name
    os.replace(tmp_path, str(path))


def _safe_formula(formula: str, headcount: int = 1, days: int = 1) -> int:
    """
    Evaluate a qty_formula string.  Only headcount, days, and arithmetic are
    permitted.  Returns max(1, rounded result).  Returns 1 on any error.
    """
    try:
        cleaned = formula.strip().lower()
        result = eval(
            cleaned.replace("headcount", str(headcount)).replace("days", str(days)),
            {"__builtins__": {}},
        )
        return max(1, int(round(float(result))))
    except Exception:
        return 1


def _validate_formula(formula: str) -> bool:
    """Return True if the formula string is safe to eval."""
    cleaned = formula.strip().lower()
    # Must match allowed character set
    if not _ALLOWED_FORMULA_CHARS.match(cleaned):
        return False
    # No function calls
    if re.search(r'[a-z_]+\s*\(', cleaned):
        return False
    # Must evaluate without error and produce a non-negative number ≤ 10000
    try:
        result = eval(
            cleaned.replace("headcount", "10").replace("days", "2"),
            {"__builtins__": {}},
        )
        return isinstance(result, (int, float)) and 0 <= result <= 10_000
    except Exception:
        return False


def _validate_llm_need(need: dict, safety_context: Optional[str] = None) -> Optional[dict]:
    """
    Validate a single LLM-generated need dict.
    Returns the cleaned need on success, None on failure.
    """
    need_id = str(need.get("need_id", "")).lower().replace(" ", "_").replace("-", "_")
    if not need_id:
        return None
    if need_id in BLOCKED_CATEGORIES:
        return None
    if safety_context == "child_safe" and need_id in CHILD_SAFE_BLOCKED:
        return None

    priority = need.get("priority")
    if priority not in ("must_have", "should_have", "optional"):
        return None

    formula = str(need.get("qty_formula", "1"))
    if not _validate_formula(formula):
        formula = "1"  # fall back to 1 rather than reject the whole need

    category_candidates = need.get("category_candidates", [])
    if not isinstance(category_candidates, list) or not category_candidates:
        category_candidates = [need_id]

    return {
        "need_id": need_id,
        "priority": priority,
        "qty_formula": formula,
        "category_candidates": [str(c).lower() for c in category_candidates],
        "clamp_floor": float(need.get("clamp_floor", 0.0)),
        "notes": str(need.get("notes", "")),
        "budget_fraction": float(need.get("budget_fraction", 0.10)),
    }


# ---------------------------------------------------------------------------
# ProfileEngine
# ---------------------------------------------------------------------------

class ProfileEngine:
    """
    Manages occasion need profiles across two layers:
      Layer 1  — occasion_need_taxonomy.json  (human-curated, read-only at runtime)
      Layer 2  — occasion_profiles_cache.json (LLM-generated, written atomically)

    The engine maintains an in-memory dict so every get_needs() call is O(1) on
    cache hit with zero disk I/O.
    """

    def __init__(self) -> None:
        # occasion_type → profile dict  (Layer 1 + Layer 2 merged at startup)
        self._profiles: dict[str, dict] = {}
        # user_id → occasion_type → need_id → float signal
        self._user_signals: dict[str, dict] = {}
        # per-occasion asyncio.Lock entries for stampede protection
        self._generation_locks: dict[str, asyncio.Lock] = {}
        # write-back buffer
        self._feedback_buffer: list[dict] = []
        # idempotency set for approve events (per-minute granularity)
        self._seen_event_ids: set[str] = set()
        # flush state
        self._last_flush_time: float = time.time()
        self._flush_in_progress: bool = False
        self._loaded: bool = False

    # ------------------------------------------------------------------
    # Startup
    # ------------------------------------------------------------------

    async def load(self) -> None:
        """
        Called from FastAPI lifespan.  Loads taxonomy then LLM cache into
        _profiles.  Taxonomy entries take precedence over cache entries for the
        same occasion_type.  Never raises — startup must always succeed.
        """
        # Layer 1: human-curated taxonomy (authoritative)
        if TAXONOMY_PATH.exists():
            try:
                with open(TAXONOMY_PATH, encoding="utf-8") as f:
                    raw = json.load(f)
                for occasion_type, profile in raw.get("occasions", {}).items():
                    self._profiles[occasion_type] = profile
                print(f"ProfileEngine: loaded {len(self._profiles)} taxonomy profiles")
            except Exception as e:
                print(f"ProfileEngine WARNING: taxonomy load failed (non-fatal): {e}")

        # Layer 2: LLM-generated cache (supplemental — never overrides taxonomy)
        if CACHE_PATH.exists():
            try:
                with open(CACHE_PATH, encoding="utf-8") as f:
                    raw = json.load(f)
                count_added = 0
                for entry in (raw if isinstance(raw, list) else []):
                    ot = entry.get("occasion_type") or entry.get("occasion_id")
                    if ot and ot not in self._profiles:
                        self._profiles[ot] = entry
                        count_added += 1
                print(f"ProfileEngine: loaded {count_added} cached LLM profiles")
            except Exception as e:
                print(f"ProfileEngine WARNING: cache load failed (non-fatal): {e}")

        # User signals
        if USER_SIGNALS_PATH.exists():
            try:
                with open(USER_SIGNALS_PATH, encoding="utf-8") as f:
                    self._user_signals = json.load(f)
            except Exception as e:
                print(f"ProfileEngine WARNING: user signals load failed (non-fatal): {e}")

        self._loaded = True
        print(f"ProfileEngine: ready with {len(self._profiles)} total profiles")

    # ------------------------------------------------------------------
    # Main entry point — replaces route_and_decompose(spec)
    # ------------------------------------------------------------------

    async def get_needs(self, spec: MissionSpec, user_id: str = "U001") -> list[NeedItem]:
        """
        Input:  MissionSpec (existing model, unchanged)
        Output: list[NeedItem] (existing model, unchanged — drop-in replacement)
        Guarantee: always returns a non-empty list (fallback chain ensures this)
        """
        occasion_type = self._resolve_occasion_type(spec)

        # --- Cache hit path  (O(1) dict lookup) ---
        if occasion_type in self._profiles:
            profile = self._profiles[occasion_type]
            profile = self._enrich_with_community(profile, occasion_type)
            profile = self._enrich_with_user(profile, user_id, occasion_type)
            return self._materialize_needs(profile, spec)

        # --- Cache miss — stampede-protected LLM generation ---
        if occasion_type not in self._generation_locks:
            self._generation_locks[occasion_type] = asyncio.Lock()

        async with self._generation_locks[occasion_type]:
            # Double-check: a prior waiter may have already generated it
            if occasion_type in self._profiles:
                profile = self._profiles[occasion_type]
            else:
                profile = await self._generate_profile(occasion_type, spec)
                self._profiles[occasion_type] = profile
                # Evict the lock — it is no longer needed (prevents unbounded growth)
                del self._generation_locks[occasion_type]
                # Persist to disk without blocking the caller
                asyncio.create_task(self._persist_cache())

        profile = self._enrich_with_community(profile, occasion_type)
        profile = self._enrich_with_user(profile, user_id, occasion_type)
        return self._materialize_needs(profile, spec)

    # ------------------------------------------------------------------
    # Occasion type resolution
    # ------------------------------------------------------------------

    def _resolve_occasion_type(self, spec: MissionSpec) -> str:
        """
        Maps MissionSpec to a canonical snake_case occasion_type string.
        spec.occasion takes priority over spec.domain.
        """
        if spec.occasion and spec.occasion.lower() not in ("general", ""):
            return spec.occasion.lower().replace(" ", "_").replace("-", "_")
        if spec.domain and spec.domain.lower() not in ("general", ""):
            return spec.domain.lower().replace(" ", "_").replace("-", "_")
        return "general"

    # ------------------------------------------------------------------
    # LLM profile generation (Layer 2 — cache miss only)
    # ------------------------------------------------------------------

    async def _generate_profile(self, occasion_type: str, spec: MissionSpec) -> dict:
        """
        Calls the LLM to generate a need list for an unknown occasion type.
        Wrapped in asyncio.wait_for with an 8-second timeout (ADR-002).
        On any failure: returns a minimal safe profile tagged llm_fallback.
        """
        try:
            profile = await asyncio.wait_for(
                self._call_llm_for_profile(occasion_type, spec),
                timeout=8.0,
            )
            return profile
        except asyncio.TimeoutError:
            print(f"ProfileEngine WARNING: LLM timeout for '{occasion_type}' — using fallback")
        except Exception as e:
            print(f"ProfileEngine WARNING: LLM generation failed for '{occasion_type}': {e}")

        return self._make_fallback_profile(occasion_type)

    async def _call_llm_for_profile(self, occasion_type: str, spec: MissionSpec) -> dict:
        """
        Issues the actual LLM call and validates the JSON response.
        Uses the shared LLM factory — no new provider logic here.
        """
        from app.services.llm.factory import get_llm_client

        client = get_llm_client()
        if client is None:
            raise RuntimeError("No LLM provider available")

        user_message = (
            f"Generate the need list for occasion: {occasion_type}\n"
            f"Domain: {spec.domain or 'event'}\n"
            f"Typical headcount: {spec.headcount or 10}\n"
            f"Safety context: {spec.safety_context or 'none'}\n"
            f"Return ONLY the JSON array. No explanation. No markdown."
        )

        response = await client.complete(
            system_prompt=_NEED_GENERATION_SYSTEM_PROMPT,
            user_message=user_message,
            max_tokens=800,
            temperature=0.1,
        )

        raw_text = response.text.strip()

        # Strip markdown code fences if present
        if raw_text.startswith("```"):
            raw_text = re.sub(r"```[a-z]*\n?", "", raw_text).replace("```", "").strip()

        needs_raw: list = json.loads(raw_text)
        if not isinstance(needs_raw, list):
            raise ValueError("LLM returned non-list JSON")

        # Validate each need; drop invalid entries
        needs_validated = []
        for raw_need in needs_raw:
            cleaned = _validate_llm_need(raw_need, spec.safety_context)
            if cleaned is not None:
                needs_validated.append(cleaned)

        # Safety gate: must have at least one must_have
        if not any(n["priority"] == "must_have" for n in needs_validated):
            raise ValueError("LLM profile has no must_have needs after validation")

        return {
            "occasion_id": occasion_type,
            "occasion_type": occasion_type,
            "parent_occasion": self._infer_parent(occasion_type),
            "source": "llm_draft",
            "generated_by": "llm_seeded",
            "generation_confidence": 0.40,
            "feedback_count": 0,
            "community_signals": {},
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "needs": needs_validated,
        }

    def _make_fallback_profile(self, occasion_type: str) -> dict:
        """
        Returns a minimal safe profile when LLM fails or times out.
        Tries parent-keyword matching first; falls back to 3 generic needs.
        Tagged generated_by='llm_fallback' so it is distinguishable in analytics.
        """
        needs = self._parent_profile_fallback(occasion_type)
        return {
            "occasion_id": occasion_type,
            "occasion_type": occasion_type,
            "parent_occasion": self._infer_parent(occasion_type),
            "source": "llm_fallback",
            "generated_by": "llm_fallback",
            "generation_confidence": 0.20,
            "feedback_count": 0,
            "community_signals": {},
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "needs": needs,
        }

    # ------------------------------------------------------------------
    # Enrichment
    # ------------------------------------------------------------------

    def _enrich_with_community(self, profile: dict, occasion_type: str) -> dict:
        """
        Adjusts need priorities based on community_signals stored inside the
        profile dict.  Parent-occasion signal fallback is applied when the
        profile itself has no signals yet.

        Returns a new profile dict — the original is not mutated.
        """
        signals = profile.get("community_signals", {})

        # Inherit signals from parent occasion when own signals are empty
        if not signals:
            parent = profile.get("parent_occasion")
            if parent and parent in self._profiles:
                signals = self._profiles[parent].get("community_signals", {})

        if not signals:
            return profile  # nothing to enrich

        enriched = dict(profile)
        enriched["needs"] = []
        for need in profile.get("needs", []):
            need = dict(need)
            need_id = need.get("need_id", "")
            candidates = need.get("category_candidates", [need_id])
            max_signal = max((signals.get(c, 0.0) for c in candidates), default=0.0)

            if max_signal >= COMMUNITY_MUST_HAVE_THRESHOLD and need["priority"] != "must_have":
                need["priority"] = "must_have"
            elif max_signal < COMMUNITY_OPTIONAL_THRESHOLD and need["priority"] == "must_have":
                # Clamp floor prevents demotion below a threshold for critical items
                clamp = need.get("clamp_floor", 0.0)
                if max_signal >= clamp:
                    need["priority"] = "should_have"
                # If signal is still below clamp_floor, demotion is blocked

            enriched["needs"].append(need)
        return enriched

    def _enrich_with_user(
        self, profile: dict, user_id: str, occasion_type: str
    ) -> dict:
        """
        Applies per-user EWMA signals to override community-enriched priorities.
        User signal fully replaces community signal for that need (no blend).
        Returns a new profile dict.
        """
        user_occasion_signals = (
            self._user_signals
            .get(user_id, {})
            .get(occasion_type, {})
        )
        if not user_occasion_signals:
            return profile

        enriched = dict(profile)
        enriched["needs"] = []
        for need in profile.get("needs", []):
            need = dict(need)
            need_id = need.get("need_id", "")
            if need_id in user_occasion_signals:
                sig = user_occasion_signals[need_id]
                if sig >= COMMUNITY_MUST_HAVE_THRESHOLD:
                    need["priority"] = "must_have"
                elif sig >= COMMUNITY_OPTIONAL_THRESHOLD:
                    need["priority"] = "should_have"
                else:
                    need["priority"] = "optional"
            enriched["needs"].append(need)
        return enriched

    # ------------------------------------------------------------------
    # Materialisation — profile dict → list[NeedItem]
    # ------------------------------------------------------------------

    def _materialize_needs(self, profile: dict, spec: MissionSpec) -> list[NeedItem]:
        """
        Converts an enriched profile dict into the list[NeedItem] that the
        cart builder expects.  Sorted must_have → should_have → optional.
        """
        budget = spec.budget_max or 3000.0
        raw_needs = profile.get("needs", [])

        if not raw_needs:
            raw_needs = list(_GENERIC_FALLBACK_NEEDS)

        PRIORITY_ORDER = {"must_have": 0, "should_have": 1, "optional": 2}
        raw_needs = sorted(
            raw_needs,
            key=lambda n: PRIORITY_ORDER.get(n.get("priority", "optional"), 2),
        )

        result: list[NeedItem] = []
        for tmpl in raw_needs:
            try:
                need_id = tmpl.get("need_id", "unknown")
                priority = tmpl.get("priority", "should_have")
                # Default budget fractions by priority
                default_fraction = {"must_have": 0.15, "should_have": 0.10, "optional": 0.05}.get(
                    priority, 0.10
                )
                budget_fraction = float(tmpl.get("budget_fraction", default_fraction))
                result.append(
                    NeedItem(
                        need_id=need_id,
                        label=need_id.replace("_", " ").title(),
                        priority=priority,
                        category_candidates=list(tmpl.get("category_candidates", [need_id])),
                        budget_fraction=budget_fraction,
                        budget_ceiling=budget * budget_fraction * 1.5,
                        safety_tags=list(tmpl.get("safety_tags", [])),
                    )
                )
            except Exception as e:
                print(f"ProfileEngine WARNING: need materialisation failed for {tmpl}: {e}")
                continue

        if not result:
            # Absolute bottom fallback — always produces something
            for tmpl in _GENERIC_FALLBACK_NEEDS:
                result.append(
                    NeedItem(
                        need_id=tmpl["need_id"],
                        label=tmpl["need_id"].replace("_", " ").title(),
                        priority=tmpl["priority"],
                        category_candidates=list(tmpl["category_candidates"]),
                        budget_fraction=0.30,
                        budget_ceiling=budget * 0.45,
                        safety_tags=[],
                    )
                )

        return result

    # ------------------------------------------------------------------
    # Fallback helpers
    # ------------------------------------------------------------------

    def _parent_profile_fallback(self, occasion_type: str) -> list[dict]:
        """
        Returns need dicts from the closest matching existing profile.
        Used when LLM generation fails and no taxonomy entry exists.
        """
        ot_lower = occasion_type.lower()
        for keyword, parent_type in _PARENT_KEYWORD_MAP.items():
            if keyword in ot_lower and parent_type in self._profiles:
                return list(self._profiles[parent_type].get("needs", []))

        # Last resort: first available profile, or hardcoded generic
        if self._profiles:
            return list(next(iter(self._profiles.values())).get("needs", []))
        return list(_GENERIC_FALLBACK_NEEDS)

    def _infer_parent(self, occasion_type: str) -> Optional[str]:
        """Infers a parent occasion string for LLM-generated profiles."""
        ot_lower = occasion_type.lower()
        for keyword, parent in _PARENT_INFER_MAP.items():
            if keyword in ot_lower:
                return parent
        return None

    # ------------------------------------------------------------------
    # Feedback — synchronous in-memory update (ADR-005)
    # ------------------------------------------------------------------

    def record_feedback(
        self,
        user_id: str,
        occasion_type: str,
        kept_asins: list[str],
        removed_asins: list[str],
        added_asins: list[str],
    ) -> None:
        """
        Synchronous in-memory EWMA update.  Called directly in the approve
        request handler before returning the response.  Takes < 1 ms.
        Does NOT write to disk — call flush_feedback() as a BackgroundTask.

        kept_asins / removed_asins / added_asins are treated as need_id strings
        (the caller passes need_ids, not ASINs, despite the parameter names
        preserved from the task spec for interface compatibility).
        """
        event_id = _make_event_id(user_id, occasion_type)
        if event_id in self._seen_event_ids:
            return  # idempotent within the same minute
        self._seen_event_ids.add(event_id)

        self._update_user_signals(user_id, occasion_type, kept_asins, removed_asins, added_asins)
        self._update_community_signals(occasion_type, kept_asins, removed_asins, added_asins)

        # Increment feedback_count and promote llm_draft → community_validated at 5
        profile = self._profiles.get(occasion_type)
        if profile:
            profile["feedback_count"] = profile.get("feedback_count", 0) + 1
            profile["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            if (
                profile.get("feedback_count", 0) >= 5
                and profile.get("source") == "llm_draft"
            ):
                profile["source"] = "community_validated"
                profile["generated_by"] = "community_validated"

        self._feedback_buffer.append({
            "event_id": event_id,
            "user_id": user_id,
            "occasion_type": occasion_type,
            "kept": kept_asins,
            "removed": removed_asins,
            "added": added_asins,
            "timestamp": time.time(),
        })

    def _update_user_signals(
        self,
        user_id: str,
        occasion_type: str,
        kept: list[str],
        removed: list[str],
        added: list[str],
    ) -> None:
        """Applies asymmetric EWMA to per-user signals (ADR-003)."""
        if user_id not in self._user_signals:
            self._user_signals[user_id] = {}
        if occasion_type not in self._user_signals[user_id]:
            self._user_signals[user_id][occasion_type] = {}

        sigs = self._user_signals[user_id][occasion_type]

        for need_id in kept:
            current = sigs.get(need_id, 0.5)
            sigs[need_id] = round(current * (1 - ALPHA_POSITIVE) + 1.0 * ALPHA_POSITIVE, 3)

        for need_id in removed:
            current = sigs.get(need_id, 0.5)
            sigs[need_id] = round(current * (1 - ALPHA_NEGATIVE) + 0.0 * ALPHA_NEGATIVE, 3)

        for need_id in added:
            current = sigs.get(need_id, 0.0)
            sigs[need_id] = round(current * (1 - ALPHA_ADDED) + 1.0 * ALPHA_ADDED, 3)
            # Append as an optional discovered need if the profile doesn't already have it
            self._add_discovered_need(occasion_type, need_id)

    def _update_community_signals(
        self,
        occasion_type: str,
        kept: list[str],
        removed: list[str],
        added: list[str],
    ) -> None:
        """Updates the community_signals dict inside the profile (not user-specific)."""
        profile = self._profiles.get(occasion_type)
        if not profile:
            return
        sigs = profile.setdefault("community_signals", {})

        for need_id in kept:
            sigs[need_id] = round(
                sigs.get(need_id, 0.5) * (1 - ALPHA_POSITIVE) + 1.0 * ALPHA_POSITIVE, 3
            )

        for need_id in removed:
            current = sigs.get(need_id, 0.5)
            new_val = round(current * (1 - ALPHA_NEGATIVE) + 0.0 * ALPHA_NEGATIVE, 3)
            # Respect clamp_floor to prevent feedback poisoning on critical needs
            clamp = 0.0
            for n in profile.get("needs", []):
                if n.get("need_id") == need_id:
                    clamp = float(n.get("clamp_floor", 0.0))
                    break
            sigs[need_id] = max(new_val, clamp)

        for need_id in added:
            sigs[need_id] = round(
                sigs.get(need_id, 0.0) * (1 - ALPHA_ADDED) + 1.0 * ALPHA_ADDED, 3
            )

    def _add_discovered_need(self, occasion_type: str, need_id: str) -> None:
        """
        When a user manually adds a need the profile didn't have, append it as
        optional.  This is the need discovery signal — the most valuable input
        in the feedback loop.
        """
        profile = self._profiles.get(occasion_type)
        if not profile:
            return
        existing_ids = {n.get("need_id") for n in profile.get("needs", [])}
        if need_id not in existing_ids:
            profile.setdefault("needs", []).append({
                "need_id": need_id,
                "priority": "optional",
                "qty_formula": "1",
                "category_candidates": [need_id],
                "clamp_floor": 0.0,
                "notes": f"Discovered via user addition — community signal: {ALPHA_ADDED}",
                "discovered_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "budget_fraction": 0.05,
            })

    # ------------------------------------------------------------------
    # Flush  (call as BackgroundTask after returning the approve response)
    # ------------------------------------------------------------------

    def flush_feedback(self) -> None:
        """
        Atomically writes user signals and LLM-generated profile cache to disk.
        Checks flush conditions (N events or T seconds) before writing.
        Simple boolean guard prevents re-entrant writes (ADR-004).
        """
        now = time.time()
        should_flush = (
            len(self._feedback_buffer) >= FLUSH_EVERY_N
            or (now - self._last_flush_time) > FLUSH_EVERY_SECONDS
        )
        if not should_flush or self._flush_in_progress:
            return

        self._flush_in_progress = True
        try:
            # Write LLM-generated profiles only (taxonomy is read-only at runtime)
            cache_profiles = [
                p for p in self._profiles.values()
                if p.get("source") in ("llm_draft", "community_validated", "llm_runtime", "llm_fallback")
            ]
            _atomic_write_json(CACHE_PATH, cache_profiles)
            _atomic_write_json(USER_SIGNALS_PATH, self._user_signals)

            self._feedback_buffer.clear()
            self._last_flush_time = time.time()
        except Exception as e:
            print(f"ProfileEngine WARNING: disk flush failed (non-fatal): {e}")
        finally:
            self._flush_in_progress = False

    async def _persist_cache(self) -> None:
        """Async wrapper for flush_feedback — called via asyncio.create_task."""
        await asyncio.to_thread(self.flush_feedback)

    def _save_runtime_profile(self, occasion_type: str, profile: dict) -> None:
        """
        Atomic write of the profiles cache after a single new profile is generated.
        Loads existing cache, updates the key, rewrites the entire file atomically.
        """
        try:
            existing: list = []
            if CACHE_PATH.exists():
                with open(CACHE_PATH, encoding="utf-8") as f:
                    existing = json.load(f)
                if not isinstance(existing, list):
                    existing = []
            # Replace or append
            existing = [e for e in existing if e.get("occasion_type") != occasion_type]
            existing.append(profile)
            _atomic_write_json(CACHE_PATH, existing)
        except Exception as e:
            print(f"ProfileEngine WARNING: _save_runtime_profile failed (non-fatal): {e}")


# ---------------------------------------------------------------------------
# Module-level singleton  (same pattern as community_engine.py)
# ---------------------------------------------------------------------------

profile_engine = ProfileEngine()
