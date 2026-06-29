from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from uuid import uuid4
from datetime import datetime, timedelta, date
import asyncio
import json
import random
from pathlib import Path

from ..services.depletion_engine import depletion_engine, DepletionPrediction

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


# ── ENDPOINTS ─────────────────────────────────────────


@router.get("/draft")
async def get_reorder_draft(user_id: str = "U001", removed: str = ""):
    """Get today's reorder draft.
    removed: comma-separated ASINs to exclude
    """
    removed_ids = {r.strip() for r in removed.split(",") if r.strip()}

    bundle: list[DepletionPrediction] = depletion_engine.build_morning_bundle(user_id)

    # Filter removed items
    bundle = [p for p in bundle if p.asin not in removed_ids]

    if not bundle:
        return {
            "success": True,
            "data": {
                "draft_id": f"DRAFT-{str(uuid4())[:8].upper()}",
                "user_id": user_id,
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
                "status": "pending",
                "items": [],
                "item_count": 0,
                "total_price": 0.0,
                "all_amazon_now": False,
                "delivery_estimate_mins": 60,
                "delivery_copy": "Some items via standard delivery",
                "simulated_data": True,
                "prediction_model": "ewma_v1",
                "coverage_summary": {"items_due_today": 0, "items_due_soon": 0, "model_confidence_avg": 0.0},
            },
            "error": None,
            "request_id": str(uuid4()),
        }

    # Gather explanations concurrently
    explanations = await asyncio.gather(
        *[depletion_engine.explain(pred) for pred in bundle],
        return_exceptions=True,
    )

    items = []
    total_cost = 0.0
    today = date.today()

    for pred, explain_result in zip(bundle, explanations):
        if isinstance(explain_result, Exception):
            urgency_copy_llm = "Running low based on your purchase history."
            model_used = "template"
        else:
            urgency_copy_llm, model_used = explain_result

        # Runtime urgency display copy
        days_remaining = pred.days_remaining
        if days_remaining <= 0:
            urgency_copy = "Runs out today"
        elif days_remaining <= 1:
            urgency_copy = "Runs out tomorrow"
        else:
            urgency_copy = f"Runs out in {int(days_remaining)} days"

        # Days since last purchase (runtime-computed)
        try:
            last_date = date.fromisoformat(pred.last_purchase_date)
            days_since = (today - last_date).days
        except (ValueError, TypeError):
            days_since = int(pred.ewma_interval)

        # Pattern description
        avg_interval = pred.ewma_interval
        if avg_interval <= 4:
            pattern = f"You buy this every {avg_interval:.0f} days"
        elif avg_interval <= 8:
            pattern = f"Weekly purchase · every {avg_interval:.0f} days"
        elif avg_interval <= 16:
            pattern = "Bi-weekly purchase"
        else:
            pattern = "Monthly purchase"

        now_eligible = pred.amazon_now_eligible
        qty = pred.suggested_quantity
        price = pred.price_inr

        item = {
            # ALL ORIGINAL FIELDS (frontend compatibility guaranteed)
            "item_id": pred.prediction_id,
            "asin": pred.asin,
            "title": pred.title,
            "category": pred.category,
            "suggested_quantity": qty,
            "user_quantity": qty,
            "unit": "pack",
            "price_per_unit": price,
            "total_cost": round(price * qty, 2),
            "confidence": pred.confidence["percentage"],
            "urgency_copy": urgency_copy,
            "explanation": {
                "avg_interval_days": round(pred.ewma_interval, 1),
                "last_purchased": pred.last_purchase_date,
                "days_since": days_since,
                "days_remaining": days_remaining,
                "purchase_count": pred.confidence.get("n_observations", 0) + 1,
                "pattern": pattern,
                "days_remaining_formula": (
                    f"ewma: {pred.ewma_interval:.1f}d | "
                    f"cv: {pred.confidence.get('cv', 0):.2f} | "
                    f"n_obs: {pred.confidence.get('n_observations', 0)} | "
                    f"remaining: {days_remaining:.1f}d"
                ),
                "availability": (
                    "Available via Amazon Now · Delivers in ~20 min"
                    if now_eligible
                    else "Not on Amazon Now · Standard delivery"
                ),
                # NEW ADDITIVE FIELDS
                "ewma_interval": pred.ewma_interval,
                "seasonal_multiplier": 1.0,
                "bulk_multiplier": 1.0,
                "model_notes": [],
                "anomalies_excluded": 0,
                "explanation_copy": urgency_copy_llm,
                "model_used": model_used,
            },
            "inventory_status": "in_stock" if now_eligible else "substitute_available",
            "amazon_now_eligible": now_eligible,
            "delivery_eta_mins": 20 if now_eligible else 120,
            # NEW ADDITIVE FIELDS
            "bundle_score": pred.bundle_score,
            "reorder_urgency": pred.reorder_urgency,
            "subcategory": pred.subcategory,
            "confidence_detail": pred.confidence,
            "days_remaining": pred.days_remaining,
            "simulated_data": True,
        }
        items.append(item)
        total_cost += item["total_cost"]

    all_now = all(i["amazon_now_eligible"] for i in items) if items else False
    items_urgent = sum(1 for p in bundle if p.reorder_urgency == "urgent")
    items_soon = sum(1 for p in bundle if p.reorder_urgency == "soon")
    avg_confidence = (
        sum(p.confidence.get("score", 0) for p in bundle) / len(bundle)
        if bundle else 0.0
    )

    draft = {
        "draft_id": f"DRAFT-{str(uuid4())[:8].upper()}",
        "user_id": user_id,
        "created_at": datetime.utcnow().isoformat(),
        "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
        "status": "pending",
        "items": items,
        "item_count": len(items),
        "total_price": round(total_cost, 2),
        "all_amazon_now": all_now,
        "delivery_estimate_mins": 20 if all_now else 60,
        "delivery_copy": (
            "All items via Amazon Now · ~20 min"
            if all_now
            else "Some items via standard delivery"
        ),
        "simulated_data": True,
        "prediction_model": "ewma_v1",
        "coverage_summary": {
            "items_due_today": items_urgent,
            "items_due_soon": items_soon,
            "model_confidence_avg": round(avg_confidence, 2),
        },
    }

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
