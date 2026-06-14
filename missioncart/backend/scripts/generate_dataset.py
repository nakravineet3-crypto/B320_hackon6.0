"""Generate the MissionCart community evidence session dataset."""

import json
import random
from datetime import date, timedelta
from pathlib import Path


random.seed(42)

BACKEND_DIR = Path(__file__).resolve().parents[1]
CATALOG_PATH = BACKEND_DIR / "app" / "data" / "catalog.json"
OUTPUT_PATH = (
    BACKEND_DIR / "app" / "data" / "simulated" / "community_sessions.json"
)

CITIES = [
    "Bangalore", "Mumbai", "Delhi", "Chennai", "Hyderabad", "Pune",
    "Kolkata", "Ahmedabad", "Jaipur", "Lucknow", "Kochi", "Indore",
]
SOUTH_CITIES = ["Chennai", "Hyderabad", "Kochi", "Bangalore"]
AGE_BRACKETS = ["18-22", "22-28", "28-35", "35-45", "45-55", "55+"]
DEVICES = ["android", "ios", "web"]
START_DATE = date(2024, 1, 1)
END_DATE = date(2026, 6, 14)

SESSION_COUNTS = {
    "kids_birthday": 800,
    "home_setup": 480,
    "travel_prep": 320,
    "festival": 240,
    "office_event": 160,
    "annaprasanam": 120,
    "grihapravesh": 80,
    "office_farewell": 40,
}

CATEGORY_ALIASES = {
    "first_aid": "first_aid_kit",
    "flowers": "decorations",
    "pooja_items": "scented_candle",
    "festival_lights": "led_bulb",
    "sweets": "chocolates",
    "incense": "scented_candle",
    "cake": "chocolates",
    "diyas": "scented_candle",
    "decoration": "decorations",
    "banana_leaf": "plates",
}


def load_asins_by_category() -> dict[str, str]:
    with CATALOG_PATH.open(encoding="utf-8") as file:
        catalog = json.load(file)
    mapping = {}
    for product in catalog:
        category = product.get("category")
        asin = product.get("asin")
        if category and asin and category not in mapping:
            mapping[category] = asin
    return mapping


def random_date() -> str:
    span = (END_DATE - START_DATE).days
    return (START_DATE + timedelta(days=random.randint(0, span))).isoformat()


def item(
    category: str,
    quantity: int,
    asins_by_category: dict[str, str],
) -> dict:
    catalog_category = CATEGORY_ALIASES.get(category, category)
    asin = asins_by_category.get(
        catalog_category, f"MC_{category.upper()}_001"
    )
    return {"category": category, "asin": asin, "quantity": quantity}


