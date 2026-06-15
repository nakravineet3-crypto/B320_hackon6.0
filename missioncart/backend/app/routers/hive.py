from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from uuid import uuid4
from datetime import datetime
from app.services.hive_engine import (
    load_hive_data, save_hive_data,
    get_cart_total, get_vote_score,
    run_optimizer, calculate_split,
    get_member_map,
)

router = APIRouter()


# ── Request models ─────────────────────────────────────────

class AddItemRequest(BaseModel):
    asin: str
    title: str
    category: str
    price: float
    quantity: int = 1
    added_by: str = "U001"
    note: Optional[str] = None
    pack_size: int = 1
    amazon_now_eligible: bool = True
    delivery_eta: str = "now_20min"
    rating: float = 4.0


class SendMessageRequest(BaseModel):
    hive_id: str
    user_id: str = "U001"
    content: str
    cart_id: Optional[str] = None


class UpdateBudgetRequest(BaseModel):
    budget_cap: float


# ── Helpers ────────────────────────────────────────────────

def enrich_cart(cart: dict) -> dict:
    member_map = get_member_map()
    items = cart.get("items", [])
    enriched_items = []
    for item in items:
        item_copy = dict(item)
        item_copy["vote_score"] = get_vote_score(item)
        added_by = item.get("added_by", "")
        item_copy["added_by_name"] = member_map.get(added_by, {}).get("name", "Unknown")
        item_copy["added_by_color"] = member_map.get(added_by, {}).get("color", "#565959")
        item_copy["added_by_letter"] = member_map.get(added_by, {}).get("letter", "?")
        enriched_items.append(item_copy)
    cart_copy = dict(cart)
    cart_copy["items"] = enriched_items
    cart_copy["total"] = round(get_cart_total(items), 2)
    cart_copy["item_count"] = len(items)
    return cart_copy


# ── Endpoints ──────────────────────────────────────────────

@router.get("/demo")
async def get_demo_hive():
    data = load_hive_data()
    hive = next((h for h in data["hives"] if h["hive_id"] == "HIVE_BIRTHDAY_001"), None)
    cart = next((c for c in data["carts"] if c["cart_id"] == "CART_BIRTHDAY_001"), None)
    messages = [m for m in data["messages"] if m["hive_id"] == "HIVE_BIRTHDAY_001"]

    if not hive or not cart:
        return {"success": False, "error": "Demo hive not found", "request_id": str(uuid4())}

    enriched_cart = enrich_cart(cart)
    total = enriched_cart["total"]
    budget_cap = hive.get("budget_cap", 4500)
    over_budget = total > budget_cap

    split_preview = calculate_split(cart["items"], hive["members"], "equal")

    return {
        "success": True,
        "data": {
            "hive": hive,
            "cart": enriched_cart,
            "messages": sorted(messages, key=lambda m: m.get("created_at", "")),
            "budget_status": {
                "cap": budget_cap,
                "total": total,
                "over_budget": over_budget,
                "over_by": round(total - budget_cap, 2) if over_budget else 0,
                "percentage": round((total / budget_cap) * 100, 1) if budget_cap > 0 else 0,
            },
            "split_preview": split_preview,
        },
        "error": None,
        "request_id": str(uuid4()),
    }


@router.post("/cart/{cart_id}/add-item")
async def add_item_to_cart(cart_id: str, req: AddItemRequest):
    data = load_hive_data()
    cart = next((c for c in data["carts"] if c["cart_id"] == cart_id), None)
    if not cart:
        return {"success": False, "error": "Cart not found", "request_id": str(uuid4())}

    new_item = {
        "item_id": str(uuid4()),
        "asin": req.asin,
        "title": req.title,
        "category": req.category,
        "price": req.price,
        "quantity": req.quantity,
        "pack_size": req.pack_size,
        "added_by": req.added_by,
        "note": req.note,
        "status": "pending",
        "amazon_now_eligible": req.amazon_now_eligible,
        "delivery_eta": req.delivery_eta,
        "rating": req.rating,
        "votes": [{"user_id": req.added_by, "value": 1}],
    }
    cart["items"].append(new_item)

    member_map = get_member_map()
    adder_name = member_map.get(req.added_by, {}).get("name", "Someone")
    data["messages"].append({
        "message_id": str(uuid4()),
        "hive_id": cart["hive_id"],
        "cart_id": cart_id,
        "user_id": "system",
        "type": "system",
        "content": f"{adder_name} added {req.title[:30]} to the Quorum cart",
        "created_at": datetime.utcnow().isoformat(),
    })
    save_hive_data(data)

    new_total = get_cart_total(cart["items"])
    return {
        "success": True,
        "data": {
            "item_id": new_item["item_id"],
            "new_total": round(new_total, 2),
            "item_count": len(cart["items"]),
        },
        "error": None,
        "request_id": str(uuid4()),
    }


