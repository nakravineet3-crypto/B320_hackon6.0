from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from uuid import uuid4
import json
from pathlib import Path

router = APIRouter()


class PreCheckoutRequest(BaseModel):
    cart_items: List[dict]
    goal: str = ""
    budget_max: float = 4000
    headcount: int = 12
    occasion_type: str = "kids_birthday"
    user_id: str = "U001"


class PreCheckoutWarning(BaseModel):
    warning_id: str
    type: str  # "late_item" | "price_drop" | "compatibility_gap"
    # | "budget_insight" | "quantity_risk"
    severity: str  # "critical" | "warning" | "info"
    title: str
    detail: str
    action_label: str
    action_type: str  # "swap_item" | "adjust_qty" | "continue"
    affected_asin: Optional[str] = None
    saving_amount: Optional[float] = None


@router.post("/pre-checkout")
async def pre_checkout_check(request: PreCheckoutRequest):
    warnings: List[PreCheckoutWarning] = []

    data_path = Path(__file__).parent.parent / "data"
    simulated_path = data_path / "simulated"

    # Load price history
    price_history = {}
    ph_path = simulated_path / "price_history.json"
    if ph_path.exists():
        with open(ph_path) as f:
            price_history = json.load(f)

    # Load community sessions for quantity validation
    sessions_data = {}
    cs_path = simulated_path / "community_sessions.json"
    if cs_path.exists():
        with open(cs_path) as f:
            sessions_data = json.load(f)

    cart_items = request.cart_items

    # ── CHECK 1: LATE ITEMS ────────────────────────────────
    # Any item not on Amazon Now when deadline is tight
    late_items = [
        item for item in cart_items
        if not item.get("amazon_now_eligible", True)
        and item.get("delivery_eta") not in ["now_20min", "today"]
    ]

    if late_items:
        item = late_items[0]
        warnings.append(PreCheckoutWarning(
            warning_id=str(uuid4()),
            type="late_item",
            severity="critical",
            title=f"{item.get('title', 'One item')[:30]} arrives late",
            detail=(
                f"This item arrives tomorrow, not today. "
                f"If your occasion is today, this will be missing. "
                f"We found a Now-eligible alternative."
            ),
            action_label="Swap to Now item",
            action_type="swap_item",
            affected_asin=item.get("asin"),
        ))

    # ── CHECK 2: PRICE DROP ALERT ──────────────────────────
    # Any item cheaper in last 30 days
    price_alerts = []
    for item in cart_items:
        asin = item.get("asin", "")
        ph = price_history.get(asin, {})
        if ph:
            lowest = ph.get("lowest_30d", item.get("price", 0))
            current = item.get("price", 0)
            saving = current - lowest
            if saving >= 15:  # Only flag if saving >= ₹15
                price_alerts.append({
                    "item": item,
                    "saving": saving,
                    "lowest": lowest,
                    "trend": ph.get("price_trend", "stable"),
                })

    if price_alerts:
        # Show the biggest saving
        best = max(price_alerts, key=lambda x: x["saving"])
        warnings.append(PreCheckoutWarning(
            warning_id=str(uuid4()),
            type="price_drop",
            severity="warning",
            title=f"\u20b9{best['saving']:.0f} saving available",
            detail=(
                f"{best['item'].get('title', 'Item')[:25]} was "
                f"\u20b9{best['lowest']:.0f} recently "
                f"(currently \u20b9{best['item'].get('price', 0):.0f}). "
                f"Price is {best['trend']} \u2014 "
                f"{'good time to buy' if best['trend'] == 'falling' else 'consider alternatives'}."
            ),
            action_label="See alternatives",
            action_type="swap_item",
            affected_asin=best["item"].get("asin"),
            saving_amount=best["saving"],
        ))

    # ── CHECK 3: COMPATIBILITY GAP ─────────────────────────
    # Check if any item needs an accessory not in cart
    cart_categories = [item.get("category", "") for item in cart_items]

    COMPATIBILITY = {
        "balloon_set": {
            "requires": "balloon_pump",
            "message": "Balloon set needs a pump \u2014 not found in cart",
        },
        "balloons": {
            "requires": "balloon_pump",
            "message": "Balloons need a pump to inflate",
        },
        "induction_cooktop": {
            "requires": "induction_compatible_vessel",
            "message": "Induction cooktop needs compatible vessels",
        },
        "cake": {
            "requires": "candles",
            "message": "Cake needs candles",
        },
    }

    for item in cart_items:
        cat = item.get("category", "")
        rule = COMPATIBILITY.get(cat)
        if rule and rule["requires"] not in cart_categories:
            warnings.append(PreCheckoutWarning(
                warning_id=str(uuid4()),
                type="compatibility_gap",
                severity="critical",
                title="Missing accessory",
                detail=rule["message"],
                action_label="Add missing item",
                action_type="add_item",
                affected_asin=item.get("asin"),
            ))
            break  # Only show one compatibility warning

    # ── CHECK 4: QUANTITY RISK ────────────────────────────
    # Compare cart quantities against community median
    if sessions_data and request.headcount > 0:
        occ_sessions = [
            s for s in sessions_data.get("sessions", [])
            if s.get("occasion_type") == request.occasion_type
        ]

        if occ_sessions:
            for item in cart_items:
                cat = item.get("category", "")
                pack_size = item.get("pack_size", 10)
                current_packs = item.get("packs_quantity", 1)
                current_units = current_packs * pack_size

                # Compute median quantity from sessions
                cat_quantities = []
                for s in occ_sessions:
                    s_headcount = s.get("headcount", 10)
                    for i in s.get("items_purchased", []):
                        if i.get("category") == cat:
                            ratio = i.get("quantity", 1) * pack_size / s_headcount
                            cat_quantities.append(ratio)

                if cat_quantities:
                    median_ratio = sorted(cat_quantities)[len(cat_quantities) // 2]
                    recommended_units = median_ratio * request.headcount

                    if current_units < recommended_units * 0.75:
                        warnings.append(PreCheckoutWarning(
                            warning_id=str(uuid4()),
                            type="quantity_risk",
                            severity="warning",
                            title="Quantity may be low",
                            detail=(
                                f"For {request.headcount} guests, "
                                f"similar occasions used "
                                f"{recommended_units:.0f} "
                                f"{cat.replace('_', ' ')}. You have {current_units}."
                            ),
                            action_label="Adjust quantity",
                            action_type="adjust_qty",
                            affected_asin=item.get("asin"),
                        ))
                        break  # One quantity warning max

    # ── CHECK 5: BUDGET INSIGHT ───────────────────────────
    total = sum(item.get("total_cost", 0) for item in cart_items)
    budget = request.budget_max
    utilization = total / budget if budget > 0 else 0

    if utilization > 0.95:
        remaining = budget - total
        warnings.append(PreCheckoutWarning(
            warning_id=str(uuid4()),
            type="budget_insight",
            severity="info",
            title=(
                f"\u20b9{abs(remaining):.0f} "
                f"{'over' if remaining < 0 else 'under'} budget"
            ),
            detail=(
                f"Cart total \u20b9{total:.0f} vs budget \u20b9{budget:.0f}. "
                f"{'Consider removing optional items.' if remaining < 0 else 'You have a small buffer.'}"
            ),
            action_label="Review cart",
            action_type="continue",
            saving_amount=abs(remaining) if remaining > 0 else None,
        ))

    # Limit to 3 most important warnings
    # Priority: critical first, then warning, then info
    priority = {"critical": 0, "warning": 1, "info": 2}
    warnings.sort(key=lambda w: priority.get(w.severity, 3))
    top_warnings = warnings[:3]

    # If no warnings — good news
    if not top_warnings:
        all_clear = True
    else:
        all_clear = False

    return {
        "success": True,
        "data": {
            "warnings": [w.dict() for w in top_warnings],
            "warning_count": len(top_warnings),
            "all_clear": all_clear,
            "cart_total": sum(item.get("total_cost", 0) for item in cart_items),
            "proceed_to_checkout": True,
            "amazon_cart_url": "https://www.amazon.in",
        },
        "error": None,
        "request_id": str(uuid4()),
    }
