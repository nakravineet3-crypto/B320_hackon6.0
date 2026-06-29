"""
depletion_engine.py — Stateful singleton service for MissionCart Smart Reorder.

This is the ONLY file that reorder.py calls. All prediction logic lives here.
The router is protocol translation only.

Architecture:
  - Loaded once at startup via load() (async, guarded by asyncio.Lock)
  - build_morning_bundle() is sync — no I/O, no LLM
  - explain() is async — may call LLM, results cached in _explain_cache
  - update_on_purchase() is sync — online EWMA update, persists async via create_task

LLM principle: explain() generates copy for a DECISION ALREADY MADE by
deterministic systems. The LLM does not decide what goes in the card.
"""

import asyncio
import json
import math
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional


# ── Depletion prediction dataclass ─────────────────────────────────────────────

@dataclass
class DepletionPrediction:
    prediction_id: str
    user_id: str
    asin: str
    title: str
    category: str
    subcategory: str
    last_purchase_date: str          # ISO date string
    suggested_quantity: int
    price_inr: float
    amazon_now_eligible: bool
    ewma_interval: float
    final_interval: float
    days_remaining: float
    reorder_urgency: str             # "urgent" | "soon" | "normal" | "low"
    should_alert_today: bool
    bundle_score: float
    confidence: dict                 # ConfidenceResult fields as dict
    simulated_data: bool = True


# ── Private helpers ─────────────────────────────────────────────────────────────

def _compute_urgency(days_remaining: float) -> str:
    if days_remaining <= 2:
        return "urgent"
    elif days_remaining <= 5:
        return "soon"
    elif days_remaining <= 7:
        return "normal"
    else:
        return "low"


def _compute_bundle_score(
    days_remaining: float,
    final_interval: float,
    confidence_score: float,
    price_inr: float,
    amazon_now_eligible: bool,
) -> float:
    """
    Composite bundle score used to rank items for the morning card.
    Weights: urgency 0.45 + confidence 0.30 + value 0.15 + now_eligible 0.10
    """
    urgency_fraction = max(0, (final_interval - days_remaining)) / max(final_interval, 1.0)
    urgency_score = max(0.0, min(1.0, urgency_fraction))
    conf_score = max(0.0, min(1.0, confidence_score))
    value_score = min(1.0, price_inr / 500.0)
    now_score = 1.0 if amazon_now_eligible else 0.4

    return round(
        urgency_score * 0.45 +
        conf_score * 0.30 +
        value_score * 0.15 +
        now_score * 0.10,
        4
    )


# ── Explanation prompt constants ────────────────────────────────────────────────

_EXPLANATION_SYSTEM_PROMPT = """You write concise, personal notification copy for a grocery reorder app.
You are given pre-computed prediction data. Write 1 sentence that feels human, not robotic.
Never use the words "predicted", "algorithm", or "model".
Rules:
- If days_remaining <= 1: mention the product and "running low now"
- If days_remaining 2-3: mention "in about N days"
- If model_notes contains "consumption_accelerating": mention going through it faster lately
- Use "you" (second person) throughout
- Under 70 characters. Start with the product name.
Example good: "Ariel 2kg — you buy this every 28 days. Last bought 24 days ago."
Example bad: "Predicted depletion in 4 days based on your purchase history." """


def _build_explanation_user_prompt(
    title: str,
    ewma_interval: float,
    days_since: int,
    days_remaining: float,
    confidence_label: str,
    model_notes: list,
) -> str:
    notes = ", ".join(model_notes) if model_notes else "none"
    return (
        f"Product: {title}\n"
        f"Purchase interval: every {int(round(ewma_interval))} days\n"
        f"Days since last purchase: {days_since}\n"
        f"Days remaining until empty: {days_remaining:.0f}\n"
        f"Confidence level: {confidence_label}\n"
        f"Model notes: {notes}\n\n"
        f"Write the 1-sentence explanation."
    )


# ── Embedded minimal priors (emergency fallback when category_priors.json absent) ──

