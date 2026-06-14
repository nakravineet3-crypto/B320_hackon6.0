"""Compute depletion alerts from actual recurring purchase intervals."""

import json
from collections import defaultdict
from datetime import date
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND_DIR / "app" / "data" / "simulated"
PURCHASES_PATH = DATA_DIR / "purchase_history.json"
OUTPUT_PATH = DATA_DIR / "depletion_alerts.json"
TODAY = date(2026, 6, 14)
DEMO_ALERT_LIMITS = {"U001": 8, "U002": 5, "U003": 4}


def main() -> None:
    with PURCHASES_PATH.open(encoding="utf-8") as file:
        all_history = json.load(file)

    all_alerts = {}
    urgency_order = {"urgent": 0, "soon": 1, "normal": 2, "low": 3}

    for user_id, orders in all_history.items():
        product_purchases = defaultdict(list)
        for order in orders:
            if order.get("occasion_tag") != "routine_grocery":
                continue
            for item in order.get("items", []):
                product_purchases[item["asin"]].append(
                    {
                        "date": order["date"],
                        "quantity": item.get("quantity", 1),
                        "price": item.get("price", 0),
                        "title": item.get("title", ""),
                        "category": item.get("category", ""),
                        "amazon_now_eligible": item.get(
                            "amazon_now_eligible", True
                        ),
                    }
                )

        user_alerts = []
        for asin, purchases in product_purchases.items():
            if len(purchases) < 2:
                continue
            purchases.sort(key=lambda purchase: purchase["date"])
            intervals = [
                (
                    date.fromisoformat(purchases[index]["date"])
                    - date.fromisoformat(purchases[index - 1]["date"])
                ).days
                for index in range(1, len(purchases))
            ]
            avg_interval = sum(intervals) / len(intervals)
            last_purchase = date.fromisoformat(purchases[-1]["date"])
            days_since = (TODAY - last_purchase).days
            raw_days_remaining = avg_interval - days_since

            if raw_days_remaining <= 2:
                urgency = "urgent"
            elif raw_days_remaining <= 5:
                urgency = "soon"
            elif raw_days_remaining <= 10:
                urgency = "normal"
            else:
                urgency = "low"

            if raw_days_remaining > 14 and user_id not in DEMO_ALERT_LIMITS:
                continue

            confidence = (
                "high" if len(intervals) >= 4
                else "medium" if len(intervals) >= 2
                else "estimated"
            )
            latest = purchases[-1]
            user_alerts.append(
                {
                    "asin": asin,
                    "title": latest["title"],
                    "category": latest["category"],
                    "average_interval_days": round(avg_interval, 1),
                    "last_purchased": latest["date"],
                    "days_since_purchase": days_since,
                    "days_remaining": round(max(0, raw_days_remaining), 1),
                    "confidence": confidence,
                    "suggested_quantity": latest["quantity"],
                    "price": latest["price"],
                    "amazon_now_eligible": latest["amazon_now_eligible"],
                    "reorder_urgency": urgency,
                    "purchase_count": len(purchases),
                    "avg_interval_days": round(avg_interval, 1),
                }
            )

        user_alerts.sort(
            key=lambda alert: (
                urgency_order.get(alert["reorder_urgency"], 4),
                alert["days_remaining"],
                -alert["purchase_count"],
            )
        )
        if user_id in DEMO_ALERT_LIMITS:
            user_alerts = user_alerts[: DEMO_ALERT_LIMITS[user_id]]
        all_alerts[user_id] = user_alerts

    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(all_alerts, file, indent=2)

    total_alerts = sum(len(value) for value in all_alerts.values())
    users_with_alerts = sum(bool(value) for value in all_alerts.values())
    sneha_alerts = all_alerts.get("U001", [])
    urgent = [
        alert for alert in sneha_alerts
        if alert["reorder_urgency"] == "urgent"
    ]
    print("Depletion alerts generated:")
    print(f"  Total alerts: {total_alerts}")
    print(f"  Users with alerts: {users_with_alerts}")
    print(f"\nSneha's alerts: {len(sneha_alerts)}")
    print(f"  Urgent: {len(urgent)}")
    for alert in sneha_alerts[:5]:
        print(
            f"  {alert['title']}: {alert['days_remaining']:.1f} days "
            f"remaining ({alert['reorder_urgency']})"
        )


if __name__ == "__main__":
    main()
