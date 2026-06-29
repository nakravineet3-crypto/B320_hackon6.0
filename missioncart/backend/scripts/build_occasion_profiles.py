"""
build_occasion_profiles.py
--------------------------
Reads occasion_need_taxonomy.json and community_insights.json.
Populates community_signal on every need in the taxonomy by matching
category_candidates against adoption_rate data in community_insights.

Then applies three priority-promotion rules (per architecture ADR):
  community_signal >= 0.90  -> force must_have
  community_signal >= 0.65  -> keep or upgrade to should_have
  community_signal <  0.40  -> downgrade to optional

Outputs:
  1. occasion_need_taxonomy.json  (in-place update of community_signal fields only)
  2. community_need_signals.json  (flat lookup: {occasion_id: {need_id: signal_float}})

Run from backend/ directory:
  python scripts/build_occasion_profiles.py
"""

import json
import os
import sys
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
BACKEND_DIR = Path(__file__).parent.parent
DATA_DIR = BACKEND_DIR / "app" / "data"

TAXONOMY_PATH         = DATA_DIR / "occasion_need_taxonomy.json"
COMMUNITY_INSIGHTS    = DATA_DIR / "community_insights.json"
OUTPUT_SIGNALS_PATH   = DATA_DIR / "community_need_signals.json"

# ── Priority promotion thresholds (ADR-003 / architecture Section 3) ───────────
THRESHOLD_MUST_HAVE   = 0.90
THRESHOLD_SHOULD_HAVE = 0.65
THRESHOLD_OPTIONAL    = 0.40   # below this → downgrade to optional

# ── Occasion name aliases ──────────────────────────────────────────────────────
# Maps taxonomy occasion_id to community_insights occasion keys.
# community_insights uses some different keys (e.g. "travel_prep" vs "travel_trek").
OCCASION_ALIAS_MAP = {
    "travel_trek":          "travel_prep",
    "diwali_celebration":   "festival",
    "holi_celebration":     "festival",
    "office_potluck":       "office_event",
    "baby_shower":          "office_farewell",   # no direct match; office_farewell has plates/cups
    "monsoon_prep":         None,                # no community data available
    "cricket_viewing_party": "office_event",     # closest structural match
}


def load_json(path: Path) -> dict:
    if not path.exists():
        print(f"ERROR: file not found: {path}")
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_adoption_map(community_insights: dict) -> dict[str, dict[str, float]]:
    """
    Builds a dict: {occasion_key: {category: adoption_rate}} from community_insights.
    Covers both the "occasions" block and the flat top-level items.
    """
    adoption: dict[str, dict[str, float]] = {}
    occasions_block = community_insights.get("occasions", {})
    for occ_key, occ_data in occasions_block.items():
        cat_signals: dict[str, float] = {}
        for item in occ_data.get("top_items", []):
            cat = item.get("category", "")
            rate = item.get("adoption_rate", 0.0)
            if cat:
                cat_signals[cat] = rate
        adoption[occ_key] = cat_signals
    return adoption


def resolve_signal_for_need(
    need: dict,
    occasion_adoption: dict[str, float],
) -> float:
    """
    Returns the highest adoption_rate found across all category_candidates for this need.
    occasion_adoption is {category: float} for the resolved occasion.
    Falls back to 0.0 if no candidate matches.
    """
    best = 0.0
    for cat in need.get("category_candidates", []):
        rate = occasion_adoption.get(cat, 0.0)
        if rate > best:
            best = rate
    return round(best, 4)


def promote_priority(original: str, signal: float) -> str:
    """
    Applies signal-based priority promotion/demotion.
    Rules from architecture Section 3 Task 2:
      signal >= 0.90 → must_have
      signal >= 0.65 → should_have (upgrade if below, don't demote if already must_have)
      signal <  0.40 → optional (downgrade)
      0.40 <= signal < 0.65 → keep original
    """
    if signal == 0.0:
        # No community data — leave priority unchanged
        return original

    if signal >= THRESHOLD_MUST_HAVE:
        return "must_have"

    if signal >= THRESHOLD_SHOULD_HAVE:
        # Upgrade optional → should_have; never demote must_have
        if original == "optional":
            return "should_have"
        return original  # keep must_have or should_have as-is

    if signal < THRESHOLD_OPTIONAL:
        # Downgrade to optional — but respect clamp_floor in taxonomy
        # (clamp enforcement is in ProfileEngine; here we record the signal faithfully)
        return "optional"

    # 0.40 <= signal < 0.65: keep original
    return original


