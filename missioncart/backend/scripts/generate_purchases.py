"""Generate realistic purchase histories for all simulated users."""

import calendar
import json
import random
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path


random.seed(42)

BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND_DIR / "app" / "data" / "simulated"
USERS_PATH = DATA_DIR / "users.json"
OUTPUT_PATH = DATA_DIR / "purchase_history.json"
TODAY = date(2026, 6, 14)

ROUTINE_PRODUCTS = [
    {
        "asin": "MC_SALT_001",
        "title": "Tata Salt 1kg",
        "category": "grocery_staples",
        "price": 21,
        "quantity": 2,
        "pack_size": 1,
        "now": True,
        "interval_days": 7,
        "variance": 2,
        "sneha_last": "2026-06-10",
    },
    {
        "asin": "MC_SURF_001",
        "title": "Surf Excel 1kg",
        "category": "detergent",
        "price": 189,
        "quantity": 1,
        "pack_size": 1,
        "now": True,
        "interval_days": 14,
        "variance": 3,
        "sneha_last": "2026-06-05",
    },
    {
        "asin": "MC_PARLEG_001",
        "title": "Parle-G 800g",
        "category": "biscuits",
        "price": 35,
        "quantity": 3,
        "pack_size": 1,
        "now": True,
        "interval_days": 7,
        "variance": 2,
        "sneha_last": "2026-06-08",
    },
    {
        "asin": "MC_MILK_001",
        "title": "Amul Milk 1L",
        "category": "dairy",
        "price": 28,
        "quantity": 6,
        "pack_size": 1,
        "now": True,
        "interval_days": 3,
        "variance": 1,
        "sneha_last": "2026-06-12",
    },
    {
        "asin": "MC_BREAD_001",
        "title": "Brown Bread",
        "category": "bakery",
        "price": 45,
        "quantity": 2,
        "pack_size": 1,
        "now": True,
        "interval_days": 5,
        "variance": 2,
        "sneha_last": "2026-06-11",
    },
    {
        "asin": "MC_DAL_001",
        "title": "Toor Dal 1kg",
        "category": "pulses",
        "price": 98,
        "quantity": 2,
        "pack_size": 1,
        "now": True,
        "interval_days": 14,
        "variance": 3,
        "sneha_last": "2026-06-06",
    },
    {
        "asin": "MC_RICE_001",
        "title": "Basmati Rice 5kg",
        "category": "rice",
        "price": 349,
        "quantity": 1,
        "pack_size": 5,
        "now": False,
        "interval_days": 30,
        "variance": 5,
        "sneha_last": "2026-05-30",
    },
    {
        "asin": "MC_OIL_001",
        "title": "Sunflower Oil 1L",
        "category": "cooking_oil",
        "price": 145,
        "quantity": 2,
        "pack_size": 1,
        "now": True,
        "interval_days": 21,
        "variance": 4,
        "sneha_last": "2026-06-02",
    },
    {
        "asin": "MC_ONION_001",
        "title": "Onions 1kg",
        "category": "vegetables",
        "price": 32,
        "quantity": 3,
        "pack_size": 1,
        "now": True,
        "interval_days": 14,
        "variance": 3,
        "sneha_last": "2026-06-07",
    },
    {
        "asin": "MC_ARIEL_001",
        "title": "Ariel Detergent 2kg",
        "category": "laundry",
        "price": 399,
        "quantity": 1,
        "pack_size": 2,
        "now": True,
        "interval_days": 30,
        "variance": 5,
        "sneha_last": "2026-05-25",
    },
    {
        "asin": "MC_COLGATE_001",
        "title": "Colgate Toothpaste 150g",
        "category": "oral_care",
        "price": 89,
        "quantity": 2,
        "pack_size": 1,
        "now": True,
        "interval_days": 45,
        "variance": 7,
        "sneha_last": "2026-05-12",
    },
    {
        "asin": "MC_DETTOL_001",
        "title": "Dettol Soap",
        "category": "personal_care",
        "price": 45,
        "quantity": 4,
        "pack_size": 1,
        "now": True,
        "interval_days": 60,
        "variance": 10,
        "sneha_last": "2026-04-30",
    },
    {
        "asin": "MC_SHAMPOO_001",
        "title": "Head & Shoulders Shampoo 400ml",
        "category": "hair_care",
        "price": 299,
        "quantity": 1,
        "pack_size": 1,
        "now": True,
        "interval_days": 45,
        "variance": 7,
        "sneha_last": "2026-05-20",
    },
]

