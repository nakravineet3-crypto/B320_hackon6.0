from app.services.adapters.base import BaseAdapter
from app.models.mission import MissionSpec, NeedItem
from typing import List


class TravelAdapter(BaseAdapter):
    def get_needs(self, spec: MissionSpec) -> List[NeedItem]:
        return [
            self._make_need("water", "Water bottles", "must_have",
                           ["water_bottle", "water_bottle_steel"], 0.15),
            self._make_need("first_aid", "First aid kit", "must_have",
                           ["first_aid", "first_aid_kit"], 0.10),
            self._make_need("bag", "Backpack", "must_have",
                           ["backpack", "trekking_backpack"], 0.30),
            self._make_need("footwear", "Trekking socks", "should_have",
                           ["trekking_socks", "socks"], 0.10),
            self._make_need("lighting", "Torch / headlamp", "should_have",
                           ["torch", "headlamp", "led_torch"], 0.10),
            self._make_need("rain", "Rain protection", "should_have",
                           ["rain_jacket", "raincoat", "poncho"], 0.15),
            self._make_need("energy", "Energy snacks", "optional",
                           ["energy_bar", "protein_bar", "snacks"], 0.10),
        ]
