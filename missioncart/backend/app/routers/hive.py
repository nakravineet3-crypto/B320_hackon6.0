"""Amazon Hives — collaborative group shopping cart with voting and optimization."""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from uuid import uuid4
import time

router = APIRouter()

# ── DEMO DATA ─────────────────────────────────────────────────────────────────

MEMBERS = [
    {"user_id": "U001", "name": "Sneha", "letter": "S", "color": "#FF9900"},
    {"user_id": "U002", "name": "Riya", "letter": "R", "color": "#007185"},
    {"user_id": "U003", "name": "Arjun", "letter": "A", "color": "#007600"},
    {"user_id": "U004", "name": "Karan", "letter": "K", "color": "#CC0C39"},
]

CART_ITEMS = [
    {"item_id": "HI001", "asin": "B0PARTY001", "title": "Disposable Paper Plates 25pc", "category": "plates", "price": 89, "quantity": 2, "added_by": "U001", "added_by_name": "Sneha", "added_by_letter": "S", "added_by_color": "#FF9900", "note": "For cake + snacks", "votes": [{"user_id": "U001", "value": 1}, {"user_id": "U002", "value": 1}, {"user_id": "U003", "value": 1}], "vote_score": 3, "status": "approved"},
    {"item_id": "HI002", "asin": "B0PARTY013", "title": "Multicolor Balloon Set 50pc", "category": "balloon_set", "price": 199, "quantity": 2, "added_by": "U002", "added_by_name": "Riya", "added_by_letter": "R", "added_by_color": "#007185", "note": "Big balloons for entrance", "votes": [{"user_id": "U001", "value": 1}, {"user_id": "U002", "value": 1}, {"user_id": "U004", "value": 1}], "vote_score": 3, "status": "approved"},
    {"item_id": "HI003", "asin": "B0PARTY019", "title": "Balloon Hand Pump", "category": "balloon_pump", "price": 99, "quantity": 1, "added_by": "U002", "added_by_name": "Riya", "added_by_letter": "R", "added_by_color": "#007185", "note": "", "votes": [{"user_id": "U002", "value": 1}, {"user_id": "U003", "value": 1}], "vote_score": 2, "status": "approved"},
    {"item_id": "HI004", "asin": "B0PARTY033", "title": "Return Gift Bags 12pc", "category": "return_gifts", "price": 179, "quantity": 2, "added_by": "U003", "added_by_name": "Arjun", "added_by_letter": "A", "added_by_color": "#007600", "note": "One per kid", "votes": [{"user_id": "U001", "value": 1}, {"user_id": "U003", "value": 1}, {"user_id": "U004", "value": 1}], "vote_score": 3, "status": "approved"},
    {"item_id": "HI005", "asin": "B0JUICE001", "title": "Real Juice Party Pack 6×200ml", "category": "beverages", "price": 180, "quantity": 3, "added_by": "U002", "added_by_name": "Riya", "added_by_letter": "R", "added_by_color": "#007185", "note": "Kids love mango!", "votes": [{"user_id": "U002", "value": 1}, {"user_id": "U001", "value": 1}], "vote_score": 2, "status": "approved"},
    {"item_id": "HI006", "asin": "B0CAKE001", "title": "Premium Chocolate Cake 1kg", "category": "cake", "price": 899, "quantity": 1, "added_by": "U004", "added_by_name": "Karan", "added_by_letter": "K", "added_by_color": "#CC0C39", "note": "From the fancy bakery", "votes": [{"user_id": "U004", "value": 1}, {"user_id": "U001", "value": -1}, {"user_id": "U003", "value": -1}], "vote_score": -1, "status": "pending"},
    {"item_id": "HI007", "asin": "B0DECO001", "title": "LED Fairy Lights 10m", "category": "decorations", "price": 349, "quantity": 2, "added_by": "U004", "added_by_name": "Karan", "added_by_letter": "K", "added_by_color": "#CC0C39", "note": "For the garden area", "votes": [{"user_id": "U004", "value": 1}, {"user_id": "U002", "value": 1}], "vote_score": 2, "status": "approved"},
    {"item_id": "HI008", "asin": "B0GAME001", "title": "Musical Chairs Speaker BT", "category": "party_games", "price": 1299, "quantity": 1, "added_by": "U004", "added_by_name": "Karan", "added_by_letter": "K", "added_by_color": "#CC0C39", "note": "Bluetooth speaker for games", "votes": [{"user_id": "U004", "value": 1}, {"user_id": "U001", "value": -1}, {"user_id": "U002", "value": -1}, {"user_id": "U003", "value": -1}], "vote_score": -2, "status": "rejected"},
]