def build_profiles() -> None:
    print("=" * 60)
    print("build_occasion_profiles.py — Community Signal Builder")
    print("=" * 60)

    taxonomy      = load_json(TAXONOMY_PATH)
    community     = load_json(COMMUNITY_INSIGHTS)
    adoption_map  = get_adoption_map(community)

    occasions: dict = taxonomy.get("occasions", {})
    if not occasions:
        print("ERROR: taxonomy has no 'occasions' block")
        sys.exit(1)

    flat_signals: dict[str, dict[str, float]] = {}  # output community_need_signals.json
    summary_rows: list[tuple] = []

    for occ_id, profile in occasions.items():
        # Resolve the community_insights key for this occasion
        alias = OCCASION_ALIAS_MAP.get(occ_id, occ_id)
        occasion_adoption: dict[str, float] = {}
        if alias and alias in adoption_map:
            occasion_adoption = adoption_map[alias]
        elif occ_id in adoption_map:
            occasion_adoption = adoption_map[occ_id]
        # else: no community data → all signals stay 0.0

        needs = profile.get("needs", [])
        occ_flat_signals: dict[str, float] = {}
        high_signal_count = 0
        low_signal_count  = 0

        for need in needs:
            need_id  = need.get("need_id", "")
            signal   = resolve_signal_for_need(need, occasion_adoption)

            # Write signal back into the need dict (in-place update)
            need["community_signal"] = signal

            # Apply priority promotion based on signal
            original_priority      = need.get("priority", "should_have")
            promoted_priority      = promote_priority(original_priority, signal)
            need["priority"]       = promoted_priority

            occ_flat_signals[need_id] = signal

            if signal >= 0.65:
                high_signal_count += 1
            else:
                low_signal_count += 1

        flat_signals[occ_id] = occ_flat_signals
        summary_rows.append((occ_id, high_signal_count, low_signal_count, alias or "NO_DATA"))

    # Write updated taxonomy back (community_signal and promoted priority fields only)
    with open(TAXONOMY_PATH, "w", encoding="utf-8") as f:
        json.dump(taxonomy, f, indent=2, ensure_ascii=False)
    print(f"\nUpdated: {TAXONOMY_PATH}")

    # Write flat community_need_signals.json
    with open(OUTPUT_SIGNALS_PATH, "w", encoding="utf-8") as f:
        json.dump(flat_signals, f, indent=2, ensure_ascii=False)
    print(f"Written: {OUTPUT_SIGNALS_PATH}")

    # Print summary
    print("\n" + "-" * 70)
    print(f"{'Occasion':<30} {'High (>=0.65)':>14} {'Below (<0.65)':>14}  Community source")
    print("-" * 70)
    for occ_id, high, low, src in summary_rows:
        print(f"{occ_id:<30} {high:>14} {low:>14}  {src}")
    print("-" * 70)

    total_high = sum(r[1] for r in summary_rows)
    total_low  = sum(r[2] for r in summary_rows)
    print(f"{'TOTAL':<30} {total_high:>14} {total_low:>14}")
    print()

    # Validation pass — warn about zero-signal occasions
    no_data_occasions = [r[0] for r in summary_rows if r[3] == "NO_DATA"]
    if no_data_occasions:
        print("WARNING: No community data found for these occasions:")
        for occ in no_data_occasions:
            print(f"  - {occ}  (taxonomy priorities used unchanged)")
    else:
        print("All occasions resolved to community data sources.")

    print("\nDone.")


if __name__ == "__main__":
    build_profiles()