@router.delete("/cart/{cart_id}/item/{item_id}")
async def remove_item_from_cart(cart_id: str, item_id: str):
    data = load_hive_data()
    cart = next((c for c in data["carts"] if c["cart_id"] == cart_id), None)
    if not cart:
        return {"success": False, "error": "Cart not found", "request_id": str(uuid4())}

    item = next((i for i in cart["items"] if i["item_id"] == item_id), None)
    if not item:
        return {"success": False, "error": "Item not found", "request_id": str(uuid4())}

    cart["items"] = [i for i in cart["items"] if i["item_id"] != item_id]
    data["messages"].append({
        "message_id": str(uuid4()),
        "hive_id": cart["hive_id"],
        "cart_id": cart_id,
        "user_id": "system",
        "type": "system",
        "content": f"{item['title'][:30]} removed from cart",
        "created_at": datetime.utcnow().isoformat(),
    })
    save_hive_data(data)

    return {
        "success": True,
        "data": {
            "removed_item_id": item_id,
            "new_total": round(get_cart_total(cart["items"]), 2),
            "item_count": len(cart["items"]),
        },
        "error": None,
        "request_id": str(uuid4()),
    }


@router.post("/cart/{cart_id}/vote")
async def vote_on_item(cart_id: str, item_id: str, user_id: str, value: int):
    if value not in [1, -1]:
        return {"success": False, "error": "Vote must be +1 or -1", "request_id": str(uuid4())}

    data = load_hive_data()
    cart = next((c for c in data["carts"] if c["cart_id"] == cart_id), None)
    if not cart:
        return {"success": False, "error": "Cart not found", "request_id": str(uuid4())}

    for item in cart["items"]:
        if item["item_id"] == item_id:
            item["votes"] = [v for v in item["votes"] if v["user_id"] != user_id]
            item["votes"].append({"user_id": user_id, "value": value})
            new_score = get_vote_score(item)
            if new_score >= 3:
                item["status"] = "approved"
            elif new_score <= -2:
                item["status"] = "rejected"
            else:
                item["status"] = "pending"

            member_map = get_member_map()
            voter_name = member_map.get(user_id, {}).get("name", "Someone")
            action = "upvoted" if value == 1 else "downvoted"
            data["messages"].append({
                "message_id": str(uuid4()),
                "hive_id": cart["hive_id"],
                "cart_id": cart_id,
                "user_id": "system",
                "type": "system",
                "content": f"{voter_name} {action} {item['title'][:30]}",
                "created_at": datetime.utcnow().isoformat(),
            })
            save_hive_data(data)

            return {
                "success": True,
                "data": {"item_id": item_id, "new_score": new_score, "new_status": item["status"], "vote_recorded": value},
                "error": None,
                "request_id": str(uuid4()),
            }

    return {"success": False, "error": "Item not found", "request_id": str(uuid4())}


@router.post("/cart/{cart_id}/optimize")
async def optimize_cart(cart_id: str):
    data = load_hive_data()
    cart = next((c for c in data["carts"] if c["cart_id"] == cart_id), None)
    if not cart:
        return {"success": False, "error": "Cart not found", "request_id": str(uuid4())}

    hive = next((h for h in data["hives"] if h["hive_id"] == cart["hive_id"]), None)
    budget_cap = hive.get("budget_cap", 4500) if hive else 4500

    result = run_optimizer(cart, budget_cap)
    cart["items"] = result["optimized_items"]

    data["messages"].append({
        "message_id": str(uuid4()),
        "hive_id": cart["hive_id"],
        "cart_id": cart_id,
        "user_id": "system",
        "type": "system",
        "content": f"Hive optimizer saved ₹{result['total_saved']:.0f} — cart is now {'within' if result['under_budget'] else 'over'} budget",
        "created_at": datetime.utcnow().isoformat(),
    })
    save_hive_data(data)

    return {"success": True, "data": result, "error": None, "request_id": str(uuid4())}


@router.get("/cart/{cart_id}/split")
async def get_split(cart_id: str, method: str = "equal"):
    data = load_hive_data()
    cart = next((c for c in data["carts"] if c["cart_id"] == cart_id), None)
    hive = next((h for h in data["hives"] if cart and h["hive_id"] == cart["hive_id"]), None)
    if not cart or not hive:
        return {"success": False, "error": "Cart or hive not found", "request_id": str(uuid4())}

    # Only split items with non-negative vote score (exclude rejected)
    active_items = [i for i in cart["items"] if get_vote_score(i) >= 0]

    result = calculate_split(active_items, hive["members"], method)

    # Add extra context per share
    for share in result["shares"]:
        uid = share["user_id"]
        items_added = [i for i in active_items if i.get("added_by") == uid]
        share["items_added_count"] = len(items_added)
        share["items_added_value"] = round(sum(i["price"] * i["quantity"] for i in items_added), 2)

    result["active_item_count"] = len(active_items)
    result["excluded_item_count"] = len(cart["items"]) - len(active_items)
    result["method"] = method

    return {"success": True, "data": result, "error": None, "request_id": str(uuid4())}