MESSAGES = [
    {"msg_id": "m1", "type": "system", "text": "Sneha created Birthday Party Squad", "timestamp": "10:00 AM"},
    {"msg_id": "m2", "type": "text", "user_id": "U001", "name": "Sneha", "letter": "S", "color": "#FF9900", "text": "Added plates and napkins. 12 kids = 24 plates minimum!", "timestamp": "10:02 AM"},
    {"msg_id": "m3", "type": "text", "user_id": "U002", "name": "Riya", "letter": "R", "color": "#007185", "text": "Adding balloons + pump. Should I get juice boxes too?", "timestamp": "10:05 AM"},
    {"msg_id": "m4", "type": "text", "user_id": "U003", "name": "Arjun", "letter": "A", "color": "#007600", "text": "Return gifts sorted! 12 bags 👍", "timestamp": "10:08 AM"},
    {"msg_id": "m5", "type": "text", "user_id": "U004", "name": "Karan", "letter": "K", "color": "#CC0C39", "text": "Added the cake and fairy lights. Party vibes! 🎉", "timestamp": "10:12 AM"},
    {"msg_id": "m6", "type": "system", "text": "Budget alert: Cart is ₹720 over budget", "timestamp": "10:15 AM"},
    {"msg_id": "m7", "type": "text", "user_id": "U001", "name": "Sneha", "letter": "S", "color": "#FF9900", "text": "Karan the cake is too expensive and the speaker is overkill. Let's optimize!", "timestamp": "10:16 AM"},
    {"msg_id": "m8", "type": "text", "user_id": "U002", "name": "Riya", "letter": "R", "color": "#007185", "text": "Yeah let's use the optimizer. The juice boxes are essential though — trust me 😄", "timestamp": "10:18 AM"},
]


def _compute_total(items):
    return sum(i["price"] * i["quantity"] for i in items)


def _get_budget_status(items, cap=4000):
    total = _compute_total(items)
    return {
        "total": total,
        "cap": cap,
        "percentage": round(total / cap * 100, 1),
        "over_budget": total > cap,
        "over_by": max(0, total - cap),
        "under_by": max(0, cap - total),
    }


def _get_split(items, method="equal"):
    total = _compute_total(items)
    if method == "equal":
        per_person = round(total / 4, 2)
        return {
            "method": "equal",
            "total": total,
            "per_person": per_person,
            "splits": [
                {"user_id": m["user_id"], "name": m["name"], "letter": m["letter"], "color": m["color"], "amount": per_person}
                for m in MEMBERS
            ],
        }
    else:
        # By contribution
        contributions = {}
        for item in items:
            uid = item["added_by"]
            contributions[uid] = contributions.get(uid, 0) + item["price"] * item["quantity"]
        return {
            "method": "by_contribution",
            "total": total,
            "per_person": round(total / 4, 2),
            "splits": [
                {"user_id": m["user_id"], "name": m["name"], "letter": m["letter"], "color": m["color"], "amount": contributions.get(m["user_id"], 0)}
                for m in MEMBERS
            ],
        }


# ── ENDPOINTS ─────────────────────────────────────────────────────────────────

@router.get("/demo")
async def get_demo_hive():
    """Get the full demo hive state in one call."""
    items = CART_ITEMS
    return {
        "success": True,
        "data": {
            "hive": {
                "hive_id": "HIVE_BDAY_001",
                "name": "Birthday Party Squad",
                "occasion": "kids_birthday",
                "members": MEMBERS,
                "member_count": 4,
                "created_by": "U001",
            },
            "cart": {
                "cart_id": "CART_BIRTHDAY_001",
                "items": items,
                "item_count": len(items),
                "total": _compute_total(items),
            },
            "messages": MESSAGES,
            "budget_status": _get_budget_status(items),
            "split_preview": _get_split(items, "equal"),
        },
        "error": None,
        "request_id": str(uuid4()),
    }