OCCASION_ITEMS = {
    "kids_birthday": [
        ("MC_PLATES_001", "Disposable Paper Plates 25pc", "plates", 89),
        ("MC_CUPS_001", "Disposable Cups 50pc", "cups", 79),
        ("MC_BALLOONS_001", "Multicolor Balloons 30pc", "balloon_set", 149),
        ("MC_PUMP_001", "Hand Balloon Pump", "balloon_pump", 149),
        ("MC_CANDLES_001", "Birthday Candles", "candles", 49),
    ],
    "festival": [
        ("MC_DIYA_001", "Earthen Diyas Pack of 50", "festival_lights", 149),
        ("MC_FAIRY_001", "Fairy Lights 10m", "festival_lights", 299),
        ("MC_RANGOLI_001", "Rangoli Colors Set", "decoration", 199),
        ("MC_INCENSE_001", "Agarbatti Set", "pooja_items", 89),
    ],
    "holi": [
        ("MC_COLORS_001", "Holi Colors Set", "holi_supplies", 299),
        ("MC_PICHKARI_001", "Water Gun Set", "holi_supplies", 199),
        ("MC_SWEETS_001", "Festival Sweets Box", "sweets", 449),
    ],
    "office_potluck": [
        ("MC_PLATES_001", "Disposable Paper Plates 25pc", "plates", 89),
        ("MC_CUPS_001", "Disposable Cups 50pc", "cups", 79),
        ("MC_NAPKINS_001", "Paper Napkins 100pc", "napkins", 59),
        ("MC_SNACKS_001", "Assorted Snacks", "snacks", 299),
    ],
    "travel": [
        ("MC_BACKPACK_001", "Trekking Backpack", "backpack", 1499),
        ("MC_BOTTLE_001", "Insulated Water Bottle", "water_bottle", 499),
        ("MC_FIRSTAID_001", "Travel First Aid Kit", "first_aid", 599),
    ],
}

SNEHA_OCCASIONS = [
    ("2026-01-14", "festival", "Pongal celebration supplies", 1847, 10),
    ("2026-02-14", "valentine_dinner", "Valentine dinner supplies", 892, 2),
    ("2026-03-08", "holi", "Holi celebration supplies", 1203, 12),
    ("2026-04-14", "office_potluck", "Office team potluck", 743, 18),
    ("2026-05-12", "kids_birthday", "Mom birthday party", 3847, 12),
    ("2026-06-01", "kids_school_farewell", "Kids school farewell party", 2103, 24),
]


def month_starts(start: date, end: date):
    current = start.replace(day=1)
    while current <= end:
        yield current
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)


def selected_products(user: dict) -> list[dict]:
    uid = user["user_id"]
    if uid == "U001":
        return ROUTINE_PRODUCTS
    if uid == "U002":
        return [
            ROUTINE_PRODUCTS[index]
            for index in [0, 1, 4, 5, 6, 7, 9, 10]
        ]
    if uid == "U003":
        return [
            ROUTINE_PRODUCTS[index]
            for index in [2, 4, 6, 10, 12]
        ]

    probability = min(0.82, 0.42 + user["household_size"] * 0.06)
    chosen = [
        product for product in ROUTINE_PRODUCTS
        if random.random() <= probability
    ]
    if len(chosen) < 5:
        remaining = [product for product in ROUTINE_PRODUCTS if product not in chosen]
        chosen.extend(random.sample(remaining, 5 - len(chosen)))
    return chosen


