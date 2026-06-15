"""
Community prior modifier. Simulation-based, always disclosed.
Narrow range [0.95, 1.05] — cannot swing winners significantly.
"""

import json
from pathlib import Path

_STATS_PATH = Path(__file__).parent.parent.parent / "data" / "community_stats.json"
_COMMUNITY_STATS = {}
try:
    with open(_STATS_PATH, encoding="utf-8") as f:
        _COMMUNITY_STATS = json.load(f)
except Exception:
    pass


def apply_evidence(
    mission_fit_score: float,
    category: str,
    occasion_type: str,
) -> dict:
    """Apply community prior modifier.

    Modifier range: [0.95, 1.05] — deliberately narrow.
    Simulated data should not swing the winner.
    """
    # Look up adoption rate
    adoption_rate = None
    occ_data = _COMMUNITY_STATS.get(occasion_type, {})
    categories = occ_data.get("categories", {})
    cat_data = categories.get(category, {})
    adoption_rate = cat_data.get("adoption_rate", None)

    # Compute modifier
    if adoption_rate is not None:
        modifier = 0.95 + (adoption_rate * 0.10)
    else:
        modifier = 1.0  # no data, no modification

    # Clamp to [0.95, 1.05]
    modifier = max(0.95, min(1.05, modifier))

    evidence_adjusted_score = mission_fit_score * modifier

    return {
        "evidence_adjusted_score": round(evidence_adjusted_score, 4),
        "adoption_rate": adoption_rate,
        "modifier": round(modifier, 4),
        "simulated_data": True,
        "evidence_note": "Simulation-based prior from community session analysis",
    }