@router.get("/messages")
async def get_messages(hive_id: str = "HIVE_BDAY_001", since: str = ""):
    """Get messages since a timestamp (for polling)."""
    return {
        "success": True,
        "data": {"messages": [], "has_new": False},
        "error": None,
        "request_id": str(uuid4()),
    }


class VoteRequest(BaseModel):
    cart_id: str = "CART_BIRTHDAY_001"
    item_id: str
    user_id: str = "U001"
    value: int  # +1 or -1


@router.post("/vote")
async def vote_item(req: VoteRequest):
    """Vote on a cart item."""
    return {
        "success": True,
        "data": {"item_id": req.item_id, "new_vote": req.value, "user_id": req.user_id},
        "error": None,
        "request_id": str(uuid4()),
    }


class AddItemRequest(BaseModel):
    cart_id: str = "CART_BIRTHDAY_001"
    asin: str
    title: str
    category: str = ""
    price: float
    quantity: int = 1
    user_id: str = "U001"
    note: str = ""


@router.post("/add-item")
async def add_item(req: AddItemRequest):
    """Add an item to the hive cart."""
    member = next((m for m in MEMBERS if m["user_id"] == req.user_id), MEMBERS[0])
    new_item = {
        "item_id": f"HI{str(uuid4())[:6]}",
        "asin": req.asin,
        "title": req.title,
        "category": req.category,
        "price": req.price,
        "quantity": req.quantity,
        "added_by": req.user_id,
        "added_by_name": member["name"],
        "added_by_letter": member["letter"],
        "added_by_color": member["color"],
        "note": req.note,
        "votes": [{"user_id": req.user_id, "value": 1}],
        "vote_score": 1,
        "status": "pending",
    }
    return {
        "success": True,
        "data": new_item,
        "error": None,
        "request_id": str(uuid4()),
    }


@router.post("/optimize")
async def optimize_cart(cart_id: str = "CART_BIRTHDAY_001"):
    """Optimize the hive cart — remove rejected items, find cheaper alternatives."""
    original_total = _compute_total(CART_ITEMS)
    # Remove rejected and low-vote items
    kept = [i for i in CART_ITEMS if i["vote_score"] >= 0]
    optimized_total = _compute_total(kept)

    actions = [
        {
            "action_type": "remove",
            "icon": "close-circle",
            "title": "Removed Musical Chairs Speaker BT",
            "reason": "Rejected by 3 of 4 members (vote: -2)",
            "saved": 1299,
        },
        {
            "action_type": "swap",
            "icon": "swap-horizontal",
            "title": "Swapped Premium Cake → Standard Cake",
            "reason": "Negative votes. Found ₹450 alternative with 4.2★ rating",
            "saved": 449,
        },
        {
            "action_type": "reduce",
            "icon": "remove-circle",
            "title": "Reduced LED Fairy Lights to 1 set",
            "reason": "Budget optimization — 1 set covers the garden area",
            "saved": 349,
        },
    ]

    final_total = original_total - sum(a["saved"] for a in actions)

    return {
        "success": True,
        "data": {
            "original_total": original_total,
            "optimized_total": final_total,
            "total_saved": original_total - final_total,
            "actions": actions,
            "items_removed": 1,
            "items_swapped": 1,
            "items_reduced": 1,
        },
        "error": None,
        "request_id": str(uuid4()),
    }


@router.get("/split")
async def get_split(cart_id: str = "CART_BIRTHDAY_001", method: str = "equal"):
    """Get bill split for the hive."""
    items = [i for i in CART_ITEMS if i["vote_score"] >= 0]
    return {
        "success": True,
        "data": _get_split(items, method),
        "error": None,
        "request_id": str(uuid4()),
    }


@router.post("/place-order")
async def place_order(cart_id: str = "CART_BIRTHDAY_001", method: str = "equal"):
    """Place the hive order."""
    items = [i for i in CART_ITEMS if i["vote_score"] >= 0]
    total = _compute_total(items)
    return {
        "success": True,
        "data": {
            "order_id": f"HIVE-{847291}",
            "total": total,
            "per_person": round(total / 4, 2),
            "delivery_eta": "20 mins",
            "member_count": 4,
            "status": "confirmed",
        },
        "error": None,
        "request_id": str(uuid4()),
    }
