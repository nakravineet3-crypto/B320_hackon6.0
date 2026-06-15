import json
from pathlib import Path
from uuid import uuid4
from datetime import datetime

DATA_PATH = Path(__file__).parent.parent / "data"


def load_hive_data() -> dict:
    path = DATA_PATH / "hive_data.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {"hives": [], "carts": [], "messages": [], "orders": []}


def save_hive_data(data: dict):
    path = DATA_PATH / "hive_data.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_cart_total(items: list) -> float:
    return sum(i["price"] * i["quantity"] for i in items)


def get_vote_score(item: dict) -> int:
    return sum(v["value"] for v in item.get("votes", []))


def get_member_map() -> dict:
    return {
        "U001": {"name": "Sneha", "color": "#FF9900", "letter": "S"},
        "U002": {"name": "Riya", "color": "#007185", "letter": "R"},
        "U003": {"name": "Arjun", "color": "#007600", "letter": "A"},
        "U004": {"name": "Kabir", "color": "#CC0C39", "letter": "K"},
        "system": {"name": "MissionCart", "color": "#565959", "letter": "M"},
    }


def run_optimizer(cart: dict, budget_cap: float) -> dict:
    """Rule-based budget optimizer. Three rules in priority order."""
    items = list(cart["items"])
    actions = []
    total_saved = 0

    # RULE 1: Remove items with vote_score <= -2
    to_remove = []
    for item in items:
        score = get_vote_score(item)
        if score <= -2:
            saved = item["price"] * item["quantity"]
            to_remove.append(item["item_id"])
            actions.append({
                "action_type": "remove",
                "item_id": item["item_id"],
                "title": item["title"],
                "reason": f"Low votes — {score} net vote. Group doesn't want this.",
                "saved": saved,
                "icon": "thumbs-down-outline",
            })
            total_saved += saved
    items = [i for i in items if i["item_id"] not in to_remove]

    # RULE 2: Swap multiple small Coke to family pack
    coke_items = [
        i for i in items
        if "coke" in i["title"].lower()
        or "coca-cola" in i["title"].lower()
        or "cola" in i["title"].lower()
    ]
    if coke_items:
        total_coke_cost = sum(i["price"] * i["quantity"] for i in coke_items)
        family_pack_price = 89
        if total_coke_cost > family_pack_price * 1.2:
            saved = total_coke_cost - family_pack_price
            for coke in coke_items:
                items = [i for i in items if i["item_id"] != coke["item_id"]]
            items.append({
                "item_id": str(uuid4()),
                "asin": "MC_COKE_FAMILY_001",
                "title": "Coca-Cola 2L Family Pack",
                "category": "beverages",
                "price": family_pack_price,
                "quantity": 1,
                "added_by": "system",
                "note": "Swapped by Hive optimizer",
                "status": "approved",
                "votes": [],
                "is_optimizer_addition": True,
            })
            actions.append({
                "action_type": "swap",
                "title": "Coca-Cola 500ml × 4",
                "new_title": "Coca-Cola 2L Family Pack",
                "reason": (
                    f"4 bottles (₹{total_coke_cost:.0f}) → "
                    f"2L family pack (₹{family_pack_price}). "
                    f"More volume, lower cost."
                ),
                "saved": round(saved, 2),
                "icon": "swap-horizontal-outline",
            })
            total_saved += saved

    # RULE 3: Remove exact duplicate ASINs
    seen_asins = {}
    to_remove_dupes = []
    for item in items:
        asin = item["asin"]
        if asin in seen_asins:
            saved = item["price"] * item["quantity"]
            to_remove_dupes.append(item["item_id"])
            actions.append({
                "action_type": "remove_duplicate",
                "item_id": item["item_id"],
                "title": item["title"],
                "reason": (
                    f"Duplicate — already added by "
                    f"{get_member_map().get(seen_asins[asin], {}).get('name', 'another member')}."
                ),
                "saved": saved,
                "icon": "copy-outline",
            })
            total_saved += saved
        else:
            seen_asins[asin] = item["added_by"]
    items = [i for i in items if i["item_id"] not in to_remove_dupes]

    new_total = get_cart_total(items)
    original_total = get_cart_total(cart["items"])

    return {
        "original_total": round(original_total, 2),
        "optimized_total": round(new_total, 2),
        "total_saved": round(total_saved, 2),
        "actions": actions,
        "optimized_items": items,
        "under_budget": new_total <= budget_cap,
        "budget_cap": budget_cap,
        "budget_remaining": round(budget_cap - new_total, 2),
    }


def calculate_split(items: list, members: list, method: str = "equal") -> dict:
    """Calculate payment split."""
    total = get_cart_total(items)
    n = len(members)
    member_map = get_member_map()

    if method == "proportional":
        added_costs = {m["user_id"]: 0.0 for m in members}
        for item in items:
            added_by = item.get("added_by", "")
            if added_by in added_costs:
                added_costs[added_by] += item["price"] * item["quantity"]
            else:
                split_amount = (item["price"] * item["quantity"]) / n
                for uid in added_costs:
                    added_costs[uid] += split_amount

        shares = []
        for m in members:
            uid = m["user_id"]
            shares.append({
                "user_id": uid,
                "display_name": member_map.get(uid, {}).get("name", "Member"),
                "avatar_color": member_map.get(uid, {}).get("color", "#565959"),
                "avatar_letter": member_map.get(uid, {}).get("letter", "?"),
                "amount": round(added_costs.get(uid, 0), 2),
                "status": "pending",
            })

        return {
            "method": "proportional",
            "total": round(total, 2),
            "member_count": n,
            "per_person": round(total / n, 2),
            "shares": shares,
        }

    # Default: equal split
    per_person = round(total / n, 2)
    shares = []
    running = 0
    for i, m in enumerate(members):
        if i == len(members) - 1:
            amount = round(total - running, 2)
        else:
            amount = per_person
        running += amount
        uid = m["user_id"]
        shares.append({
            "user_id": uid,
            "display_name": member_map.get(uid, {}).get("name", "Member"),
            "avatar_color": member_map.get(uid, {}).get("color", "#565959"),
            "avatar_letter": member_map.get(uid, {}).get("letter", "?"),
            "amount": amount,
            "status": "pending",
        })

    return {
        "method": "equal",
        "total": round(total, 2),
        "member_count": n,
        "per_person": per_person,
        "shares": shares,
    }