def routine_order(user: dict, product: dict, purchase_date: date) -> dict:
    is_sneha = user["user_id"] == "U001"
    quantity = product["quantity"] if is_sneha else max(
        1,
        round(product["quantity"] * random.uniform(0.65, 1.25)),
    )
    price = product["price"] if is_sneha else round(
        product["price"] * random.uniform(0.92, 1.08)
    )
    item = {
        "asin": product["asin"],
        "title": product["title"],
        "category": product["category"],
        "price": price,
        "quantity": quantity,
        "pack_size": product["pack_size"],
        "amazon_now_eligible": product["now"],
    }
    return {
        "user_id": user["user_id"],
        "date": purchase_date.isoformat(),
        "items": [item],
        "total": price * quantity,
        "delivery_type": "amazon_now" if product["now"] else "standard",
        "occasion_tag": "routine_grocery",
    }


def generate_routine_orders(
    user: dict, products: list[dict], start: date, end: date
) -> list[dict]:
    orders = []
    for product in products:
        if user["user_id"] == "U001":
            current = date.fromisoformat(product["sneha_last"])
            dates = []
            while current >= start:
                dates.append(current)
                interval = product["interval_days"] + random.randint(
                    -product["variance"], product["variance"]
                )
                current -= timedelta(days=max(1, interval))
            dates.reverse()
        else:
            current = start + timedelta(
                days=random.randint(0, product["interval_days"])
            )
            dates = []
            while current <= end:
                dates.append(current)
                interval = product["interval_days"] + random.randint(
                    -product["variance"], product["variance"]
                )
                current += timedelta(days=max(1, interval))

        orders.extend(routine_order(user, product, day) for day in dates)
    return orders


