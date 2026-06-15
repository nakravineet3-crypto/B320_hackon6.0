from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from uuid import uuid4
from datetime import datetime, timedelta
import json
import random
from pathlib import Path

router = APIRouter()

DATA_PATH = Path(__file__).parent.parent / "data" / "simulated"

# Idempotency store (in-memory for hackathon)
_processed_orders: dict = {}


def load_depletion_alerts(user_id: str = "U001") -> list:
    path = DATA_PATH / "depletion_alerts.json"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        all_alerts = json.load(f)
    return all_alerts.get(user_id, [])


def compute_confidence(alert: dict) -> dict:
    """Confidence formula:
    base = purchase_count regularity (more purchases = higher)
    urgency = 1.0 if days_remaining < 1, 0.8 if < 2, 0.6 if < 3
    confidence_raw = (regularity * 0.5) + (urgency * 0.5)
    """
    purchase_count = alert.get("purchase_count", 2)
    days_remaining = alert.get("days_remaining", 2)

    # Regularity score
    if purchase_count >= 8:
        regularity = 1.0
    elif purchase_count >= 5:
        regularity = 0.85
    elif purchase_count >= 3:
        regularity = 0.70
    else:
        regularity = 0.55

    # Urgency score
    if days_remaining <= 0:
        urgency = 1.0
    elif days_remaining <= 1:
        urgency = 0.92
    elif days_remaining <= 2:
        urgency = 0.80
    else:
        urgency = 0.65

    confidence_raw = (regularity * 0.5) + (urgency * 0.5)

    if confidence_raw >= 0.85:
        label = "High"
    elif confidence_raw >= 0.70:
        label = "Medium"
    else:
        label = "Estimated"

    return {
        "score": round(confidence_raw, 2),
        "percentage": round(confidence_raw * 100),
        "label": label,
    }


def build_draft_item(alert: dict) -> dict:
    confidence = compute_confidence(alert)

    # Runtime days_remaining computation
    avg_interval = alert.get("average_interval_days", 7)
    last_purchased_str = alert.get("last_purchased", "")
    if last_purchased_str:
        try:
            last_purchased_dt = datetime.strptime(last_purchased_str, "%Y-%m-%d")
            expected_next = last_purchased_dt + timedelta(days=avg_interval)
            days_remaining = (expected_next - datetime.now()).days
            days_remaining = max(0, days_remaining)
        except Exception:
            days_remaining = alert.get("days_remaining", 1)
    else:
        days_remaining = alert.get("days_remaining", 1)

    days_since = alert.get("days_since_purchase", 6)
    purchase_count = alert.get("purchase_count", 4)
    last_purchased = last_purchased_str

    # Urgency copy for card
    if days_remaining <= 0:
        urgency_copy = "Runs out today"
    elif days_remaining <= 1:
        urgency_copy = "Runs out tomorrow"
    else:
        urgency_copy = f"Runs out in {days_remaining:.0f} days"

    # Pattern description
    if avg_interval <= 4:
        pattern = f"You buy this every {avg_interval:.0f} days"
    elif avg_interval <= 8:
        pattern = f"Weekly purchase · every {avg_interval:.0f} days"
    elif avg_interval <= 16:
        pattern = "Bi-weekly purchase"
    else:
        pattern = "Monthly purchase"

    # Inventory status
    now_eligible = alert.get("amazon_now_eligible", True)
    inventory_status = "in_stock" if now_eligible else "substitute_available"

    qty = alert.get("suggested_quantity", 1)
    price = alert.get("price", 50)

    return {
        "item_id": alert.get("asin", str(uuid4())),
        "asin": alert.get("asin", ""),
        "title": alert.get("title", ""),
        "category": alert.get("category", ""),
        "suggested_quantity": qty,
        "user_quantity": qty,
        "unit": alert.get("unit", "pack") if alert.get("unit") else "pack",
        "price_per_unit": price,
        "total_cost": round(price * qty, 2),
        "confidence": confidence,
        "urgency_copy": urgency_copy,
        "explanation": {
            "avg_interval_days": round(avg_interval, 1),
            "last_purchased": last_purchased,
            "days_since": days_since,
            "days_remaining": round(days_remaining, 1),
            "purchase_count": purchase_count,
            "pattern": pattern,
            "days_remaining_formula": (
                f"Last bought {last_purchased} + "
                f"{avg_interval:.0f} day avg interval = "
                f"runs out in {days_remaining} days"
            ),
            "availability": (
                "Available via Amazon Now · Delivers in ~20 min"
                if now_eligible
                else "Not on Amazon Now · Standard delivery"
            ),
        },
        "inventory_status": inventory_status,
        "amazon_now_eligible": now_eligible,
        "delivery_eta_mins": 20 if now_eligible else 1440,
    }


