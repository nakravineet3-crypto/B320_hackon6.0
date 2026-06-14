"""Generate 90-day price histories for every catalog product."""

import json
import random
from datetime import date, timedelta
from pathlib import Path


random.seed(42)

BACKEND_DIR = Path(__file__).resolve().parents[1]
CATALOG_PATH = BACKEND_DIR / "app" / "data" / "catalog.json"
OUTPUT_PATH = BACKEND_DIR / "app" / "data" / "simulated" / "price_history.json"
TODAY = date(2026, 6, 14)
DAY_OFFSETS = [90, 75, 60, 45, 30, 21, 14, 7, 3, 0]

TREND_TYPES = ["stable", "falling", "rising", "volatile", "sale_ended"]
TREND_WEIGHTS = [40, 25, 20, 10, 5]
MEANINGFUL_DROP_CATEGORIES = {
    "plates", "balloon_pump", "decoration_streamers", "return_gifts"
}


def trend_price(
    base_price: float,
    trend: str,
    progress: float,
    meaningful_drop: bool,
) -> float:
    if progress == 1:
        return base_price
    if trend == "stable":
        return base_price * random.uniform(0.97, 1.03)
    if trend == "falling":
        start_multiplier = (
            random.uniform(1.25, 1.38)
            if meaningful_drop
            else random.uniform(1.08, 1.18)
        )
        return (
            base_price
            * (start_multiplier - (start_multiplier - 1) * progress)
            * random.uniform(0.985, 1.015)
        )
    if trend == "rising":
        start_multiplier = random.uniform(0.80, 0.90)
        return (
            base_price
            * (start_multiplier + (1 - start_multiplier) * progress)
            * random.uniform(0.985, 1.015)
        )
    if trend == "volatile":
        return base_price * random.uniform(0.80, 1.20)
    if progress < 0.60:
        return base_price * 0.70
    return base_price * random.uniform(0.98, 1.02)


def main() -> None:
    with CATALOG_PATH.open(encoding="utf-8") as file:
        catalog = json.load(file)

    forced_drop_asins = set()
    for category in MEANINGFUL_DROP_CATEGORIES:
        product = next(
            (item for item in catalog if item.get("category") == category),
            None,
        )
        if product:
            forced_drop_asins.add(product["asin"])

    price_history = {}
    for product in catalog:
        asin = product.get("asin")
        if not asin:
            continue
        base_price = float(product.get("price", 100))
        meaningful_drop = asin in forced_drop_asins
        trend = (
            "falling"
            if meaningful_drop
            else random.choices(TREND_TYPES, weights=TREND_WEIGHTS)[0]
        )

        history = []
        for index, days_back in enumerate(DAY_OFFSETS):
            progress = index / (len(DAY_OFFSETS) - 1)
            price = round(
                trend_price(base_price, trend, progress, meaningful_drop)
            )
            history.append(
                {
                    "date": (TODAY - timedelta(days=days_back)).isoformat(),
                    "price": price,
                }
            )

        prices = [entry["price"] for entry in history]
        recent_prices = [
            entry["price"]
            for entry in history
            if (TODAY - date.fromisoformat(entry["date"])).days <= 30
        ]
        current = prices[-1]
        lowest = min(prices)
        highest = max(prices)
        lowest_30d = min(recent_prices)
        highest_30d = max(recent_prices)
        at_lowest = current <= lowest * 1.02
        at_highest = current >= highest * 0.98

        price_alert = None
        if meaningful_drop:
            price_alert = (
                f"\u20b9{highest - current:.0f} cheaper than 3 months ago "
                "- good time to buy"
            )
        elif trend == "rising" and current - lowest >= 10:
            price_alert = (
                f"\u20b9{current - lowest:.0f} cheaper "
                f"{random.randint(30, 60)} days ago"
            )
        elif trend == "sale_ended":
            sale_price = round(base_price * 0.70)
            price_alert = (
                f"Was on sale at \u20b9{sale_price:.0f} - sale has ended"
            )

        price_history[asin] = {
            "asin": asin,
            "title": product.get("title", ""),
            "category": product.get("category", ""),
            "current_price": current,
            "base_price": product.get("price", base_price),
            "history": history,
            "lowest_90d": lowest,
            "highest_90d": highest,
            "lowest_30d": lowest_30d,
            "highest_30d": highest_30d,
            "avg_30d": round(sum(recent_prices) / len(recent_prices), 1),
            "avg_90d": round(sum(prices) / len(prices), 1),
            "price_trend": trend,
            "at_lowest": at_lowest,
            "at_highest": at_highest,
            "price_alert": price_alert,
            "volatility": round((highest - lowest) / base_price * 100, 1),
        }

    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(price_history, file, indent=2)

    falling = sum(
        item["price_trend"] == "falling" for item in price_history.values()
    )
    rising = sum(
        item["price_trend"] == "rising" for item in price_history.values()
    )
    alerts = sum(bool(item.get("price_alert")) for item in price_history.values())
    print(f"Price history generated for {len(price_history)} products")
    print(f"  Falling: {falling}")
    print(f"  Rising: {rising}")
    print(f"  Meaningful demo drops: {len(forced_drop_asins)}")
    print(f"  With price alert: {alerts}")


if __name__ == "__main__":
    main()
