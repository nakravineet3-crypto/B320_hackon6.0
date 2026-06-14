from app.models.mission import MissionSpec, NeedItem
from app.services.adapters.event_adapter import EventAdapter
from app.services.adapters.home_adapter import HomeSetupAdapter
from app.services.adapters.travel_adapter import TravelAdapter
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
    "general": EventAdapter,
}


def route_and_decompose(spec: MissionSpec) -> List[NeedItem]:
    adapter_class = ADAPTER_MAP.get(spec.domain, EventAdapter)
    adapter = adapter_class()
    needs = adapter.get_needs(spec)

    # Apply budget ceilings
    if spec.budget_max:
        for need in needs:
            need.budget_ceiling = spec.budget_max * need.budget_fraction * 1.5

    return needs