def build_draft(user_id: str = "U001", removed_ids: list = []) -> dict:
    alerts = load_depletion_alerts(user_id)

    # Filter urgent items (days_remaining <= 2)
    # Exclude removed items
    urgent = [
        a for a in alerts
        if a.get("days_remaining", 99) <= 2
        and a.get("asin") not in removed_ids
    ]

    # If no urgent, include soon items
    if not urgent:
        urgent = [
            a for a in alerts
            if a.get("days_remaining", 99) <= 5
            and a.get("asin") not in removed_ids
        ][:5]

    items = [build_draft_item(a) for a in urgent]
    total = sum(i["total_cost"] for i in items)
    all_now = all(i["amazon_now_eligible"] for i in items)

    return {
        "draft_id": f"DRAFT-{str(uuid4())[:8].upper()}",
        "user_id": user_id,
        "created_at": datetime.utcnow().isoformat(),
        "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
        "status": "pending",
        "items": items,
        "item_count": len(items),
        "total_price": round(total, 2),
        "all_amazon_now": all_now,
        "delivery_estimate_mins": 20 if all_now else 60,
        "delivery_copy": (
            "All items via Amazon Now · ~20 min"
            if all_now
            else "Some items via standard delivery"
        ),
    }


# ── ENDPOINTS ─────────────────────────────────────────


@router.get("/draft")
async def get_reorder_draft(user_id: str = "U001", removed: str = ""):
    """Get today's reorder draft.
    removed: comma-separated ASINs to exclude
    """
    removed_ids = [r.strip() for r in removed.split(",") if r.strip()]
    draft = build_draft(user_id, removed_ids)
    return {
        "success": True,
        "data": draft,
        "error": None,
        "request_id": str(uuid4()),
    }


@router.get("/alerts")
async def get_reorder_alerts(user_id: str = "U001"):
    """Compact alert list for home screen card.
    Returns ALL urgent items (days_remaining <= 2).
    """
    alerts = load_depletion_alerts(user_id)
    urgent = [a for a in alerts if a.get("days_remaining", 99) <= 2]
    if not urgent:
        urgent = alerts[:3]
    return {
        "success": True,
        "data": urgent,
        "error": None,
        "request_id": str(uuid4()),
    }


@router.get("/notification-content")
async def get_notification_content(user_id: str = "U001"):
    alerts = load_depletion_alerts(user_id)
    urgent = [a for a in alerts if a.get("days_remaining", 99) <= 2]
    if not urgent:
        urgent = alerts[:3]

    names = [a.get("title", "Item") for a in urgent]

    if len(names) == 0:
        body = "Your daily essentials need restocking"
    elif len(names) == 1:
        body = f"{names[0]} — Tap to approve & order ⚡"
    elif len(names) == 2:
        body = f"{names[0]}, {names[1]} — Tap to approve ⚡"
    elif len(names) == 3:
        body = f"{names[0]}, {names[1]}, {names[2]} — Tap to approve ⚡"
    else:
        body = (
            f"{names[0]}, {names[1]} "
            f"+{len(names) - 2} more — Tap to approve ⚡"
        )

    return {
        "success": True,
        "data": {
            "title": "🛒 Your daily reorder is ready",
            "body": body,
            "item_count": len(urgent),
            "items": [
                {
                    "name": a.get("title", ""),
                    "quantity": a.get("suggested_quantity", 1),
                    "price_inr": a.get("price", 0),
                    "days_remaining": a.get("days_remaining", 0),
                }
                for a in urgent
            ],
        },
        "error": None,
        "request_id": str(uuid4()),
    }


