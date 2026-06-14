"""Extract occasion missions from the simulated purchase history."""

import json
import random
from datetime import date, timedelta
from pathlib import Path


random.seed(42)

BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND_DIR / "app" / "data" / "simulated"
USERS_PATH = DATA_DIR / "users.json"
PURCHASES_PATH = DATA_DIR / "purchase_history.json"
OUTPUT_PATH = DATA_DIR / "occasion_history.json"
TODAY = date(2026, 6, 14)

OCCASION_LABELS = {
    "kids_birthday": [
        "Riya's Birthday", "Aryan's Birthday", "Zara's Birthday",
        "Dev's Birthday", "School Friends Party", "Family Birthday",
    ],
    "festival": ["Diwali Celebration", "Festival Celebration"],
    "diwali": ["Diwali Celebration"],
    "holi": ["Holi with Friends", "Family Holi"],
    "office_potluck": [
        "Team Lunch", "Office Potluck", "Department Party", "Farewell Lunch",
    ],
    "travel": ["Coorg Trek", "Weekend Trek"],
    "valentine_dinner": ["Valentine Dinner"],
    "kids_school_farewell": ["School Farewell Party"],
    "annaprasanam": ["Annaprasanam Ceremony"],
    "grihapravesh": ["New Home Blessing"],
    "office_farewell": ["Team Farewell"],
}

RECURRENCE_OCCASIONS = {
    "kids_birthday", "festival", "diwali", "holi",
    "valentine_dinner", "kids_school_farewell",
}


def next_recurrence(order_date: date) -> date:
    recurrence = order_date + timedelta(days=365)
    while recurrence <= TODAY:
        recurrence += timedelta(days=365)
    return recurrence


def main() -> None:
    with USERS_PATH.open(encoding="utf-8") as file:
        users = json.load(file)
    with PURCHASES_PATH.open(encoding="utf-8") as file:
        all_history = json.load(file)

    all_occasions = {}
    mission_counter = 1
    for user in users:
        uid = user["user_id"]
        occasions = []
        for order in all_history.get(uid, []):
            tag = order.get("occasion_tag", "routine_grocery")
            if tag == "routine_grocery":
                continue

            label = order.get("occasion_label") or random.choice(
                OCCASION_LABELS.get(tag, [tag.replace("_", " ").title()])
            )
            order_date = date.fromisoformat(order["date"])
            recurrence_date = None
            days_until_recurrence = None
            recurrence_alert = None
            if tag in RECURRENCE_OCCASIONS:
                recurrence = next_recurrence(order_date)
                recurrence_date = recurrence.isoformat()
                days_until_recurrence = (recurrence - TODAY).days
                if days_until_recurrence <= 30:
                    recurrence_alert = (
                        f"{label} in {days_until_recurrence} days "
                        "- rebuild last year's mission?"
                    )

            items_ordered = []
            for item in order.get("items", []):
                price_then = item.get("price", 0)
                price_now = round(price_then * random.uniform(0.85, 1.15))
                items_ordered.append(
                    {
                        "asin": item.get("asin", ""),
                        "title": item.get("title", ""),
                        "category": item.get("category", ""),
                        "quantity_packs": item.get("quantity", 1),
                        "price_then": price_then,
                        "price_now": price_now,
                        "price_change": price_now - price_then,
                        "still_available": random.random() > 0.05,
                    }
                )

            total = order.get("total", 0)
            outcome = random.choices([3, 4, 5], weights=[5, 35, 60])[0]
            note = {
                5: "Everything was perfect, will reorder the same items",
                4: "Mostly good, minor quantity issues",
                3: "Some items were missing or late",
            }[outcome]
            occasions.append(
                {
                    "mission_id": f"M{mission_counter:04d}",
                    "user_id": uid,
                    "occasion_type": tag,
                    "occasion_label": label,
                    "date": order["date"],
                    "headcount": order.get("headcount", 10),
                    "budget_used": total,
                    "budget_max": order.get("budget_max", round(total * 1.1)),
                    "coverage_score": random.choice(
                        ["7/8", "8/8", "9/9", "8/9", "9/10"]
                    ),
                    "outcome_rating": outcome,
                    "outcome_note": note,
                    "repeat_next_year": tag in RECURRENCE_OCCASIONS,
                    "items_ordered": items_ordered,
                    "days_until_recurrence": days_until_recurrence,
                    "recurrence_date": recurrence_date,
                    "recurrence_alert": recurrence_alert,
                }
            )
            mission_counter += 1
        all_occasions[uid] = occasions

    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(all_occasions, file, indent=2)

    total_occasions = sum(len(value) for value in all_occasions.values())
    users_with_occasions = sum(bool(value) for value in all_occasions.values())
    print("Occasion history generated:")
    print(f"  Total occasions: {total_occasions}")
    print(f"  Users with occasions: {users_with_occasions}")
    print(f"\nSneha's occasions: {len(all_occasions.get('U001', []))}")
    for occasion in all_occasions.get("U001", []):
        suffix = (
            f" -> {occasion['recurrence_alert']}"
            if occasion.get("recurrence_alert")
            else ""
        )
        print(
            f"  {occasion['date']}: {occasion['occasion_label']} "
            f"({occasion['outcome_rating']}/5){suffix}"
        )


if __name__ == "__main__":
    main()
