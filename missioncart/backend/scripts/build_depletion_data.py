"""
build_depletion_data.py
=======================
Offline data generation script for the MissionCart Smart Reorder system.

Reads:
  - backend/app/data/simulated/purchase_history.json
  - backend/app/data/simulated/users.json
  - backend/app/data/simulated/price_history.json
  - backend/app/data/catalog.json

Writes:
  - backend/app/data/category_priors.json
  - backend/app/data/simulated/purchase_events.json
  - backend/app/data/simulated/user_product_features.json
  - backend/app/data/simulated/depletion_predictions.json

Run: python scripts/build_depletion_data.py
     OR: python -m scripts.build_depletion_data

Safe to re-run — all output files are overwritten.

Design note: This script imports ONLY from app.services.ewma_engine (pure math,
no I/O). It never imports depletion_engine — that service imports from this
data layer and would create a circular dependency.

Scale note: At Amazon production scale, replace this script with a Spark job
processing purchase events from DynamoDB via EventBridge, writing features to
Amazon SageMaker Feature Store, and running batch predictions via SageMaker
Batch Transform. The EWMA logic (ewma_engine.py) is portable and unchanged.
"""

import sys
import json
import math
from pathlib import Path
from datetime import date, datetime
from collections import defaultdict

# ── Path setup ─────────────────────────────────────────────────────────────────
# Works whether invoked as: python scripts/build_depletion_data.py
#                       or: python -m scripts.build_depletion_data
_SCRIPT_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _SCRIPT_DIR.parent
sys.path.insert(0, str(_BACKEND_DIR))

DATA_PATH = _BACKEND_DIR / "app" / "data"
SIM_PATH = DATA_PATH / "simulated"

# Demo date — all predictions are relative to this date so urgency is correct
# during the hackathon demo on 2026-06-23.
DEMO_DATE = date(2026, 6, 23)

# ── Demo ASINs — must appear in U001's predictions with High/Medium confidence ─
DEMO_ASINS = {
    "MC_ARIEL_001":   {"max_days_remaining": 7, "description": "Ariel 2kg Detergent"},
    "MC_SHAMPOO_001": {"max_days_remaining": 7, "description": "Head & Shoulders 400ml"},
    "MC_DOGFOOD_001": {"max_days_remaining": 5, "description": "Pedigree Adult 3kg"},
}