@router.post("/messages/send")
async def send_message(req: SendMessageRequest):
    if not req.content.strip():
        return {"success": False, "error": "Message cannot be empty", "request_id": str(uuid4())}

    data = load_hive_data()
    new_message = {
        "message_id": str(uuid4()),
        "hive_id": req.hive_id,
        "cart_id": req.cart_id,
        "user_id": req.user_id,
        "type": "text",
        "content": req.content.strip(),
        "created_at": datetime.utcnow().isoformat(),
    }
    data["messages"].append(new_message)
    save_hive_data(data)

    member_map = get_member_map()
    new_message["display_name"] = member_map.get(req.user_id, {}).get("name", "Unknown")
    new_message["avatar_color"] = member_map.get(req.user_id, {}).get("color", "#565959")
    new_message["avatar_letter"] = member_map.get(req.user_id, {}).get("letter", "?")

    return {"success": True, "data": new_message, "error": None, "request_id": str(uuid4())}


@router.post("/hive/{hive_id}/budget")
async def update_budget(hive_id: str, req: UpdateBudgetRequest):
    if req.budget_cap <= 0:
        return {"success": False, "error": "Budget must be greater than 0", "request_id": str(uuid4())}

    data = load_hive_data()
    hive = next((h for h in data["hives"] if h["hive_id"] == hive_id), None)
    if not hive:
        return {"success": False, "error": "Hive not found", "request_id": str(uuid4())}

    old_budget = hive.get("budget_cap", 0)
    hive["budget_cap"] = req.budget_cap

    data["messages"].append({
        "message_id": str(uuid4()),
        "hive_id": hive_id,
        "cart_id": None,
        "user_id": "system",
        "type": "system",
        "content": f"Budget updated: ₹{old_budget:.0f} → ₹{req.budget_cap:.0f}",
        "created_at": datetime.utcnow().isoformat(),
    })
    save_hive_data(data)

    cart = next((c for c in data["carts"] if c["hive_id"] == hive_id), None)
    total = get_cart_total(cart["items"]) if cart else 0
    over_budget = total > req.budget_cap

    return {
        "success": True,
        "data": {
            "hive_id": hive_id,
            "budget_cap": req.budget_cap,
            "current_total": round(total, 2),
            "over_budget": over_budget,
            "over_by": round(max(0, total - req.budget_cap), 2),
            "percentage": round((total / req.budget_cap) * 100, 1) if req.budget_cap > 0 else 0,
        },
        "error": None,
        "request_id": str(uuid4()),
    }


@router.get("/messages/{hive_id}")
async def get_messages(hive_id: str, since: Optional[str] = None):
    data = load_hive_data()
    messages = [m for m in data["messages"] if m["hive_id"] == hive_id]
    if since:
        messages = [m for m in messages if m["created_at"] > since]

    # Sort oldest first
    messages = sorted(messages, key=lambda m: m.get("created_at", ""))

    member_map = get_member_map()
    for msg in messages:
        uid = msg.get("user_id", "")
        msg["display_name"] = member_map.get(uid, {}).get("name", "Unknown")
        msg["avatar_color"] = member_map.get(uid, {}).get("color", "#565959")
        msg["avatar_letter"] = member_map.get(uid, {}).get("letter", "?")

    return {"success": True, "data": messages, "error": None, "request_id": str(uuid4())}


@router.post("/cart/{cart_id}/place-order")
async def place_hive_order(cart_id: str, split_method: str = "equal"):
    import random
    data = load_hive_data()
    cart = next((c for c in data["carts"] if c["cart_id"] == cart_id), None)
    hive = next((h for h in data["hives"] if cart and h["hive_id"] == cart["hive_id"]), None)
    if not cart or not hive:
        return {"success": False, "error": "Cart or hive not found", "request_id": str(uuid4())}

    order_id = f"HIVE-{random.randint(100000, 999999)}"
    total = get_cart_total(cart["items"])
    split = calculate_split(cart["items"], hive["members"], split_method)

    order = {
        "order_id": order_id, "cart_id": cart_id, "hive_id": cart["hive_id"],
        "hive_name": hive["name"], "total": round(total, 2), "split": split,
        "item_count": len(cart["items"]),
        "delivery_address": cart.get("delivery_address", "Bangalore"),
        "estimated_delivery": "20 minutes",
        "placed_at": datetime.utcnow().isoformat(), "status": "confirmed",
    }
    data["orders"].append(order)
    cart["status"] = "ordered"
    data["messages"].append({
        "message_id": str(uuid4()), "hive_id": cart["hive_id"], "cart_id": cart_id,
        "user_id": "system", "type": "system",
        "content": f"Order placed! {order_id} · ₹{total:.0f} · Arriving in 20 mins ⚡",
        "created_at": datetime.utcnow().isoformat(),
    })
    save_hive_data(data)

    return {"success": True, "data": order, "error": None, "request_id": str(uuid4())}


@router.post("/reset-demo")
async def reset_demo():
    return {"success": True, "data": {"message": "Demo reset — restart server"}, "error": None, "request_id": str(uuid4())}