_EMBEDDED_MINIMAL_PRIORS = {
    "dairy":     {"default_interval_days": 3,  "seasonal_indices": {str(i): 1.0 for i in range(1, 13)}},
    "laundry":   {"default_interval_days": 30, "seasonal_indices": {"6": 1.15, "7": 1.15, "8": 1.15, **{str(i): 1.0 for i in [1, 2, 3, 4, 5, 9, 10, 11, 12]}}},
    "household": {"default_interval_days": 14, "seasonal_indices": {str(i): 1.0 for i in range(1, 13)}},
    "default":   {"default_interval_days": 14, "seasonal_indices": {str(i): 1.0 for i in range(1, 13)}},
}


# ── DepletionEngine ─────────────────────────────────────────────────────────────

class DepletionEngine:
    """
    Stateful singleton service for Smart Reorder predictions.

    Load sequence (called once at startup via load()):
      1. category_priors.json → _priors
      2. user_product_features.json → _features
      3. depletion_predictions.json → _predictions (or rebuild from _features)

    Public API:
      load()                   async — startup warm, guarded by asyncio.Lock
      build_morning_bundle()   sync  — returns 3-5 DepletionPrediction objects
      predict()                sync  — single (user, asin) prediction
      update_on_purchase()     sync  — online EWMA update on new purchase
      explain()                async — LLM explanation copy, cached
    """

    def __init__(self):
        self._predictions: dict[str, list[dict]] = {}     # user_id → sorted list of prediction dicts
        self._features: dict[str, dict] = {}              # "U001::MC_ARIEL_001" → feature record
        self._priors: dict[str, dict] = {}                # category → prior dict
        self._loaded: bool = False
        self._load_lock = asyncio.Lock()
        self._explain_cache: dict[str, tuple[str, str]] = {}   # cache_key → (copy, model_used)

    # ── Startup loading ─────────────────────────────────────────────────────────

    async def load(self) -> None:
        """Load all prediction data into memory. Called once at startup."""
        async with self._load_lock:
            if self._loaded:
                return

            BASE = Path(__file__).parent.parent / "data"

            # Load category priors
            priors_path = BASE / "category_priors.json"
            if priors_path.exists():
                with open(priors_path, encoding="utf-8") as f:
                    self._priors = json.load(f)
            else:
                self._priors = _EMBEDDED_MINIMAL_PRIORS
                print("[DepletionEngine] category_priors.json missing — using embedded minimal priors")

            # Load user product features (for online updates and rebuild fallback)
            features_path = BASE / "simulated" / "user_product_features.json"
            if features_path.exists():
                with open(features_path, encoding="utf-8") as f:
                    self._features = json.load(f)
            else:
                print("[DepletionEngine] WARNING: user_product_features.json missing")

            # Load materialized predictions (primary hot path)
            preds_path = BASE / "simulated" / "depletion_predictions.json"
            if preds_path.exists():
                with open(preds_path, encoding="utf-8") as f:
                    self._predictions = json.load(f)
                self._loaded = True
                print(f"[DepletionEngine] Loaded predictions for {len(self._predictions)} users")
                return

            # Fallback: rebuild predictions from features if predictions file is missing
            if self._features:
                print("[DepletionEngine] predictions file missing — rebuilding from features...")
                self._rebuild_from_features()
                self._loaded = True
                return

            # Last resort: still mark loaded so we serve from _fallback_bundle
            print("[DepletionEngine] WARNING: No prediction data available — using static fallback")
            self._loaded = True

    # ── Rebuild path ────────────────────────────────────────────────────────────

    def _rebuild_from_features(self) -> None:
        """Rebuild predictions from feature records when the materialized file is absent."""
        from .ewma_engine import predict_from_features

        today = date.today()
        predictions: dict[str, list[dict]] = {}

        for feature_key, feature in self._features.items():
            user_id = feature.get("user_id")
            if not user_id:
                continue
            category = feature.get("category", "default")
            prior = self._priors.get(category, self._priors.get("default", {}))
            seasonal_index = float(prior.get("seasonal_indices", {}).get(str(today.month), 1.0))

            try:
                pred = predict_from_features(feature, today, seasonal_index)
                full_pred = {**feature, **pred}

                if user_id not in predictions:
                    predictions[user_id] = []
                predictions[user_id].append(full_pred)
            except Exception:
                continue

        for uid in predictions:
            predictions[uid].sort(key=lambda p: p.get("bundle_score", 0), reverse=True)

        self._predictions = predictions

    # ── Core prediction logic ───────────────────────────────────────────────────

    def build_morning_bundle(self, user_id: str) -> list[DepletionPrediction]:
        """
        Return 3-5 items for the morning reorder card.

        Selection criteria:
          - confidence.label != "Insufficient"
          - reorder_urgency in ("urgent", "soon", "normal")
          - top N by bundle_score
          - between 3 and 5 items (return fewer only if truly insufficient data)
        """
        if not self._loaded:
            return self._fallback_bundle(user_id)

        user_preds = self._predictions.get(user_id, [])

        if not user_preds:
            return self._fallback_bundle(user_id)

        # Apply live days_remaining correction and re-score bundle_score
        today = date.today()
        live_preds = []
        for p in user_preds:
            try:
                last_date = date.fromisoformat(p.get("last_purchase_date", today.isoformat()))
                days_since = (today - last_date).days
                final_interval = float(p.get("final_interval", p.get("ewma_interval", 14.0)))
                live_days_remaining = max(0.0, final_interval - days_since)

                # Recompute urgency and bundle_score with live days_remaining
                live_urgency = _compute_urgency(live_days_remaining)
                live_bundle_score = _compute_bundle_score(
                    days_remaining=live_days_remaining,
                    final_interval=final_interval,
                    confidence_score=float(p.get("confidence", {}).get("score", 0.5)),
                    price_inr=float(p.get("price_inr", 0)),
                    amazon_now_eligible=bool(p.get("amazon_now_eligible", True)),
                )

                # Build an updated copy of the dict with live values
                live_p = dict(p)
                live_p["days_remaining"] = round(live_days_remaining, 1)
                live_p["reorder_urgency"] = live_urgency
                live_p["bundle_score"] = live_bundle_score
                live_p["should_alert_today"] = live_days_remaining <= 1.0
                live_preds.append(live_p)
            except Exception:
                live_preds.append(p)

        # Filter: exclude Insufficient confidence and "low" urgency items
        eligible = [
            p for p in live_preds
            if p.get("confidence", {}).get("label") != "Insufficient"
            and p.get("reorder_urgency", "low") in ("urgent", "soon", "normal")
        ]

        # Take top 5 by bundle_score (sort eligible descending)
        eligible.sort(key=lambda p: p.get("bundle_score", 0), reverse=True)
        top_preds = eligible[:5]

        # Force-include any already-run-out items that didn't make top 5
        urgent_force = [
            p for p in eligible[5:]
            if p.get("days_remaining", 99) <= 0
        ]
        top_preds = top_preds + urgent_force
        top_preds = top_preds[:7]  # hard cap

        # Amazon Now guarantee: if none in top set and a now-eligible item exists
        # with bundle_score >= 0.40, swap out lowest-ranked non-Now item
        now_count = sum(1 for p in top_preds if p.get("amazon_now_eligible", True))
        if now_count == 0:
            now_candidates = [
                p for p in eligible
                if p.get("amazon_now_eligible", False)
                and p.get("bundle_score", 0) >= 0.40
                and p not in top_preds
            ]
            if now_candidates and top_preds:
                non_now = [p for p in top_preds if not p.get("amazon_now_eligible", True)]
                if non_now:
                    swap_out = min(non_now, key=lambda p: p.get("bundle_score", 0))
                    top_preds.remove(swap_out)
                    top_preds.append(now_candidates[0])

        # If we have fewer than 3 eligible, pad with next-best items regardless of urgency
        if len(top_preds) < 3:
            rest = [p for p in live_preds if p not in top_preds]
            rest.sort(key=lambda p: p.get("bundle_score", 0), reverse=True)
            top_preds.extend(rest[:3 - len(top_preds)])

        # Final sort and return
        top_preds.sort(key=lambda p: p.get("bundle_score", 0), reverse=True)
        return [self._dict_to_prediction(p) for p in top_preds]

    def predict(self, user_id: str, asin: str, today=None) -> Optional[DepletionPrediction]:
        """Return the current prediction for a specific (user, asin) pair."""
        if today is None:
            today = date.today()

        feature_key = f"{user_id}::{asin}"

        # Check materialized predictions first
        user_preds = self._predictions.get(user_id, [])
        for p in user_preds:
            if p.get("asin") == asin:
                return self._dict_to_prediction(p)

        # Fallback: compute from features if available
        feature = self._features.get(feature_key)
        if feature:
            from .ewma_engine import predict_from_features
            category = feature.get("category", "default")
            prior = self._priors.get(category, self._priors.get("default", {}))
            seasonal_index = float(prior.get("seasonal_indices", {}).get(str(today.month), 1.0))
            pred = predict_from_features(feature, today, seasonal_index)
            return self._dict_to_prediction({**feature, **pred})

        return None

    # ── Online EWMA update ──────────────────────────────────────────────────────

    def update_on_purchase(self, user_id: str, asin: str, purchase_event: dict) -> None:
        """
        Online EWMA update when a new purchase is recorded.

        Called from the /approve endpoint in reorder.py after a successful order.
        Updates the in-memory feature record. The updated predictions file is
        NOT persisted here (that's the build script's job for next day's run).
        """
        from .ewma_engine import (
            compute_alpha, update_ewma, run_anomaly_check,
        )

        feature_key = f"{user_id}::{asin}"
        feature = self._features.get(feature_key)

        if not feature:
            return  # No feature record — cold start path, skip online update

        # Compute the new interval
        last_purchase_str = feature.get("last_purchase_date", "")
        try:
            last_date = date.fromisoformat(last_purchase_str)
            new_interval = (date.today() - last_date).days
        except (ValueError, TypeError):
            return  # Can't compute interval without last date

        if new_interval <= 0:
            return  # Same-day repurchase — skip

        ewma_state = feature.get("ewma", {})
        current_ewma = ewma_state.get("ewma_interval", 14.0)
        current_variance = ewma_state.get("ewma_variance", (current_ewma * 0.30) ** 2)
        n_obs = ewma_state.get("n_observations", 0)

        # Anomaly check — if anomalous, skip EWMA update for this interval
        anomaly = run_anomaly_check(
            interval=new_interval,
            price_paid=purchase_event.get("price_paid", feature.get("price_inr", 0)),
            quantity=purchase_event.get("quantity", 1),
            median_price=ewma_state.get("median_price_paid", feature.get("price_inr", 0)),
            typical_qty=ewma_state.get("typical_quantity", 1.0),
            current_ewma=current_ewma,
        )

        if anomaly.type in ("gap", "regime_change"):
            # Skip EWMA update for anomalous intervals — don't corrupt the model
            feature["last_purchase_date"] = date.today().isoformat()
            self._features[feature_key] = feature
            return

        # Compute adaptive alpha and update EWMA
        cv = (current_variance ** 0.5) / max(current_ewma, 1.0)
        alpha = compute_alpha(cv, n_obs)
        new_ewma, new_variance = update_ewma(current_ewma, current_variance, new_interval, alpha)

        # Update feature in memory
        if "ewma" not in feature:
            feature["ewma"] = {}
        feature["ewma"]["ewma_interval"] = round(new_ewma, 2)
        feature["ewma"]["ewma_variance"] = round(new_variance, 4)
        feature["ewma"]["n_observations"] = n_obs + 1
        feature["last_purchase_date"] = date.today().isoformat()
        self._features[feature_key] = feature

        # Recompute prediction for this user+asin and update predictions cache
        from .ewma_engine import predict_from_features
        category = feature.get("category", "default")
        prior = self._priors.get(category, self._priors.get("default", {}))
        today = date.today()
        seasonal_index = float(prior.get("seasonal_indices", {}).get(str(today.month), 1.0))
        new_pred = predict_from_features(feature, today, seasonal_index)
        updated_pred = {**feature, **new_pred}

        # Update in predictions cache
        user_preds = self._predictions.get(user_id, [])
        for i, p in enumerate(user_preds):
            if p.get("asin") == asin:
                user_preds[i] = updated_pred
                break
        else:
            user_preds.append(updated_pred)

        # Re-sort by bundle_score
        user_preds.sort(key=lambda p: p.get("bundle_score", 0), reverse=True)
        self._predictions[user_id] = user_preds

        # Persist features async (non-blocking)
        try:
            asyncio.create_task(self._persist_features_async())
        except RuntimeError:
            pass  # No running event loop — skip persist (e.g. during tests)

    async def _persist_features_async(self) -> None:
        """Write _features to disk. Called via create_task so it does not block response."""
        try:
            features_path = Path(__file__).parent.parent / "data" / "simulated" / "user_product_features.json"
            content = json.dumps(self._features, indent=2)
            await asyncio.to_thread(features_path.write_text, content, encoding="utf-8")
        except Exception:
            pass  # Non-fatal

    # ── LLM explanation ─────────────────────────────────────────────────────────

    async def explain(self, prediction: DepletionPrediction) -> tuple[str, str]:
        """
        Generate natural language explanation for why this item is in the morning card.
        Returns (copy, model_used).

        LLM PRINCIPLE: This method generates an explanation for a DECISION ALREADY MADE
        by deterministic systems. The LLM does NOT decide what goes in the card.
        """
        cache_key = f"{prediction.asin}::{prediction.confidence.get('label', 'Medium')}::{prediction.reorder_urgency}"

        if cache_key in self._explain_cache:
            return self._explain_cache[cache_key]

        # Compute days_since for the prompt
        try:
            last_date = date.fromisoformat(prediction.last_purchase_date)
            days_since = (date.today() - last_date).days
        except (ValueError, TypeError):
            days_since = int(prediction.ewma_interval)

        # Build template fallback first — used if LLM fails
        days = int(prediction.days_remaining)
        label = prediction.confidence.get("label", "Medium")
        urgency = prediction.reorder_urgency

        if urgency == "urgent" and days <= 0:
            template_copy = f"You're likely out of this or will be today."
        elif urgency == "urgent":
            template_copy = f"Running low — based on your purchase history, about {days} day{'s' if days != 1 else ''} left."
        elif urgency == "soon":
            template_copy = f"Reorder in the next few days to avoid running out."
        else:
            template_copy = f"Coming up in about {days} days based on your history."

        # Attempt LLM explanation (non-blocking — failure returns template)
        try:
            from .llm.factory import get_llm_client

            client = get_llm_client()
            if client is None:
                raise RuntimeError("No LLM client available")

            system_prompt = _EXPLANATION_SYSTEM_PROMPT
            user_message = _build_explanation_user_prompt(
                title=prediction.title,
                ewma_interval=prediction.ewma_interval,
                days_since=days_since,
                days_remaining=prediction.days_remaining,
                confidence_label=label,
                model_notes=[],  # not stored on DepletionPrediction dataclass
            )

            result = await asyncio.wait_for(
                client.complete(
                    system_prompt=system_prompt,
                    user_message=user_message,
                    max_tokens=80,
                    temperature=0.3,
                ),
                timeout=3.0,
            )

            copy = result.text.strip().strip('"').strip("'")
            model_used = result.model

            self._explain_cache[cache_key] = (copy, model_used)
            return (copy, model_used)

        except Exception:
            # LLM failed — use template silently. Never fail the morning card because of explain().
            self._explain_cache[cache_key] = (template_copy, "template")
            return (template_copy, "template")

    # ── Fallback bundle ─────────────────────────────────────────────────────────

    def _fallback_bundle(self, user_id: str) -> list[DepletionPrediction]:
        """Read depletion_alerts.json (static) and return its items as DepletionPrediction objects."""
        alerts_path = Path(__file__).parent.parent / "data" / "simulated" / "depletion_alerts.json"
        if not alerts_path.exists():
            return []

        try:
            with open(alerts_path, encoding="utf-8") as f:
                data = json.load(f)

            # depletion_alerts.json is keyed by user_id → list
            raw = data.get(user_id, data if isinstance(data, list) else [])
            alerts = raw if isinstance(raw, list) else []

            today = date.today()
            predictions = []

            for alert in alerts[:5]:
                # Compute live days_remaining (fix stale value)
                try:
                    last_date = date.fromisoformat(alert.get("last_purchased", today.isoformat()))
                    interval = float(alert.get("average_interval_days", alert.get("interval_days", 14)))
                    days_since = (today - last_date).days
                    days_remaining = max(0.0, interval - days_since)
                except (ValueError, TypeError):
                    days_remaining = float(alert.get("days_remaining", 3))
                    interval = float(alert.get("average_interval_days", 14))

                urgency = _compute_urgency(days_remaining)

                pred = DepletionPrediction(
                    prediction_id=f"FALLBACK_{alert.get('asin', 'UNKNOWN')}",
                    user_id=user_id,
                    asin=alert.get("asin", ""),
                    title=alert.get("title", alert.get("product_name", "")),
                    category=alert.get("category", "household"),
                    subcategory=alert.get("subcategory", ""),
                    last_purchase_date=alert.get("last_purchased", today.isoformat()),
                    suggested_quantity=int(alert.get("suggested_quantity", 1)),
                    price_inr=float(alert.get("price", alert.get("price_inr", 0))),
                    amazon_now_eligible=bool(alert.get("amazon_now_eligible", True)),
                    ewma_interval=interval,
                    final_interval=interval,
                    days_remaining=round(days_remaining, 1),
                    reorder_urgency=urgency,
                    should_alert_today=days_remaining <= 1.0,
                    bundle_score=0.5,  # Static fallback gets neutral bundle score
                    confidence={
                        "score": 0.50,
                        "percentage": 50,
                        "label": "Estimated",
                        "cv": 0.30,
                        "n_observations": int(alert.get("purchase_count", 0)),
                        "components": {},
                    },
                    simulated_data=True,
                )
                predictions.append(pred)

            return predictions

        except Exception as e:
            print(f"[DepletionEngine] Fallback bundle failed: {e}")
            return []

    # ── Conversion helper ───────────────────────────────────────────────────────

    def _dict_to_prediction(self, pred_dict: dict) -> DepletionPrediction:
        """Convert a raw prediction dict (from JSON) into a DepletionPrediction dataclass."""
        conf = pred_dict.get("confidence", {})

        # days_remaining: prefer live-computed value if present, else stored value
        days_remaining = float(
            pred_dict.get("days_remaining",
            pred_dict.get("days_remaining_at_prediction", 7))
        )

        return DepletionPrediction(
            prediction_id=pred_dict.get("prediction_id", f"PRED_{pred_dict.get('asin', '')}"),
            user_id=pred_dict.get("user_id", ""),
            asin=pred_dict.get("asin", ""),
            title=pred_dict.get("title", ""),
            category=pred_dict.get("category", ""),
            subcategory=pred_dict.get("subcategory", ""),
            last_purchase_date=pred_dict.get("last_purchase_date", ""),
            suggested_quantity=int(pred_dict.get("suggested_quantity", 1)),
            price_inr=float(pred_dict.get("price_inr", 0)),
            amazon_now_eligible=bool(pred_dict.get("amazon_now_eligible", True)),
            ewma_interval=float(pred_dict.get("ewma_interval", 14)),
            final_interval=float(pred_dict.get("final_interval", pred_dict.get("ewma_interval", 14))),
            days_remaining=days_remaining,
            reorder_urgency=pred_dict.get("reorder_urgency", "normal"),
            should_alert_today=bool(pred_dict.get("should_alert_today", False)),
            bundle_score=float(pred_dict.get("bundle_score", 0)),
            confidence={
                "score": float(conf.get("score", 0.5)),
                "percentage": int(conf.get("percentage", 50)),
                "label": conf.get("label", "Estimated"),
                "cv": float(conf.get("cv", 0.3)),
                "n_observations": int(conf.get("n_observations", 0)),
                "components": conf.get("components", {}),
            },
            simulated_data=True,
        )


# ── Module-level singleton — imported by reorder.py ────────────────────────────
depletion_engine = DepletionEngine()
