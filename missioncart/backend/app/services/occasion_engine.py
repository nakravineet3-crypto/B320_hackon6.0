"""
Occasion Intelligence Engine — computes relevance scores and ranked feed.
All scoring is deterministic. No LLM calls. Runs at startup and on each request.
"""
import json
import os
from datetime import date
from typing import Optional

_DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')


def _load_json(filename):
    path = os.path.join(_DATA_DIR, filename)
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


OCCASION_CALENDAR = _load_json('occasion_calendar.json').get('occasions', [])

# Identity affinity scores per occasion_type per cluster
_IDENTITY_AFFINITY = {
    'diwali_celebration': {
        'home_chef': 0.9,
        'office_gym_dad': 0.7,
        'college_girl': 0.8,
        'jee_student': 0.6,
    },
    'holi_celebration': {
        'college_girl': 1.0,
        'jee_student': 0.9,
        'office_gym_dad': 0.6,
        'home_chef': 0.7,
    },
    'office_potluck': {
        'office_gym_dad': 1.0,
        'college_girl': 0.7,
        'jee_student': 0.5,
        'home_chef': 0.6,
    },
    'kids_birthday': {
        'home_chef': 0.9,
        'office_gym_dad': 0.8,
        'college_girl': 0.6,
        'jee_student': 0.4,
    },
    'grihapravesh': {
        'home_chef': 1.0,
        'office_gym_dad': 0.8,
        'college_girl': 0.7,
        'jee_student': 0.5,
    },
    'travel_trek': {
        'office_gym_dad': 1.0,
        'jee_student': 0.8,
        'college_girl': 0.7,
        'home_chef': 0.5,
    },
    'raksha_bandhan': {
        'college_girl': 1.0,
        'home_chef': 0.9,
        'office_gym_dad': 0.8,
        'jee_student': 0.7,
    },
    'onam': {
        'home_chef': 0.9,
        'college_girl': 0.7,
        'office_gym_dad': 0.6,
        'jee_student': 0.5,
    },
    'navratri': {
        'home_chef': 0.9,
        'college_girl': 0.8,
        'office_gym_dad': 0.6,
        'jee_student': 0.5,
    },
    'dussehra': {
        'home_chef': 0.8,
        'office_gym_dad': 0.7,
        'college_girl': 0.7,
        'jee_student': 0.6,
    },
}


def _compute_days_until(occ: dict) -> Optional[int]:
    date_str = occ.get('date')
    if not date_str:
        return None
    try:
        event_date = date.fromisoformat(date_str)
        today = date.today()
        delta = (event_date - today).days
        return delta if delta >= 0 else None
    except Exception:
        return None


def _temporal_signal(days_until: Optional[int], occ: dict) -> float:
    """Score 0-1 based on how close the occasion is."""
    if days_until is None:
        # Recurring occasions (birthday, potluck, grihapravesh, travel) are always
        # moderately relevant — not date-bound.
        return 0.5

    discovery = occ.get('discovery_days_before', 30)
    prep = occ.get('prep_days_before', 7)
    last_min = occ.get('last_minute_days_before', 2)

    if days_until > discovery:
        return 0.0  # too far out, not shown
    elif days_until > prep:
        # Discovery window: score 0.2 → 0.5
        frac = (discovery - days_until) / (discovery - prep)
        return 0.2 + 0.3 * frac
    elif days_until > last_min:
        # Preparation window: score 0.5 → 0.9
        frac = (prep - days_until) / max(prep - last_min, 1)
        return 0.5 + 0.4 * frac
    elif days_until >= 0:
        # Last minute / day-of: 1.0
        return 1.0
    else:
        return 0.0  # past


def get_occasion_feed(cluster_id: Optional[str] = None, limit: int = 6) -> list:
    """
    Return ranked occasion cards for the feed.

    cluster_id: identity group of the user (optional, for identity_signal weighting).
    limit: maximum number of cards to return.

    Sorting: date-bound occasions ordered by days_until ascending (soonest first),
    followed by recurring occasions ordered by relevance_score descending.
    """
    results = []

    for occ in OCCASION_CALENDAR:
        days_until = _compute_days_until(occ)
        temporal = _temporal_signal(days_until, occ)

        # Skip date-bound occasions that are outside their discovery window
        if occ.get('date') and (days_until is None or temporal == 0.0):
            continue

        # Identity signal lookup — default neutral 0.5 if cluster unknown
        identity_signal = 0.5
        if cluster_id:
            affinity = _IDENTITY_AFFINITY.get(occ['occasion_type'], {})
            identity_signal = affinity.get(cluster_id, 0.5)

        # Final relevance score (weights must sum to 1.0)
        # temporal: 0.45  history_signal: 0.25 (fixed 0.5 — no per-user history)
        # identity: 0.20  community_signal: 0.10 (fixed 0.7 — high adoption default)
        relevance = (
            0.45 * temporal
            + 0.25 * 0.5
            + 0.20 * identity_signal
            + 0.10 * 0.7
        )

        # Urgency state and label
        if days_until is None:
            urgency_state = 'preparation'
            urgency_label = 'Plan ahead'
        elif days_until > 59:
            urgency_state = 'discovery'
            urgency_label = f'{days_until} days · Plan ahead'
        elif days_until > 13:
            urgency_state = 'preparation'
            urgency_label = f'{days_until} days · Time to start'
        elif days_until > 0:
            urgency_state = 'urgent'
            urgency_label = f"{days_until} days · Don't wait"
        else:
            urgency_state = 'emergency'
            urgency_label = 'TODAY · Amazon Now in 20 min'

        results.append({
            'occasion_type': occ['occasion_type'],
            'title': occ['display_name'],
            'emoji': occ['emoji'],
            'days_until': days_until,
            'urgency_state': urgency_state,
            'urgency_label': urgency_label,
            'estimated_budget': occ['estimated_budget_inr'],
            'headcount': occ['headcount_default'],
            'community_signal': occ['community_signal'],
            'tap_goal': occ['tap_goal'],
            'relevance_score': round(relevance, 3),
        })

    # Sort: date-bound by days_until ascending, recurring by relevance_score descending
    date_bound = sorted(
        [r for r in results if r['days_until'] is not None],
        key=lambda x: x['days_until'],
    )
    recurring = sorted(
        [r for r in results if r['days_until'] is None],
        key=lambda x: -x['relevance_score'],
    )

    return (date_bound + recurring)[:limit]
