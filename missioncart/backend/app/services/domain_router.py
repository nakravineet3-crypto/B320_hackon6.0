import json
import os
from app.models.mission import MissionSpec, NeedItem
from app.services.adapters.event_adapter import EventAdapter
from app.services.adapters.home_adapter import HomeSetupAdapter
from app.services.adapters.travel_adapter import TravelAdapter
from app.services.adapters.grocery_adapter import GroceryAdapter
from typing import List

ADAPTER_MAP = {
    "event": EventAdapter,
    "home_setup": HomeSetupAdapter,
    "travel": TravelAdapter,
    "travel_prep": TravelAdapter,
    "electronics": HomeSetupAdapter,
    "baby_care": EventAdapter,
    "pet_care": EventAdapter,
    "seasonal": EventAdapter,
    "grocery": GroceryAdapter,
    "general": EventAdapter,
}

# Load occasion_need_taxonomy at module level — fail silently, never crash startup
OCCASION_TAXONOMY: dict = {}
try:
    _taxonomy_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'occasion_need_taxonomy.json')
    with open(_taxonomy_path, encoding='utf-8') as _f:
        OCCASION_TAXONOMY = json.load(_f)
except Exception:
    pass

# Priority string → float (matches NeedItem.priority convention)
_PRIORITY_MAP = {
    "must_have": 1.0,
    "should_have": 0.6,
    "optional": 0.3,
}


def _get_occasion_needs(occasion_type: str, spec: MissionSpec) -> List[NeedItem]:
    """
    Build a NeedItem list from occasion_need_taxonomy.json for the given occasion.
    Returns an empty list if the occasion is not in the taxonomy — caller falls through
    to the adapter path in that case.
    """
    occasions = OCCASION_TAXONOMY.get('occasions', {})
    occ = occasions.get(occasion_type)
    if not occ:
        return []

    needs: List[NeedItem] = []
    for raw in occ.get('needs', []):
        priority_str = raw.get('priority', 'optional')
        priority_float = _PRIORITY_MAP.get(priority_str, 0.3)
        category_candidates = raw.get('category_candidates', [])
        if not category_candidates:
            continue

        need = NeedItem(
            need_id=raw.get('need_id', category_candidates[0]),
            label=raw.get('need_id', category_candidates[0]).replace('_', ' ').title(),
            priority=priority_str,
            category_candidates=category_candidates,
            budget_fraction=priority_float / 3.0,  # proportional slice of total budget
            reason=raw.get('notes', ''),
        )
        needs.append(need)
    return needs


_FESTIVAL_OCCASION_ALIASES = {
    "diwali": "diwali_celebration",
    "diwali_celebration": "diwali_celebration",
    "festival": "diwali_celebration",
    "holi": "holi_celebration",
    "holi_celebration": "holi_celebration",
    "navratri": "navratri",
    "dussehra": "dussehra",
    "onam": "onam",
    "grihapravesh": "grihapravesh",
    "housewarming": "grihapravesh",
    "travel_trek": "travel_trek",
    "trek": "travel_trek",
}


def route_and_decompose(spec: MissionSpec) -> List[NeedItem]:
    # Try taxonomy-based needs first (precise occasion decomposition)
    raw_occasion = getattr(spec, 'occasion', None) or ''
    occasion_type = _FESTIVAL_OCCASION_ALIASES.get(raw_occasion.lower(), raw_occasion)
    taxonomy_needs = _get_occasion_needs(occasion_type, spec)

    if taxonomy_needs:
        needs = taxonomy_needs
    else:
        # Fall through to domain adapter (handles domains not in taxonomy)
        adapter_class = ADAPTER_MAP.get(spec.domain, EventAdapter)
        adapter = adapter_class()
        needs = adapter.get_needs(spec)

    # Apply budget ceilings
    if spec.budget_max:
        for need in needs:
            need.budget_ceiling = spec.budget_max * need.budget_fraction * 1.5

    return needs
