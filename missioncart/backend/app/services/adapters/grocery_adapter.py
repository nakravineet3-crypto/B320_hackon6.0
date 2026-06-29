from app.services.adapters.base import BaseAdapter
from app.models.mission import MissionSpec, NeedItem
from typing import List


class GroceryAdapter(BaseAdapter):
    def get_needs(self, spec: MissionSpec) -> List[NeedItem]:
        return [
            self._make_need("staples", "Staples & grains", "must_have",
                           ["atta", "rice", "dal", "cooking_oil", "sugar"], 0.30),
            self._make_need("beverages", "Beverages & snacks", "should_have",
                           ["tea", "juice", "soda", "water", "biscuits", "chips", "namkeen"], 0.20),
            self._make_need("dairy", "Dairy & fresh", "must_have",
                           ["dairy", "milk", "eggs", "bread", "bakery"], 0.20),
            self._make_need("cleaning", "Cleaning supplies", "should_have",
                           ["detergent", "dishwash", "toilet_cleaner", "soap"], 0.15),
            self._make_need("personal_care", "Personal care", "optional",
                           ["shampoo", "toothpaste", "body_wash", "face_wash"], 0.10),
            self._make_need("condiments", "Condiments & sauces", "optional",
                           ["chocolates", "ketchup", "spices", "salt", "vinegar"], 0.05),
        ]