def kids_birthday(
    headcount: int, asins_by_category: dict[str, str]
) -> list[dict]:
    items = [
        item("plates", max(1, (headcount * 2 + 24) // 25), asins_by_category),
        item("cups", max(1, (headcount * 2 + 49) // 50), asins_by_category),
        item("candles", 1, asins_by_category),
    ]
    has_balloons = random.random() < 0.87
    if has_balloons:
        items.append(
            item(
                "balloon_set",
                max(1, (headcount * 3 + 29) // 30),
                asins_by_category,
            )
        )
        if random.random() < 0.83:
            items.append(item("balloon_pump", 1, asins_by_category))
    if random.random() < 0.71:
        items.append(
            item("return_gifts", max(1, (headcount + 11) // 12), asins_by_category)
        )
    return items


def home_setup(
    headcount: int, asins_by_category: dict[str, str]
) -> list[dict]:
    items = [
        item("mattress", max(1, headcount), asins_by_category),
        item("bedsheet", max(1, headcount + 1), asins_by_category),
    ]
    has_cooktop = random.random() < 0.88
    if has_cooktop:
        items.append(item("induction_cooktop", 1, asins_by_category))
        if random.random() < 0.84:
            items.append(
                item("induction_compatible_vessel", 1, asins_by_category)
            )
    if random.random() < 0.76:
        items.append(item("water_purifier", 1, asins_by_category))
    return items


def travel_prep(
    headcount: int, asins_by_category: dict[str, str]
) -> list[dict]:
    items = []
    if random.random() < 0.93:
        items.append(item("water_bottle", headcount, asins_by_category))
    if random.random() < 0.81:
        items.append(item("first_aid", 1, asins_by_category))
    if random.random() < 0.89:
        items.append(item("backpack", max(1, headcount - 1), asins_by_category))
    if not items:
        items.append(item("backpack", 1, asins_by_category))
    return items


def fixed_items(
    categories: list[str],
    headcount: int,
    asins_by_category: dict[str, str],
) -> list[dict]:
    items = []
    for category in categories:
        if category in {"plates", "cups", "napkins"}:
            quantity = max(1, (headcount + 24) // 25)
        elif category in {"return_gifts", "sweets"}:
            quantity = max(1, (headcount + 11) // 12)
        else:
            quantity = random.randint(1, 3)
        items.append(item(category, quantity, asins_by_category))
    return items


def session_shape(occasion_type: str) -> tuple[int, int, list[str] | None]:
    if occasion_type == "kids_birthday":
        return random.randint(8, 25), random.randint(2500, 6000), None
    if occasion_type == "home_setup":
        return random.randint(1, 3), random.randint(8000, 20000), None
    if occasion_type == "travel_prep":
        return random.randint(2, 6), random.randint(2000, 8000), None
    if occasion_type == "festival":
        return (
            random.randint(4, 15),
            random.randint(2000, 6000),
            ["festival_lights", "sweets", "decoration", "incense"],
        )
    if occasion_type == "office_event":
        return (
            random.randint(10, 30),
            random.randint(1000, 3000),
            ["plates", "cups", "napkins", "snacks"],
        )
    if occasion_type == "annaprasanam":
        return (
            random.randint(20, 60),
            random.randint(5000, 15000),
            ["banana_leaf", "sweets", "pooja_items", "flowers"],
        )
    if occasion_type == "grihapravesh":
        return (
            random.randint(15, 40),
            random.randint(8000, 20000),
            [
                "pooja_items", "sweets", "flowers", "diyas",
                "decorations", "return_gifts",
            ],
        )
    return (
        random.randint(10, 30),
        random.randint(1000, 4000),
        ["cake", "plates", "cups", "decoration"],
    )


def build_session(
    session_id: int,
    occasion_type: str,
    asins_by_category: dict[str, str],
) -> dict:
    headcount, budget, categories = session_shape(occasion_type)
    if occasion_type == "kids_birthday":
        purchased = kids_birthday(headcount, asins_by_category)
    elif occasion_type == "home_setup":
        purchased = home_setup(headcount, asins_by_category)
    elif occasion_type == "travel_prep":
        purchased = travel_prep(headcount, asins_by_category)
    else:
        purchased = fixed_items(categories or [], headcount, asins_by_category)

    city_pool = SOUTH_CITIES if occasion_type == "annaprasanam" else CITIES
    prime = random.random() < 0.65
    return {
        "session_id": f"S{session_id:04d}",
        "occasion_type": occasion_type,
        "city": random.choice(city_pool),
        "user_age_bracket": random.choice(AGE_BRACKETS),
        "amazon_prime": prime,
        "headcount": headcount,
        "budget_max": budget,
        "date": random_date(),
        "items_purchased": purchased,
        "total_spent": round(budget * random.uniform(0.62, 0.96)),
        "completed_mission": random.random() < 0.95,
        "outcome_rating": random.choices([3, 4, 5], weights=[8, 37, 55])[0],
        "repeat_purchase": random.random() < 0.30,
        "platform": (
            "amazon_now" if prime or random.random() < 0.55
            else "amazon_standard"
        ),
        "device": random.choices(DEVICES, weights=[58, 27, 15])[0],
        "time_to_checkout_minutes": random.randint(2, 15),
        "session_size": len(purchased),
    }


def main() -> None:
    asins_by_category = load_asins_by_category()
    sessions = []
    session_id = 1
    for occasion_type, count in SESSION_COUNTS.items():
        for _ in range(count):
            sessions.append(
                build_session(session_id, occasion_type, asins_by_category)
            )
            session_id += 1

    random.shuffle(sessions)
    payload = {
        "metadata": {
            "total_sessions": len(sessions),
            "date_range": "2024-01-01 to 2026-06-14",
            "occasion_types": list(SESSION_COUNTS),
            "occasions_covered": len(SESSION_COUNTS),
            "cities": CITIES,
            "cities_covered": len(CITIES),
            "session_counts": SESSION_COUNTS,
        },
        "sessions": sessions,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)

    print(f"Generated {len(sessions)} community sessions")
    for occasion_type, count in SESSION_COUNTS.items():
        print(f"  {occasion_type}: {count}")


if __name__ == "__main__":
    main()