class UpdateQuantityRequest(BaseModel):
    draft_id: str
    item_id: str
    new_quantity: int
    user_id: str = "U001"


@router.post("/draft/update-quantity")
async def update_quantity(req: UpdateQuantityRequest):
    """Update quantity for a single item.
    Returns updated item total and draft total.
    """
    if req.new_quantity < 1:
        req.new_quantity = 1
    if req.new_quantity > 20:
        req.new_quantity = 20

    alerts = load_depletion_alerts(req.user_id)
    item_alert = next(
        (a for a in alerts if a.get("asin") == req.item_id), None
    )
    price = item_alert.get("price", 50) if item_alert else 50
    new_total = round(price * req.new_quantity, 2)

    return {
        "success": True,
        "data": {
            "item_id": req.item_id,
            "new_quantity": req.new_quantity,
            "price_per_unit": price,
            "new_item_total": new_total,
        },
        "error": None,
        "request_id": str(uuid4()),
    }


class ApproveRequest(BaseModel):
    draft_id: str
    user_id: str = "U001"
    idempotency_key: str
    items: List[dict]


@router.post("/approve")
async def approve_reorder(req: ApproveRequest):
    """Approve the reorder draft.
    Idempotency key prevents double-tap issues.
    Returns order ID and status steps.
    """
    # Idempotency check
    key = req.idempotency_key
    if key and key in _processed_orders:
        return _processed_orders[key]

    from datetime import timezone, timedelta as td
    IST = timezone(td(hours=5, minutes=30))
    delivery_time = (datetime.now(tz=IST) + timedelta(minutes=20)).strftime("%I:%M %p IST")

    order_id = f"MC-2026-{random.randint(100000, 999999)}"
    total = sum(i.get("total_cost", 0) for i in req.items)

    response = {
        "success": True,
        "data": {
            "order_id": order_id,
            "draft_id": req.draft_id,
            "idempotency_key": req.idempotency_key,
            "status": "placed",
            "total_price": round(total, 2),
            "item_count": len(req.items),
            "items": req.items,
            "delivery_estimate": "20 minutes",
            "delivery_by": delivery_time,
            "amazon_now_confirmed": True,
            "placed_at": datetime.utcnow().isoformat(),
            "steps": [
                {"step": "validated", "label": "Cart validated", "delay_ms": 800},
                {"step": "authorized", "label": "Payment authorized", "delay_ms": 1600},
                {"step": "reserved", "label": "Inventory reserved", "delay_ms": 2400},
                {"step": "placed", "label": "Order placed", "delay_ms": 3200},
            ],
        },
        "error": None,
        "request_id": str(uuid4()),
    }

    # Store for idempotency
    if key:
        _processed_orders[key] = response

    return response


class RejectRequest(BaseModel):
    draft_id: str
    user_id: str = "U001"
    reason: Optional[str] = "not_needed"


@router.post("/reject")
async def reject_reorder(req: RejectRequest):
    return {
        "success": True,
        "data": {
            "draft_id": req.draft_id,
            "status": "rejected",
            "message": "Draft rejected. We'll adjust tomorrow's suggestions.",
        },
        "error": None,
        "request_id": str(uuid4()),
    }


@router.get("/order-status/{order_id}")
async def get_order_status(order_id: str):
    return {
        "success": True,
        "data": {
            "order_id": order_id,
            "status": "out_for_delivery",
            "steps": [
                {"step": "placed", "label": "Order placed", "done": True, "time": "7:02 AM"},
                {"step": "picked", "label": "Picked from store", "done": True, "time": "7:08 AM"},
                {"step": "on_the_way", "label": "Out for delivery", "done": True, "time": "7:14 AM"},
                {"step": "delivered", "label": "Delivered", "done": False, "time": "~7:22 AM"},
            ],
            "delivery_partner": "Amazon Now",
            "eta_minutes": 8,
            "can_cancel": False,
            "cancel_window_expired": True,
        },
        "error": None,
        "request_id": str(uuid4()),
    }