# ── Category priors — embedded so script is self-contained ────────────────────
# Generated here and also written to category_priors.json.
# seasonal_index > 1.0 means faster depletion in that month (shorter interval).
CATEGORY_PRIORS = {
    "dairy": {
        "default_interval_days": 3,
        "household_size_scaling": 0.7,
        "seasonal_indices": {str(m): 1.0 for m in range(1, 13)},
        "typical_pack_size_g": 1000,
        "confidence_at_tier3": 0.40,
    },
    "laundry": {
        "default_interval_days": 28,
        "household_size_scaling": 0.8,
        "seasonal_indices": {
            "1": 1.0, "2": 1.0, "3": 1.0, "4": 1.0, "5": 1.0,
            "6": 1.15, "7": 1.15, "8": 1.15, "9": 1.10,
            "10": 1.0, "11": 1.0, "12": 1.0,
        },
        "typical_pack_size_g": 2000,
        "confidence_at_tier3": 0.35,
    },
    "detergent": {
        "default_interval_days": 14,
        "household_size_scaling": 0.8,
        "seasonal_indices": {
            "1": 1.0, "2": 1.0, "3": 1.0, "4": 1.0, "5": 1.0,
            "6": 1.15, "7": 1.15, "8": 1.15, "9": 1.10,
            "10": 1.0, "11": 1.0, "12": 1.0,
        },
        "typical_pack_size_g": 2000,
        "confidence_at_tier3": 0.35,
    },
    "personal_care": {
        "default_interval_days": 21,
        "household_size_scaling": 0.5,
        "seasonal_indices": {str(m): 1.0 for m in range(1, 13)},
        "typical_pack_size_g": 400,
        "confidence_at_tier3": 0.35,
    },
    "shampoo": {
        "default_interval_days": 21,
        "household_size_scaling": 0.5,
        "seasonal_indices": {str(m): 1.0 for m in range(1, 13)},
        "typical_pack_size_g": 400,
        "confidence_at_tier3": 0.35,
    },
    "food_beverages": {
        "default_interval_days": 7,
        "household_size_scaling": 0.8,
        "seasonal_indices": {str(m): 1.0 for m in range(1, 13)},
        "typical_pack_size_g": 1000,
        "confidence_at_tier3": 0.40,
    },
    "grocery_staples": {
        "default_interval_days": 7,
        "household_size_scaling": 0.8,
        "seasonal_indices": {str(m): 1.0 for m in range(1, 13)},
        "typical_pack_size_g": 1000,
        "confidence_at_tier3": 0.40,
    },
    "household": {
        "default_interval_days": 30,
        "household_size_scaling": 0.6,
        "seasonal_indices": {str(m): 1.0 for m in range(1, 13)},
        "typical_pack_size_g": 1000,
        "confidence_at_tier3": 0.35,
    },
    "pet_care": {
        "default_interval_days": 21,
        "household_size_scaling": 1.0,
        "seasonal_indices": {str(m): 1.0 for m in range(1, 13)},
        "typical_pack_size_g": 3000,
        "confidence_at_tier3": 0.35,
    },
    "bakery": {
        "default_interval_days": 4,
        "household_size_scaling": 0.7,
        "seasonal_indices": {str(m): 1.0 for m in range(1, 13)},
        "typical_pack_size_g": 400,
        "confidence_at_tier3": 0.40,
    },
    "biscuits": {
        "default_interval_days": 7,
        "household_size_scaling": 0.7,
        "seasonal_indices": {str(m): 1.0 for m in range(1, 13)},
        "typical_pack_size_g": 800,
        "confidence_at_tier3": 0.40,
    },
    "cooking_oil": {
        "default_interval_days": 21,
        "household_size_scaling": 0.8,
        "seasonal_indices": {str(m): 1.0 for m in range(1, 13)},
        "typical_pack_size_g": 1000,
        "confidence_at_tier3": 0.38,
    },
    "snacks": {
        "default_interval_days": 7,
        "household_size_scaling": 0.6,
        "seasonal_indices": {str(m): 1.0 for m in range(1, 13)},
        "typical_pack_size_g": 500,
        "confidence_at_tier3": 0.35,
    },
    "beverages": {
        "default_interval_days": 10,
        "household_size_scaling": 0.7,
        "seasonal_indices": {str(m): 1.0 for m in range(1, 13)},
        "typical_pack_size_g": 500,
        "confidence_at_tier3": 0.38,
    },
    "instant_food": {
        "default_interval_days": 10,
        "household_size_scaling": 0.7,
        "seasonal_indices": {str(m): 1.0 for m in range(1, 13)},
        "typical_pack_size_g": 500,
        "confidence_at_tier3": 0.35,
    },
    "packaged_food": {
        "default_interval_days": 10,
        "household_size_scaling": 0.7,
        "seasonal_indices": {str(m): 1.0 for m in range(1, 13)},
        "typical_pack_size_g": 500,
        "confidence_at_tier3": 0.35,
    },
    "default": {
        "default_interval_days": 14,
        "household_size_scaling": 0.7,
        "seasonal_indices": {str(m): 1.0 for m in range(1, 13)},
        "typical_pack_size_g": 500,
        "confidence_at_tier3": 0.35,
    },
}


# ── Stat helpers (no numpy, no scipy) ─────────────────────────────────────────