def build_occasion_order(
    user_id: str,
    occasion_date: date,
    tag: str,
    label: str,
    budget_total: int,
    headcount: int,
    exact_total: bool = False,
) -> dict:
    templates = OCCASION_ITEMS.get(tag, OCCASION_ITEMS["office_potluck"])
    items = []
    running_total = 0
    for asin, title, category, base_price in templates:
        quantity = 1
        if category in {"plates", "cups"}:
            quantity = max(1, (headcount + 14) // 15)
        elif category in {"balloon_set", "holi_supplies"}:
            quantity = max(1, (headcount + 7) // 8)
        price = round(base_price * random.uniform(0.95, 1.05))
        running_total += price * quantity
        items.append(
            {
                "asin": asin,
                "title": title,
                "category": category,
                "price": price,
                "quantity": quantity,
                "pack_size": 1,
                "amazon_now_eligible": True,
            }
        )

    if exact_total and running_total > budget_total:
        reduction = running_total - budget_total
        last_item = items[-1]
        if last_item["quantity"] == 1 and last_item["price"] > reduction:
            last_item["price"] -= reduction
            running_total = budget_total

    if running_total < budget_total:
        items.append(
            {
                "asin": f"MC_{tag.upper()}_EXTRAS",
                "title": label,
                "category": "occasion_extras",
                "price": budget_total - running_total,
                "quantity": 1,
                "pack_size": 1,
                "amazon_now_eligible": True,
            }
        )
    total = sum(item["price"] * item["quantity"] for item in items)
    return {
        "user_id": user_id,
        "date": occasion_date.isoformat(),
        "items": items,
        "total": total,
        "delivery_type": "amazon_now",
        "occasion_tag": tag,
        "occasion_label": label,
        "headcount": headcount,
        "budget_max": max(budget_total, round(budget_total * 1.1)),
    }


def generate_occasion_orders(user: dict, start: date, end: date) -> list[dict]:
    uid = user["user_id"]
    if uid == "U001":
        orders = [
            build_occasion_order(
                uid,
                date.fromisoformat(day),
                tag,
                label,
                total,
                headcount,
                exact_total=True,
            )
            for day, tag, label, total, headcount in SNEHA_OCCASIONS
        ]
        orders.append(
            build_occasion_order(
                uid,
                date(2025, 10, 20),
                "festival",
                "Diwali 2025",
                4203,
                8,
                exact_total=True,
            )
        )
        return [order for order in orders if start <= date.fromisoformat(order["date"]) <= end]

    if uid == "U002":
        fixed = build_occasion_order(
            uid,
            date(2025, 12, 26),
            "travel",
            "Coorg Trek",
            4891,
            4,
        )
        orders = [fixed] if start <= date(2025, 12, 26) <= end else []
    else:
        orders = []

    for month in month_starts(start, end):
        candidates = []
        if month.month == 3:
            candidates.append(("holi", 0.92, (700, 2000), (5, 15)))
        if month.month == 10:
            candidates.append(("festival", 0.9, (3000, 8000), (5, 15)))
        candidates.extend(
            [
                ("kids_birthday", 0.12, (2500, 6000), (8, 20)),
                ("office_potluck", 0.07, (500, 2000), (10, 25)),
            ]
        )
        for tag, probability, budget_range, headcount_range in candidates:
            if random.random() > probability:
                continue
            max_day = calendar.monthrange(month.year, month.month)[1]
            occasion_date = month.replace(day=random.randint(1, max_day))
            if not start <= occasion_date <= end:
                continue
            budget = random.randint(*budget_range)
            headcount = random.randint(*headcount_range)
            orders.append(
                build_occasion_order(
                    uid,
                    occasion_date,
                    tag,
                    tag.replace("_", " ").title(),
                    budget,
                    headcount,
                )
            )

    if not orders:
        fallback_date = min(end, start + timedelta(days=45))
        orders.append(
            build_occasion_order(
                uid,
                fallback_date,
                "office_potluck",
                "Team Lunch",
                1200,
                12,
            )
        )
    return orders


def add_order_ids_and_intervals(user_id: str, orders: list[dict]) -> list[dict]:
    orders.sort(key=lambda order: (order["date"], order["occasion_tag"]))
    previous_by_category: dict[str, date] = {}
    intervals_by_category: dict[str, list[int]] = defaultdict(list)

    for index, order in enumerate(orders, start=1):
        order["order_id"] = f"ORD_{user_id}_{index:04d}"
        current_date = date.fromisoformat(order["date"])
        for item in order["items"]:
            category = item["category"]
            previous = previous_by_category.get(category)
            if previous is None:
                item["days_since_last_purchase"] = None
                item["average_interval_days"] = None
            else:
                interval = (current_date - previous).days
                intervals_by_category[category].append(interval)
                item["days_since_last_purchase"] = interval
                item["average_interval_days"] = round(
                    sum(intervals_by_category[category])
                    / len(intervals_by_category[category]),
                    1,
                )
            previous_by_category[category] = current_date
    return orders


def main() -> None:
    with USERS_PATH.open(encoding="utf-8") as file:
        users = json.load(file)

    all_history = {}
    print("Generating purchase history...")
    for user in users:
        uid = user["user_id"]
        numeric_id = int(uid[1:])
        if uid == "U001":
            months = 12
            start = date(2025, 6, 14)
        elif numeric_id <= 10:
            months = 6
            start = date(2025, 12, 14)
        else:
            months = 3
            start = date(2026, 3, 14)

        end = min(TODAY, start + timedelta(days=months * 30))
        orders = generate_routine_orders(
            user, selected_products(user), start, end
        )
        orders.extend(generate_occasion_orders(user, start, end))
        all_history[uid] = add_order_ids_and_intervals(uid, orders)
        print(f"  {uid} ({user['name']}): {len(all_history[uid])} orders")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(all_history, file, indent=2)

    print(f"\nTotal orders generated: {sum(map(len, all_history.values()))}")
    print(f"Users with history: {len(all_history)}")


if __name__ == "__main__":
    main()