def _median(values):
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    return float(s[n // 2] if n % 2 == 1 else (s[n // 2 - 1] + s[n // 2]) / 2.0)


def _mean(values):
    return sum(values) / len(values) if values else 0.0


def _variance(values):
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    return sum((v - m) ** 2 for v in values) / len(values)


def _std(values):
    return math.sqrt(_variance(values))


def _month_to_season(month: int) -> str:
    if month in (3, 4, 5):
        return "summer"
    if month in (6, 7, 8, 9):
        return "monsoon"
    if month in (10, 11):
        return "festival"
    return "winter"


# ── Step 2: Build purchase_events.json ────────────────────────────────────────

def build_purchase_events(purchase_history: dict, catalog_by_asin: dict,
                          users_by_id: dict, price_by_asin: dict) -> dict:
    """
    Flatten purchase_history.json into a per-line-item event stream.
    One event record per (order, item). Enriched with catalog and user context.

    Returns dict keyed by user_id → list of event dicts, chronologically sorted.
    """
    purchase_events = {}

    for user_id, orders in purchase_history.items():
        user = users_by_id.get(user_id, {})
        household_size = user.get("household_size", 3)
        purchase_events[user_id] = []

        # Sort orders by date ascending so interval tracking is correct
        try:
            orders_sorted = sorted(orders, key=lambda o: o.get("date", ""))
        except Exception:
            orders_sorted = orders

        # Track per-(user, asin) state for enrichment
        # asin -> {last_date, purchase_count, prices, quantities}
        asin_state: dict = {}

        for order in orders_sorted:
            order_date = order.get("date", "")
            order_id = order.get("order_id", "")
            occasion_tag = order.get("occasion_tag", "routine_grocery")

            # Parse month safely
            try:
                month = int(order_date[5:7]) if len(order_date) >= 7 else 1
            except (ValueError, IndexError):
                month = 1
            season = _month_to_season(month)

            for item in order.get("items", []):
                asin = item.get("asin", "")
                if not asin:
                    continue

                catalog_item = catalog_by_asin.get(asin, {})

                # Price: prefer item's own price; fall back to catalog price
                price_paid = float(item.get("price", catalog_item.get("price", 0)))

                # avg_30d from price_history — keyed by ASIN, may be absent for MC_ ASINs
                price_data = price_by_asin.get(asin, {})
                price_avg_30d = float(price_data.get("avg_30d", price_paid))

                # Quantity
                quantity = int(item.get("quantity", 1))

                # Catalog enrichment
                category = item.get("category", catalog_item.get("category", "default"))
                subcategory = catalog_item.get("subcategory", "")
                brand = catalog_item.get("brand", "")
                pack_size_g = int(catalog_item.get("pack_size", 0))
                amazon_now_eligible = item.get(
                    "amazon_now_eligible",
                    catalog_item.get("amazon_now_eligible", True)
                )
                title = item.get("title", catalog_item.get("title", asin))

                # Per-(user, asin) state tracking
                state = asin_state.get(asin, {
                    "last_date": None,
                    "purchase_count": 0,
                    "prices": [],
                    "quantities": [],
                })

                days_since_prev = None
                prev_date = None
                prev_qty = None
                prev_price = None

                if state["last_date"]:
                    try:
                        last = date.fromisoformat(state["last_date"])
                        curr = date.fromisoformat(order_date)
                        days_since_prev = (curr - last).days
                        prev_date = state["last_date"]
                    except ValueError:
                        pass
                    if state["quantities"]:
                        prev_qty = state["quantities"][-1]
                    if state["prices"]:
                        prev_price = state["prices"][-1]

                is_probable_sale = (
                    price_paid < price_avg_30d * 0.80
                    if price_avg_30d > 0 else False
                )
                sale_discount_pct = (
                    round((1 - price_paid / price_avg_30d) * 100, 1)
                    if price_avg_30d > 0 and is_probable_sale else 0.0
                )

                event = {
                    "event_id": f"EVT_{user_id}_{order_date.replace('-', '')}_{asin}",
                    "event_type": "purchase_completed",
                    "schema_version": "2.0",
                    "user_id": user_id,
                    "order_id": order_id,
                    "event_date": order_date,
                    "asin": asin,
                    "title": title,
                    "category": category,
                    "subcategory": subcategory,
                    "brand": brand,
                    "quantity_purchased": quantity,
                    "pack_size_g": pack_size_g,
                    "price_paid_inr": price_paid,
                    "price_avg_30d_inr": price_avg_30d,
                    "is_probable_sale": is_probable_sale,
                    "sale_discount_pct": sale_discount_pct,
                    "amazon_now_eligible": bool(amazon_now_eligible),
                    "occasion_tag": occasion_tag,
                    "household_size_at_event": household_size,
                    "month_of_year": month,
                    "season": season,
                    "days_since_prev_purchase_same_asin": days_since_prev,
                    "prev_purchase_date_same_asin": prev_date,
                    "prev_quantity_same_asin": prev_qty,
                    "prev_price_paid_same_asin": prev_price,
                    "purchase_count_same_asin": state["purchase_count"] + 1,
                    "simulated_data": True,
                }
                purchase_events[user_id].append(event)

                # Update state
                state["last_date"] = order_date
                state["purchase_count"] += 1
                state["prices"].append(price_paid)
                state["quantities"].append(quantity)
                asin_state[asin] = state

    return purchase_events


# ── Step 3: Build user_product_features.json ──────────────────────────────────

def build_features(purchase_events: dict, catalog_by_asin: dict,
                   category_priors: dict) -> dict:
    """
    Compute EWMA state + feature vectors per (user, asin) pair.

    For each (user, asin):
      1. Collect all events in chronological order
      2. Extract raw intervals between consecutive purchases
      3. Run anomaly detection on each interval (via ewma_engine)
      4. Update running EWMA from clean intervals only
      5. Compute final confidence score (via ewma_engine)
      6. Write feature record keyed as "U001::MC_ARIEL_001"

    Returns dict keyed by feature_key → feature record.
    """
    from app.services.ewma_engine import (
        compute_alpha,
        update_ewma,
        run_anomaly_check,
        compute_confidence,
    )

    features: dict = {}
    computed_at = datetime.utcnow().isoformat() + "Z"

    for user_id, events in purchase_events.items():
        # Group events by asin; they are already sorted by event_date
        asin_events: dict = defaultdict(list)
        for ev in events:
            asin_events[ev["asin"]].append(ev)

        for asin, asin_ev_list in asin_events.items():
            # Ensure chronological order within the group
            asin_ev_list.sort(key=lambda e: e.get("event_date", ""))

            feature_key = f"{user_id}::{asin}"

            # Resolve category: prefer event-level, fall back to catalog
            category = asin_ev_list[-1].get("category", "default") or "default"

            # Category prior — determines cold-start interval
            prior_record = category_priors.get(category, category_priors.get("default", {}))
            category_prior_interval = float(prior_record.get("default_interval_days", 14))

            # Collect all prices and quantities for median computation
            prices = [
                e.get("price_paid_inr", 0)
                for e in asin_ev_list
                if e.get("price_paid_inr", 0) > 0
            ]
            quantities = [e.get("quantity_purchased", 1) for e in asin_ev_list]
            median_price = _median(prices) if prices else 0.0
            typical_qty = _median(quantities) if quantities else 1.0

            # Build raw interval list from consecutive events
            raw_intervals = []
            for i in range(1, len(asin_ev_list)):
                days = asin_ev_list[i].get("days_since_prev_purchase_same_asin")
                if days is not None and days > 0:
                    raw_intervals.append({
                        "days": float(days),
                        "price_paid": float(asin_ev_list[i].get("price_paid_inr", 0)),
                        "quantity": float(asin_ev_list[i].get("quantity_purchased", 1)),
                        "date": asin_ev_list[i].get("event_date", ""),
                    })

            # ── EWMA construction pipeline ─────────────────────────────────────
            running_ewma = category_prior_interval
            clean_intervals: list = []
            anomaly_count = 0
            bulk_multiplier = 1.0
            consecutive_gaps = 0

            for interval_rec in raw_intervals:
                anomaly = run_anomaly_check(
                    interval=interval_rec["days"],
                    price_paid=interval_rec["price_paid"],
                    quantity=interval_rec["quantity"],
                    median_price=median_price,
                    typical_qty=typical_qty,
                    current_ewma=running_ewma,
                )

                if anomaly.type == "bulk_sale":
                    anomaly_count += 1
                    qty_ratio = interval_rec["quantity"] / max(typical_qty, 1.0)
                    bulk_multiplier = round(qty_ratio, 2)
                    consecutive_gaps = 0
                    continue

                elif anomaly.type in ("gap", "regime_change"):
                    anomaly_count += 1
                    consecutive_gaps += 1
                    if anomaly.type == "regime_change" and running_ewma > 0:
                        # Partial reset: blend current and new interval
                        running_ewma = 0.5 * running_ewma + 0.5 * interval_rec["days"]
                        clean_intervals.append(running_ewma)
                    continue

                else:
                    # Clean interval
                    consecutive_gaps = 0
                    clean_intervals.append(interval_rec["days"])

                    # Update running EWMA once we have enough observations
                    if len(clean_intervals) >= 3:
                        n_so_far = len(clean_intervals)
                        cv = (
                            _std(clean_intervals) / max(_mean(clean_intervals), 1.0)
                            if len(clean_intervals) > 1 else 0.30
                        )
                        alpha = compute_alpha(cv, n_so_far)
                        running_ewma = (
                            alpha * interval_rec["days"]
                            + (1.0 - alpha) * running_ewma
                        )

            # ── Compute final EWMA from clean intervals ────────────────────────
            if len(clean_intervals) == 0:
                ewma_interval = category_prior_interval
                ewma_variance = (ewma_interval * 0.30) ** 2
                n_obs = 0

            elif len(clean_intervals) == 1:
                # Warm start: blend with prior
                ewma_interval = (
                    0.4 * clean_intervals[0] + 0.6 * category_prior_interval
                )
                ewma_variance = (ewma_interval * 0.30) ** 2
                n_obs = 1

            elif len(clean_intervals) == 2:
                ewma_interval = _mean(clean_intervals)
                ewma_variance = max(1.0, _variance(clean_intervals))
                n_obs = 2

            else:
                # Full EWMA pass — walk through all clean intervals sequentially
                ewma_interval = clean_intervals[0]
                ewma_variance = (ewma_interval * 0.20) ** 2

                for i, iv in enumerate(clean_intervals[1:], start=1):
                    cv = (
                        math.sqrt(ewma_variance) / max(ewma_interval, 1.0)
                    )
                    alpha = compute_alpha(cv, i)

                    # Trend adaption: react faster to large deviations
                    if iv < 0.70 * ewma_interval or iv > 1.30 * ewma_interval:
                        alpha = min(0.70, alpha + 0.10)

                    # Data scarcity cap: be conservative in early observations
                    if i < 5:
                        alpha = min(alpha, 0.35)

                    new_ewma, new_variance = update_ewma(
                        ewma_interval, ewma_variance, iv, alpha
                    )
                    ewma_interval = new_ewma
                    ewma_variance = new_variance

                n_obs = len(clean_intervals)

            # Guard: ewma_interval must be >= 1 day
            ewma_interval = max(1.0, ewma_interval)

            # ── Confidence score ───────────────────────────────────────────────
            last_ev = asin_ev_list[-1]
            last_date_str = last_ev.get("event_date", "")
            try:
                last_date = date.fromisoformat(last_date_str)
            except (ValueError, TypeError):
                last_date = DEMO_DATE

            confidence = compute_confidence(
                ewma_interval=ewma_interval,
                ewma_variance=ewma_variance,
                n_obs=n_obs,
                last_purchase_date=last_date,
                today=DEMO_DATE,
            )

            # ── Catalog enrichment for the feature record ──────────────────────
            catalog_item = catalog_by_asin.get(asin, {})
            # Price: use the item's last price paid; fall back to catalog price
            last_price_paid = float(last_ev.get("price_paid_inr", 0))
            catalog_price = float(catalog_item.get("price", last_price_paid))
            price_for_feature = last_price_paid if last_price_paid > 0 else catalog_price

            amazon_now_eligible = bool(
                last_ev.get("amazon_now_eligible",
                            catalog_item.get("amazon_now_eligible", True))
            )

            # CV for feature record
            interval_cv = (
                round(_std(clean_intervals) / max(_mean(clean_intervals), 1.0), 4)
                if len(clean_intervals) > 1 else 0.30
            )

            features[feature_key] = {
                "feature_key": feature_key,
                "user_id": user_id,
                "asin": asin,
                "title": last_ev.get("title", catalog_item.get("title", asin)),
                "category": category,
                "subcategory": (
                    last_ev.get("subcategory", "")
                    or catalog_item.get("subcategory", "")
                ),
                "brand": (
                    last_ev.get("brand", "")
                    or catalog_item.get("brand", "")
                ),
                "computed_at": computed_at,
                "purchase_count": len(asin_ev_list),
                "first_purchase_date": asin_ev_list[0].get("event_date", ""),
                "last_purchase_date": last_date_str,
                "last_quantity_purchased": int(last_ev.get("quantity_purchased", 1)),
                "avg_quantity_purchased": round(_mean(quantities), 2),
                "last_price_paid": last_price_paid,
                "avg_price_paid": round(_mean(prices), 1) if prices else catalog_price,
                "price_inr": price_for_feature,
                "amazon_now_eligible": amazon_now_eligible,
                "suggested_quantity": int(last_ev.get("quantity_purchased", 1)),
                "interval_avg_all": (
                    round(_mean(clean_intervals), 1)
                    if clean_intervals else round(ewma_interval, 1)
                ),
                "interval_cv": interval_cv,
                "ewma": {
                    "ewma_interval": round(ewma_interval, 2),
                    "ewma_variance": round(ewma_variance, 4),
                    "n_observations": n_obs,
                    "last_alpha": 0.0,  # updated on next update_on_purchase()
                    "last_purchase_date": last_date_str,
                    "last_quantity": int(last_ev.get("quantity_purchased", 1)),
                    "typical_quantity": round(typical_qty, 2),
                    "median_price_paid": round(median_price, 1),
                    "anomaly_count": anomaly_count,
                    "bulk_multiplier": bulk_multiplier,
                    "model_notes": [],
                    "last_updated": computed_at,
                },
                "anomaly_flags": {
                    "last_gap_is_outlier": False,
                    "bulk_sale_purchase": (
                        anomaly_count > 0 and bulk_multiplier != 1.0
                    ),
                    "brand_switch_detected": False,
                    "interval_trend": "stable",
                },
                "confidence": {
                    "score": confidence.score,
                    "label": confidence.label,
                    "cv": confidence.cv,
                    "n_observations": confidence.n_observations,
                    "components": confidence.components,
                },
                "simulated_data": True,
            }

    return features


# ── Step 4: Build depletion_predictions.json ──────────────────────────────────

def build_predictions(features: dict, category_priors: dict,
                      demo_date: date) -> dict:
    """
    Run predict_from_features() for every (user, asin) pair in features.

    Does NOT import depletion_engine — uses ewma_engine.predict_from_features
    directly. This avoids the circular import that would occur if depletion_engine
    were imported here while it itself imports from this data layer.

    Returns dict keyed by user_id → list of prediction dicts, sorted by
    bundle_score descending.
    """
    from app.services.ewma_engine import predict_from_features

    predictions: dict = {}
    demo_date_str = demo_date.strftime("%Y%m%d")

    for feature_key, feature in features.items():
        user_id = feature.get("user_id")
        asin = feature.get("asin")
        if not user_id or not asin:
            continue

        category = feature.get("category", "default")
        prior = category_priors.get(category, category_priors.get("default", {}))
        month_str = str(demo_date.month)
        seasonal_index = float(
            prior.get("seasonal_indices", {}).get(month_str, 1.0)
        )

        pred = predict_from_features(feature, demo_date, seasonal_index)

        # Build the full prediction record
        price_inr = float(feature.get("price_inr", 0))
        amazon_now_eligible = bool(feature.get("amazon_now_eligible", True))
        last_purchase_date = feature.get("last_purchase_date", demo_date.isoformat())
        suggested_quantity = int(feature.get("suggested_quantity", 1))

        # Compute days_remaining_at_prediction
        days_remaining = pred.get("days_remaining", 0.0)
        final_interval = pred.get("final_interval", pred.get("ewma_interval", 14.0))

        # Bundle score (mirrors _compute_bundle_score in depletion_engine)
        urgency_frac = max(0.0, (final_interval - days_remaining)) / max(final_interval, 1.0)
        conf_score = pred.get("confidence", {}).get("score", 0.0)
        value_score = min(1.0, price_inr / 500.0)
        now_score = 1.0 if amazon_now_eligible else 0.4
        bundle_score = round(
            min(1.0, urgency_frac) * 0.45
            + conf_score * 0.30
            + value_score * 0.15
            + now_score * 0.10,
            4,
        )

        full_pred = {
            "prediction_id": f"PRED_{user_id}_{asin}_{demo_date_str}",
            "user_id": user_id,
            "asin": asin,
            "title": feature.get("title", ""),
            "category": category,
            "subcategory": feature.get("subcategory", ""),
            "last_purchase_date": last_purchase_date,
            "suggested_quantity": suggested_quantity,
            "price_inr": price_inr,
            "amazon_now_eligible": amazon_now_eligible,
            "bundle_score": bundle_score,
            "simulated_data": True,
            # Fields from predict_from_features
            "ewma_interval": pred.get("ewma_interval", 14.0),
            "seasonal_index_current_month": seasonal_index,
            "seasonal_adjusted_interval": pred.get("seasonal_adjusted_interval", 14.0),
            "bulk_multiplier": pred.get("bulk_multiplier", 1.0),
            "final_interval": final_interval,
            "days_remaining_at_prediction": days_remaining,
            "reorder_urgency": pred.get("reorder_urgency", "normal"),
            "should_alert_today": bool(pred.get("should_alert_today", False)),
            "confidence": pred.get("confidence", {
                "score": 0.0,
                "percentage": 0,
                "label": "Insufficient",
                "cv": 1.0,
                "n_observations": 0,
                "components": {},
            }),
            "model_notes": feature.get("ewma", {}).get("model_notes", []),
            "anomalies_detected_count": feature.get("ewma", {}).get("anomaly_count", 0),
        }

        if user_id not in predictions:
            predictions[user_id] = []
        predictions[user_id].append(full_pred)

    # Sort each user's predictions by bundle_score descending
    for uid in predictions:
        predictions[uid].sort(key=lambda p: p.get("bundle_score", 0.0), reverse=True)

    return predictions


# ── Step 5: Validation ────────────────────────────────────────────────────────

def validate_demo_invariants(predictions: dict) -> bool:
    """
    Print a validation table for U001's top predictions.
    Returns True if all demo invariants are satisfied, False otherwise.
    """
    print()
    print("=== U001 Demo Validation ===")
    print(f"{'ASIN':<20} | {'Interval':>8} | {'Days Left':>9} | {'Urgency':>8} | {'Confidence':>10} | {'Label'}")
    print("-" * 80)

    u001_preds = predictions.get("U001", [])
    pred_by_asin = {p["asin"]: p for p in u001_preds}

    all_ok = True

    for asin, constraints in DEMO_ASINS.items():
        pred = pred_by_asin.get(asin)

        if not pred:
            print(f"{'[MISSING] ' + asin:<20} | {'N/A':>8} | {'N/A':>9} | {'N/A':>8} | {'N/A':>10} | N/A")
            print(
                f"  WARNING: {asin} ({constraints['description']}) "
                f"not found in U001 predictions."
            )
            print(
                f"           Re-run with more purchase history for this ASIN. "
                f"Ensure U001 has 4+ orders of {asin}."
            )
            all_ok = False
            continue

        conf = pred.get("confidence", {})
        label = conf.get("label", "Insufficient")
        score = conf.get("score", 0.0)
        days_left = pred.get("days_remaining_at_prediction", 99.0)
        interval = pred.get("ewma_interval", 0.0)
        urgency = pred.get("reorder_urgency", "unknown")

        status = "OK"
        if label == "Insufficient":
            status = "FAIL"
            all_ok = False
        elif days_left > constraints["max_days_remaining"]:
            status = "WARN"

        flag = "" if status == "OK" else f"  [{status}]"
        print(
            f"{asin:<20} | {interval:>7.1f}d | {days_left:>8.1f}d | {urgency:>8} | "
            f"{score:>10.4f} | {label}{flag}"
        )

        if status == "FAIL":
            print(
                f"  WARNING: {asin} has label '{label}' (score={score:.4f}). "
                f"This item will be filtered out by build_morning_bundle()."
            )
            print(
                f"           Need >= 4 clean purchase intervals for '{label}' to improve. "
                f"Add more orders for U001 in purchase_history.json."
            )
        elif status == "WARN":
            print(
                f"  WARN: {asin} days_remaining={days_left:.1f} "
                f"(expected <= {constraints['max_days_remaining']}). "
                f"Item will still appear but may not show as urgent."
            )

    print()

    # Print top 5 predictions for U001 regardless of demo ASINs
    if u001_preds:
        print("U001 top 5 predictions by bundle_score:")
        print(f"{'ASIN':<20} | {'Title':<35} | {'Score':>6} | {'Days':>5} | {'Label'}")
        print("-" * 85)
        for p in u001_preds[:5]:
            title_trunc = (p.get("title", "") or "")[:34]
            print(
                f"{p.get('asin', ''):<20} | {title_trunc:<35} | "
                f"{p.get('bundle_score', 0):>6.4f} | "
                f"{p.get('days_remaining_at_prediction', 0):>5.1f} | "
                f"{p.get('confidence', {}).get('label', '?')}"
            )
    else:
        print("No predictions found for U001.")

    print()
    if all_ok:
        print("All demo invariants satisfied.")
    else:
        print(
            "WARNING: Some demo invariants failed. "
            "Check purchase_history.json for sufficient U001 purchase history."
        )
    return all_ok


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("MissionCart — build_depletion_data.py")
    print(f"Demo date: {DEMO_DATE.isoformat()}")
    print("=" * 60)

    # Ensure simulated/ directory exists
    SIM_PATH.mkdir(parents=True, exist_ok=True)

    # ── Step 1: Write category_priors.json (idempotent) ──────────────────────
    priors_path = DATA_PATH / "category_priors.json"
    if not priors_path.exists():
        print("Step 1: Writing category_priors.json (not found, generating)...")
    else:
        print("Step 1: Refreshing category_priors.json...")
    priors_path.write_text(
        json.dumps(CATEGORY_PRIORS, indent=2), encoding="utf-8"
    )
    print(f"  Written: {priors_path}")

    # ── Step 1b: Load all source data ────────────────────────────────────────
    print()
    print("Loading source data files...")

    ph_path = SIM_PATH / "purchase_history.json"
    users_path = SIM_PATH / "users.json"
    catalog_path = DATA_PATH / "catalog.json"
    ph_price_path = SIM_PATH / "price_history.json"

    # purchase_history.json — required
    if not ph_path.exists():
        print(f"  ERROR: {ph_path} not found. Cannot proceed.")
        sys.exit(1)
    with open(ph_path, encoding="utf-8") as f:
        purchase_history = json.load(f)
    total_orders = sum(len(v) for v in purchase_history.values())
    print(f"  purchase_history.json: {len(purchase_history)} users, {total_orders} orders")

    # users.json — required for household_size
    if not users_path.exists():
        print(f"  WARNING: {users_path} not found. Using default household_size=3.")
        users_by_id: dict = {}
    else:
        with open(users_path, encoding="utf-8") as f:
            users_list = json.load(f)
        # users.json is a list of user dicts
        users_by_id = {u["user_id"]: u for u in users_list if "user_id" in u}
        print(f"  users.json: {len(users_by_id)} users loaded")

    # catalog.json — enrichment source
    if not catalog_path.exists():
        print(f"  WARNING: {catalog_path} not found. Catalog enrichment skipped.")
        catalog_by_asin: dict = {}
    else:
        with open(catalog_path, encoding="utf-8") as f:
            catalog_raw = json.load(f)
        # catalog.json is a list of product dicts
        catalog_by_asin = {
            p["asin"]: p for p in catalog_raw if "asin" in p
        }
        print(f"  catalog.json: {len(catalog_by_asin)} products loaded")

    # price_history.json — for sale detection (keyed by catalog ASIN)
    if not ph_price_path.exists():
        print(f"  WARNING: {ph_price_path} not found. avg_30d will use item price.")
        price_by_asin: dict = {}
    else:
        with open(ph_price_path, encoding="utf-8") as f:
            price_by_asin = json.load(f)
        print(f"  price_history.json: {len(price_by_asin)} ASINs loaded")

    # ── Step 2: Build purchase_events.json ────────────────────────────────────
    print()
    print("Step 2: Building purchase_events.json...")
    purchase_events = build_purchase_events(
        purchase_history, catalog_by_asin, users_by_id, price_by_asin
    )
    total_events = sum(len(v) for v in purchase_events.values())
    print(f"  Generated {total_events} events across {len(purchase_events)} users")

    events_path = SIM_PATH / "purchase_events.json"
    events_path.write_text(
        json.dumps(purchase_events, indent=2), encoding="utf-8"
    )
    print(f"  Written: {events_path}")

    # ── Step 3: Build user_product_features.json ──────────────────────────────
    print()
    print("Step 3: Building user_product_features.json (EWMA state + features)...")
    features = build_features(purchase_events, catalog_by_asin, CATEGORY_PRIORS)
    print(f"  Computed {len(features)} (user, asin) feature records")

    features_path = SIM_PATH / "user_product_features.json"
    features_path.write_text(
        json.dumps(features, indent=2), encoding="utf-8"
    )
    print(f"  Written: {features_path}")

    # Quick sanity: U001 feature count
    u001_feature_count = sum(
        1 for k in features if k.startswith("U001::")
    )
    print(f"  U001 has {u001_feature_count} distinct (user, asin) feature records")

    # ── Step 4: Build depletion_predictions.json ──────────────────────────────
    print()
    print("Step 4: Building depletion_predictions.json...")
    predictions = build_predictions(features, CATEGORY_PRIORS, DEMO_DATE)
    total_preds = sum(len(v) for v in predictions.values())
    print(f"  Generated {total_preds} predictions across {len(predictions)} users")

    preds_path = SIM_PATH / "depletion_predictions.json"
    preds_path.write_text(
        json.dumps(predictions, indent=2), encoding="utf-8"
    )
    print(f"  Written: {preds_path}")

    u001_pred_count = len(predictions.get("U001", []))
    print(f"  U001 has {u001_pred_count} predictions")

    # ── Step 5: Validate demo invariants ─────────────────────────────────────
    print()
    print("Step 5: Validating demo invariants...")
    validate_demo_invariants(predictions)

    # ── Summary ───────────────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print("Build complete. Output files:")
    print(f"  {priors_path}")
    print(f"  {events_path}")
    print(f"  {features_path}")
    print(f"  {preds_path}")
    print()
    print("Production migration note:")
    print("  purchase_history.json  -> Amazon DynamoDB order events via EventBridge")
    print("  catalog.json           -> Amazon PA API v5")
    print("  price_history.json     -> Amazon Price API + DynamoDB cache")
    print("  EWMA features          -> Amazon SageMaker Feature Store")
    print("  Predictions            -> SageMaker Batch Transform (nightly)")
    print("=" * 60)


if __name__ == "__main__":
    main()
