"""
regenerate_simulation.py
------------------------
Regenerates purchase_history.json and user_cluster_map.json with realistic,
differentiable purchase patterns for 4 identity groups:

  office_gym_dad  U001-U013  fitness + daily essentials
  jee_student     U014-U026  stationery + snacks + study
  college_girl    U027-U039  personal care + snacks + fashion
  home_chef       U040-U050  grocery + spices + kitchen

All ASINs used are verified to exist in catalog.json.
U001 (Sneha) demo anchor ASINs are injected explicitly.
"""

import json
import random
import math
from datetime import date, timedelta
from collections import defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE = Path("D:/Projects/B320_hackon6.0/missioncart/backend/app/data")
CATALOG_PATH = BASE / "catalog.json"
PURCHASE_HISTORY_PATH = BASE / "simulated" / "purchase_history.json"
USER_CLUSTER_MAP_PATH = BASE / "user_cluster_map.json"
COMMUNITY_GROUPS_PATH = BASE / "community_groups.json"
NORM_PARAMS_PATH = BASE / "identity_normalization_params.json"

random.seed(42)

TODAY = date(2026, 6, 24)
YEAR_AGO = TODAY - timedelta(days=365)

# ---------------------------------------------------------------------------
# Load catalog — build lookup tables
# ---------------------------------------------------------------------------
with open(CATALOG_PATH, encoding="utf-8") as f:
    catalog_raw = json.load(f)

# Map asin -> product record
catalog_map = {p["asin"]: p for p in catalog_raw}

# Map category -> list of ASINs
cat_to_asins: dict[str, list[str]] = defaultdict(list)
for p in catalog_raw:
    cat_to_asins[p["category"]].append(p["asin"])

print(f"Catalog loaded: {len(catalog_raw)} products, {len(cat_to_asins)} categories")

# ---------------------------------------------------------------------------
# ASIN selection helpers
# ---------------------------------------------------------------------------

def asins_for_categories(*categories: str) -> list[str]:
    """Return all ASINs from the given categories."""
    result = []
    for cat in categories:
        result.extend(cat_to_asins.get(cat, []))
    return result


def pick_asin(pool: list[str]) -> str:
    """Pick a random ASIN from pool; crash loudly if pool is empty."""
    if not pool:
        raise ValueError("Empty ASIN pool — check category names against catalog")
    return random.choice(pool)


# ---------------------------------------------------------------------------
# Per-group ASIN pools mapped to weight buckets
# Each bucket: (weight_fraction, [asin_list])
# ---------------------------------------------------------------------------

GROCERY_POOL = asins_for_categories("food_beverages", "dairy", "atta", "dal", "rice", "cooking_oil", "sugar", "tea")
SNACK_POOL = asins_for_categories("chips", "namkeen", "biscuits", "chocolates", "instant_noodles", "juice", "soda")
PERSONAL_CARE_POOL = asins_for_categories("shampoo", "soap", "toothpaste", "baby_soap")
STATIONERY_POOL = asins_for_categories("pens", "notebooks", "markers", "sticky_notes", "folders", "desk_organizer")
KITCHEN_POOL = asins_for_categories(
    "induction_compatible_vessel", "induction_cooktop", "chopping_board",
    "kitchen_knife", "aluminium_foil", "cling_wrap", "dishwash"
)
FITNESS_OUTDOOR_POOL = asins_for_categories(
    "energy_bar", "torch", "backpack", "water_bottle",
    "trekking_socks", "packing_cubes", "first_aid_kit", "rain_jacket"
)
ELECTRONICS_POOL = asins_for_categories(
    "usb_c_hub", "hdmi_cable", "keyboard", "mouse", "laptop_stand",
    "phone_stand", "power_bank", "webcam", "cable_organizer", "extension_board"
)
CLOTHING_POOL = asins_for_categories("towels", "hangers", "pillow_covers")
PARTY_POOL = asins_for_categories("party_supplies", "balloon_set", "decoration_streamers", "candles", "decorations")
HOME_POOL = asins_for_categories("storage_box", "led_bulb", "bathroom_organizer", "bedsheet", "curtains")
BEAUTY_CARE_POOL = asins_for_categories("shampoo", "soap", "toothpaste") + asins_for_categories("baby_oil")  # beauty proxy
SPICE_ADJACENT_POOL = asins_for_categories("tea", "cooking_oil", "dal", "atta", "dishwash")

# Verify no empty pools
for name, pool in [
    ("GROCERY", GROCERY_POOL), ("SNACK", SNACK_POOL), ("PERSONAL_CARE", PERSONAL_CARE_POOL),
    ("STATIONERY", STATIONERY_POOL), ("KITCHEN", KITCHEN_POOL), ("FITNESS_OUTDOOR", FITNESS_OUTDOOR_POOL),
    ("ELECTRONICS", ELECTRONICS_POOL), ("PARTY", PARTY_POOL), ("HOME", HOME_POOL),
]:
    if not pool:
        print(f"  WARNING: {name}_POOL is empty")
    else:
        print(f"  {name}_POOL: {len(pool)} ASINs")

# ---------------------------------------------------------------------------
# Identity group definitions
# Each group: list of (weight, asin_pool) tuples
# ---------------------------------------------------------------------------

GROUP_PROFILES = {
    "office_gym_dad": [
        (0.25, FITNESS_OUTDOOR_POOL),
        (0.20, GROCERY_POOL),
        (0.15, PERSONAL_CARE_POOL),
        (0.15, ELECTRONICS_POOL),
        (0.15, KITCHEN_POOL),
        (0.10, SNACK_POOL),
    ],
    "jee_student": [
        (0.30, STATIONERY_POOL),
        (0.25, SNACK_POOL),
        (0.20, PERSONAL_CARE_POOL),
        (0.15, GROCERY_POOL),
        (0.10, ELECTRONICS_POOL),
    ],
    "college_girl": [
        (0.35, BEAUTY_CARE_POOL),
        (0.20, SNACK_POOL),
        (0.15, GROCERY_POOL),
        (0.15, CLOTHING_POOL),
        (0.15, STATIONERY_POOL),
    ],
    "home_chef": [
        (0.35, GROCERY_POOL),
        (0.20, SPICE_ADJACENT_POOL),
        (0.20, KITCHEN_POOL),
        (0.15, GROCERY_POOL),   # extra dairy/staple weight
        (0.10, HOME_POOL),
    ],
}

# Normalize weights in case they don't sum to exactly 1.0
for group, buckets in GROUP_PROFILES.items():
    total = sum(w for w, _ in buckets)
    GROUP_PROFILES[group] = [(w / total, pool) for w, pool in buckets]

# ---------------------------------------------------------------------------
# User → group assignment
# ---------------------------------------------------------------------------

USER_GROUPS = {}
for uid in range(1, 14):    # U001-U013 office_gym_dad
    USER_GROUPS[f"U{uid:03d}"] = "office_gym_dad"
for uid in range(14, 27):   # U014-U026 jee_student
    USER_GROUPS[f"U{uid:03d}"] = "jee_student"
for uid in range(27, 40):   # U027-U039 college_girl
    USER_GROUPS[f"U{uid:03d}"] = "college_girl"
for uid in range(40, 51):   # U040-U050 home_chef
    USER_GROUPS[f"U{uid:03d}"] = "home_chef"

# ---------------------------------------------------------------------------
# U001 demo anchor data — these orders MUST appear in purchase_history
# ASINs: Ariel (detergent), Head & Shoulders (shampoo), Pedigree (adult_dog_food)
# Plus demo spec birthday ASINs from party_supplies
# ---------------------------------------------------------------------------

DEMO_USER = "U001"

# Demo reorder anchor ASINs — must appear in U001 recent history
DEMO_REORDER_ASINS = {
    "B07BFMWZF2": ("detergent", "Ariel Matic Powder 2kg", 399),
    "B00CPFSO6K": ("shampoo", "Head & Shoulders Shampoo 400ml", 449),
    "B00PNS7HM0": ("adult_dog_food", "Pedigree Adult Chicken & Vegetables 3kg", 599),
}

# Demo birthday party ASINs (from party_supplies category in catalog)
DEMO_BIRTHDAY_ASINS = {
    "B001PLATES": ("party_supplies", "Disposable Paper Plates 24-Pack", 149),
    "B002BALLOONS": ("party_supplies", "Birthday Balloon Set 50-Pack with Ribbon", 199),
    "B003STREAMERS": ("party_supplies", "Paper Streamers 12-Roll Set", 129),
}

# Verify all demo ASINs are in catalog
for asin in list(DEMO_REORDER_ASINS.keys()) + list(DEMO_BIRTHDAY_ASINS.keys()):
    if asin not in catalog_map:
        print(f"  FATAL: Demo ASIN {asin} not in catalog.json — aborting")
        raise SystemExit(1)

print("\nAll demo ASINs verified in catalog.json")

# ---------------------------------------------------------------------------
# Order generation helpers
# ---------------------------------------------------------------------------

def poisson_capped(lam: float = 1.2, cap: int = 3) -> int:
    """Poisson(lam) capped at cap."""
    import random
    p = math.exp(-lam)
    k = 0
    while True:
        p *= random.random()
        if p < math.exp(-lam):
            return min(k, cap)
        k += 1
    # Fallback
    return min(int(random.expovariate(1.0 / lam)), cap)


def clamp_qty(lam: float = 1.2) -> int:
    """Simple quantity: 1-3 using Poisson approximation."""
    u = random.random()
    if u < 0.55:
        return 1
    elif u < 0.85:
        return 2
    return 3


def random_date_in_range(start: date, end: date) -> str:
    delta = (end - start).days
    return (start + timedelta(days=random.randint(0, delta))).isoformat()


def pick_occasion(group: str) -> str:
    """70% routine, 30% occasion from group-specific set."""
    if random.random() < 0.70:
        return "routine"
    occasions = {
        "office_gym_dad": ["kids_birthday", "diwali_celebration", "holi_celebration"],
        "jee_student": ["diwali_celebration", "holi_celebration", "kids_birthday"],
        "college_girl": ["kids_birthday", "holi_celebration", "diwali_celebration"],
        "home_chef": ["diwali_celebration", "kids_birthday", "holi_celebration"],
    }
    return random.choice(occasions.get(group, ["diwali_celebration"]))


def pick_asin_for_group(group: str) -> str:
    """Select an ASIN based on the group's weighted bucket distribution."""
    buckets = GROUP_PROFILES[group]
    roll = random.random()
    cumulative = 0.0
    for weight, pool in buckets:
        cumulative += weight
        if roll <= cumulative:
            if pool:
                return random.choice(pool)
    # Fallback: pick from last non-empty bucket
    for _, pool in reversed(buckets):
        if pool:
            return random.choice(pool)
    raise ValueError(f"No ASIN found for group {group}")


def build_order(user_id: str, group: str, order_num: int, order_date: str,
                asin: str, occasion: str) -> dict:
    """Build a single order record matching the existing purchase_history schema."""
    product = catalog_map[asin]
    qty = clamp_qty()
    price = product["price"]
    total = round(price * qty, 2)
    amazon_now = product.get("amazon_now_eligible", True)
    delivery_type = "amazon_now" if amazon_now else "standard"

    return {
        "user_id": user_id,
        "date": order_date,
        "items": [
            {
                "asin": asin,
                "title": product["title"],
                "category": product["category"],
                "price": price,
                "quantity": qty,
                "pack_size": product.get("pack_size", 1),
                "amazon_now_eligible": amazon_now,
                "days_since_last_purchase": None,
                "average_interval_days": None,
            }
        ],
        "total": total,
        "delivery_type": delivery_type,
        "occasion_tag": occasion,
        "order_id": f"ORD_{user_id}_{order_num:04d}",
    }


# ---------------------------------------------------------------------------
# Generate reorder anchor orders for U001
# 3 occurrences each within last 90 days, spaced to simulate depletion
# ---------------------------------------------------------------------------

def generate_reorder_anchor_orders(user_id: str, group: str, seq_start: int) -> list[dict]:
    """Inject reorder anchor ASINs (Ariel, Head & Shoulders, Pedigree) for U001."""
    orders = []
    seq = seq_start
    intervals = {
        "B07BFMWZF2": 28,   # Ariel: monthly
        "B00CPFSO6K": 21,   # Head & Shoulders: every 3 weeks
        "B00PNS7HM0": 18,   # Pedigree: every 18 days
    }
    for asin, (cat, title, price) in DEMO_REORDER_ASINS.items():
        interval = intervals.get(asin, 28)
        # Generate 4 historical purchases to give predict_reorder() enough data
        anchor = TODAY - timedelta(days=interval)
        for i in range(4):
            order_date = (anchor - timedelta(days=interval * i)).isoformat()
            product = catalog_map[asin]
            orders.append({
                "user_id": user_id,
                "date": order_date,
                "items": [
                    {
                        "asin": asin,
                        "title": product["title"],
                        "category": product["category"],
                        "price": product["price"],
                        "quantity": 1,
                        "pack_size": product.get("pack_size", 1),
                        "amazon_now_eligible": product.get("amazon_now_eligible", True),
                        "days_since_last_purchase": None,
                        "average_interval_days": None,
                    }
                ],
                "total": product["price"],
                "delivery_type": "amazon_now",
                "occasion_tag": "routine",
                "order_id": f"ORD_{user_id}_{seq:04d}",
            })
            seq += 1
    return orders, seq


def generate_birthday_orders(user_id: str, seq_start: int) -> list[dict]:
    """Inject 2 birthday party orders for U001 using demo party ASINs."""
    orders = []
    seq = seq_start
    # Birthday 1: ~30 days ago
    bday1 = (TODAY - timedelta(days=30)).isoformat()
    # Birthday 2: ~6 months ago
    bday2 = (TODAY - timedelta(days=180)).isoformat()

    for event_date in [bday1, bday2]:
        # One order with all 3 birthday ASINs bundled
        items = []
        order_total = 0
        for asin, (cat, title, price) in DEMO_BIRTHDAY_ASINS.items():
            product = catalog_map[asin]
            items.append({
                "asin": asin,
                "title": product["title"],
                "category": product["category"],
                "price": product["price"],
                "quantity": 1,
                "pack_size": product.get("pack_size", 1),
                "amazon_now_eligible": product.get("amazon_now_eligible", True),
                "days_since_last_purchase": None,
                "average_interval_days": None,
            })
            order_total += product["price"]

        orders.append({
            "user_id": user_id,
            "date": event_date,
            "items": items,
            "total": order_total,
            "delivery_type": "amazon_now",
            "occasion_tag": "kids_birthday",
            "order_id": f"ORD_{user_id}_{seq:04d}",
        })
        seq += 1
    return orders, seq


# ---------------------------------------------------------------------------
# Main generation loop
# ---------------------------------------------------------------------------

print("\nGenerating purchase history for 50 users...")

purchase_history: dict[str, list[dict]] = {}

for uid_num in range(1, 51):
    user_id = f"U{uid_num:03d}"
    group = USER_GROUPS[user_id]
    orders: list[dict] = []
    seq = 1

    # Determine order count: 80-120 for regular users, U001 gets 120+
    if user_id == DEMO_USER:
        base_orders = 120
    else:
        base_orders = random.randint(80, 120)

    # Generate main order stream
    order_dates = sorted(
        [random_date_in_range(YEAR_AGO, TODAY) for _ in range(base_orders)]
    )

    for order_date in order_dates:
        asin = pick_asin_for_group(group)
        occasion = pick_occasion(group)
        orders.append(build_order(user_id, group, seq, order_date, asin, occasion))
        seq += 1

    # U001 special injections
    if user_id == DEMO_USER:
        # Reorder anchors (Ariel, Head & Shoulders, Pedigree)
        anchor_orders, seq = generate_reorder_anchor_orders(user_id, group, seq)
        orders.extend(anchor_orders)

        # Birthday party orders (B001PLATES, B002BALLOONS, B003STREAMERS)
        bday_orders, seq = generate_birthday_orders(user_id, seq)
        orders.extend(bday_orders)

        # Daily milk/eggs/bread for demo morning approval flow
        # Add food_beverages orders for the last 7 days (4+ times)
        food_asins = asins_for_categories("food_beverages")
        for day_offset in [1, 2, 3, 4, 5, 7]:
            order_date = (TODAY - timedelta(days=day_offset)).isoformat()
            asin = random.choice(food_asins)
            orders.append(build_order(user_id, group, seq, order_date, asin, "routine"))
            seq += 1

    # Sort by date
    orders.sort(key=lambda o: o["date"])

    # Re-number order IDs after sorting
    for i, order in enumerate(orders, start=1):
        order["order_id"] = f"ORD_{user_id}_{i:04d}"

    purchase_history[user_id] = orders

# Summary before writing
print("\n--- Order counts per user (sample) ---")
for uid in ["U001", "U010", "U014", "U020", "U027", "U035", "U040", "U050"]:
    print(f"  {uid} ({USER_GROUPS[uid]}): {len(purchase_history[uid])} orders")

# Category distribution per group
print("\n--- Category distribution per identity group ---")
group_cat_counts: dict[str, dict[str, int]] = {g: defaultdict(int) for g in GROUP_PROFILES}

for user_id, orders in purchase_history.items():
    group = USER_GROUPS[user_id]
    for order in orders:
        for item in order["items"]:
            group_cat_counts[group][item["category"]] += 1

for group_name, cat_counts in group_cat_counts.items():
    total = sum(cat_counts.values())
    top5 = sorted(cat_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    print(f"\n  {group_name} (total items: {total}):")
    for cat, count in top5:
        pct = 100 * count / total
        print(f"    {cat:<30} {count:>5} ({pct:.1f}%)")

# Verify U001 demo ASINs
print("\n--- U001 demo ASIN verification ---")
u001_asins = set()
for order in purchase_history["U001"]:
    for item in order["items"]:
        u001_asins.add(item["asin"])

for asin in list(DEMO_REORDER_ASINS.keys()) + list(DEMO_BIRTHDAY_ASINS.keys()):
    found = asin in u001_asins
    status = "FOUND" if found else "MISSING"
    print(f"  {asin}: {status}")

# Verify all ASINs in output exist in catalog
print("\n--- Catalog ASIN verification ---")
all_output_asins = set()
mc_star_found = []
for user_id, orders in purchase_history.items():
    for order in orders:
        for item in order["items"]:
            all_output_asins.add(item["asin"])

missing_from_catalog = [a for a in all_output_asins if a not in catalog_map]
KNOWN_MC_ASINS = {
    "MC_CHIPS_003", "MC_CHIPS_002", "MC_CHOC_002", "MC_CHOC_003",
    "MC_AGARBATTI_001", "MC_AGARBATTI_002", "MC_AGARBATTI_003",
    "MC_DIYAS_001", "MC_MAGGI_001", "MC_FIRSTAID_001",
    "MC_MOSQUITO_001", "MC_MOSQUITO_002", "MC_MOSQUITO_003",
    "MC_PUJAKIT_001", "MC_PUJAKIT_002", "MC_PUJAKIT_003",
    "MC_HOLICOLORS_001", "MC_HOLI_002", "MC_HOLI_003",
    "MC_TORCH_001", "MC_RAIN_001", "MC_RAINSHOES_001", "MC_PURIFIER_001",
    "MC_BACKPACK_001",
}
mc_star_asins = [a for a in all_output_asins if a.startswith("MC_") and a not in KNOWN_MC_ASINS]

if missing_from_catalog:
    print(f"  FATAL: {len(missing_from_catalog)} ASINs not in catalog:")
    for a in missing_from_catalog[:10]:
        print(f"    {a}")
    raise SystemExit(1)
else:
    print(f"  All {len(all_output_asins)} unique ASINs verified in catalog.json")

if mc_star_asins:
    print(f"  NOTE: {len(mc_star_asins)} MC_* ASINs used (all present in catalog): {mc_star_asins[:5]}")

# ---------------------------------------------------------------------------
# Write purchase_history.json
# ---------------------------------------------------------------------------
with open(PURCHASE_HISTORY_PATH, "w", encoding="utf-8") as f:
    json.dump(purchase_history, f, indent=2, ensure_ascii=False)

total_orders = sum(len(v) for v in purchase_history.values())
print(f"\nWrote {PURCHASE_HISTORY_PATH}")
print(f"  Users: {len(purchase_history)}, Total orders: {total_orders}")

# ---------------------------------------------------------------------------
# Update user_cluster_map.json
# ---------------------------------------------------------------------------

GROUP_CONFIDENCES = {
    "office_gym_dad": 0.91,
    "jee_student": 0.87,
    "college_girl": 0.89,
    "home_chef": 0.88,
}

# Apply slight per-user variance to confidence
user_cluster_map = {}
for user_id, group in USER_GROUPS.items():
    base_conf = GROUP_CONFIDENCES[group]
    variance = random.uniform(-0.04, 0.04)
    confidence = round(max(0.75, min(0.98, base_conf + variance)), 2)
    user_cluster_map[user_id] = {
        "cluster_id": group,
        "confidence": confidence,
    }

with open(USER_CLUSTER_MAP_PATH, "w", encoding="utf-8") as f:
    json.dump(user_cluster_map, f, indent=2, ensure_ascii=False)

print(f"\nWrote {USER_CLUSTER_MAP_PATH}")
assignment_summary = ", ".join(
    f"{g}={sum(1 for v in user_cluster_map.values() if v['cluster_id'] == g)}"
    for g in GROUP_PROFILES
)
print(f"  Assignments: {assignment_summary}")

# ---------------------------------------------------------------------------
# Compute centroid feature vectors and update community_groups.json
# Feature vector (6D):
#   [avg_fitness_spend, avg_stationery_spend, avg_beauty_spend,
#    avg_grocery_spend, avg_snack_spend, avg_kitchen_spend]
# ---------------------------------------------------------------------------

FEATURE_CATEGORIES = {
    "fitness_spend": set(FITNESS_OUTDOOR_POOL) | set(asins_for_categories("energy_bar")),
    "stationery_spend": set(STATIONERY_POOL),
    "beauty_spend": set(BEAUTY_CARE_POOL) | set(PERSONAL_CARE_POOL),
    "grocery_spend": set(GROCERY_POOL),
    "snack_spend": set(SNACK_POOL),
    "kitchen_spend": set(KITCHEN_POOL),
}

FEATURE_DIMS = ["fitness_spend", "stationery_spend", "beauty_spend",
                "grocery_spend", "snack_spend", "kitchen_spend"]

# Compute per-user spend totals per feature dimension
user_features: dict[str, list[float]] = {}
for user_id, orders in purchase_history.items():
    dim_totals = {dim: 0.0 for dim in FEATURE_DIMS}
    total_spend = 0.0
    for order in orders:
        for item in order["items"]:
            asin = item["asin"]
            spend = item["price"] * item["quantity"]
            total_spend += spend
            for dim in FEATURE_DIMS:
                if asin in FEATURE_CATEGORIES[dim]:
                    dim_totals[dim] += spend
    # Normalize by total spend
    if total_spend > 0:
        user_features[user_id] = [dim_totals[dim] / total_spend for dim in FEATURE_DIMS]
    else:
        user_features[user_id] = [0.0] * len(FEATURE_DIMS)

# Compute per-group mean feature vector
group_feature_sums: dict[str, list[float]] = {g: [0.0] * len(FEATURE_DIMS) for g in GROUP_PROFILES}
group_member_counts: dict[str, int] = defaultdict(int)

for user_id, features in user_features.items():
    group = USER_GROUPS[user_id]
    for i, v in enumerate(features):
        group_feature_sums[group][i] += v
    group_member_counts[group] += 1

group_centroids_raw: dict[str, list[float]] = {}
for group in GROUP_PROFILES:
    n = group_member_counts[group]
    if n > 0:
        group_centroids_raw[group] = [v / n for v in group_feature_sums[group]]
    else:
        group_centroids_raw[group] = [0.0] * len(FEATURE_DIMS)

# Min-max normalize each dimension across groups
dim_mins = [min(group_centroids_raw[g][i] for g in GROUP_PROFILES) for i in range(len(FEATURE_DIMS))]
dim_maxs = [max(group_centroids_raw[g][i] for g in GROUP_PROFILES) for i in range(len(FEATURE_DIMS))]

def normalize_centroid(raw: list[float]) -> list[float]:
    result = []
    for i, v in enumerate(raw):
        denom = dim_maxs[i] - dim_mins[i]
        if denom < 1e-9:
            result.append(0.0)
        else:
            result.append(round((v - dim_mins[i]) / denom, 6))
    return result

group_centroids_normalized = {g: normalize_centroid(group_centroids_raw[g]) for g in GROUP_PROFILES}

print("\n--- Centroid feature vectors (normalized 0-1) ---")
for group, centroid in group_centroids_normalized.items():
    dims_str = ", ".join(f"{v:.3f}" for v in centroid)
    print(f"  {group}: [{dims_str}]")

# ---------------------------------------------------------------------------
# Update community_groups.json
# Keep existing structure, update cluster_id, centroid, member_count, members
# ---------------------------------------------------------------------------

GROUP_DISPLAY = {
    "office_gym_dad": {
        "group_id": "office_gym_dad",
        "group_name": "The Fit Dads",
        "archetype": "office_gym_dad",
        "tagline": "Protein shakers and school bags — all before 8am",
        "color": "#45B7D1",
        "members": [f"U{i:03d}" for i in range(1, 14)],
    },
    "jee_student": {
        "group_id": "jee_student",
        "group_name": "The JEE Grinders",
        "archetype": "jee_student",
        "tagline": "Highlighters, snacks, repeat",
        "color": "#FFEAA7",
        "members": [f"U{i:03d}" for i in range(14, 27)],
    },
    "college_girl": {
        "group_id": "college_girl",
        "group_name": "The Campus Crew",
        "archetype": "college_girl",
        "tagline": "Skincare, chai, and group study hauls",
        "color": "#DDA0DD",
        "members": [f"U{i:03d}" for i in range(27, 40)],
    },
    "home_chef": {
        "group_id": "home_chef",
        "group_name": "The Kitchen Masters",
        "archetype": "home_chef",
        "tagline": "Fresh dal, tadka, and the perfect masala ratio",
        "color": "#96CEB4",
        "members": [f"U{i:03d}" for i in range(40, 51)],
    },
}

# Compute top categories per group from actual data
group_cat_spend: dict[str, dict[str, float]] = {g: defaultdict(float) for g in GROUP_PROFILES}
for user_id, orders in purchase_history.items():
    group = USER_GROUPS[user_id]
    for order in orders:
        for item in order["items"]:
            group_cat_spend[group][item["category"]] += item["price"] * item["quantity"]

new_community_groups = []
for group_id, display in GROUP_DISPLAY.items():
    cat_spend = group_cat_spend[group_id]
    top_categories = sorted(cat_spend.items(), key=lambda x: x[1], reverse=True)[:6]
    top_categories_fmt = [{"category": cat, "total_spend": round(spend, 2)} for cat, spend in top_categories]

    centroid = group_centroids_normalized[group_id]
    members = display["members"]

    new_community_groups.append({
        "group_id": group_id,
        "group_name": display["group_name"],
        "archetype": group_id,
        "tagline": display["tagline"],
        "color": display["color"],
        "member_count": len(members),
        "members": members,
        "active_now": random.randint(20, 50),
        "top_categories": top_categories_fmt,
        "top_occasion": "kids_birthday",
        "centroid": centroid,
    })

with open(COMMUNITY_GROUPS_PATH, "w", encoding="utf-8") as f:
    json.dump(new_community_groups, f, indent=2, ensure_ascii=False)

print(f"\nWrote {COMMUNITY_GROUPS_PATH}")
for g in new_community_groups:
    print(f"  {g['group_id']}: {g['member_count']} members, centroid={[round(v,3) for v in g['centroid']]}")

# ---------------------------------------------------------------------------
# Write identity_normalization_params.json
# ---------------------------------------------------------------------------

norm_params = {
    "feature_dimensions": FEATURE_DIMS,
    "feature_dimension_descriptions": {
        "fitness_spend": "Fraction of total spend on fitness/outdoor ASINs",
        "stationery_spend": "Fraction of total spend on stationery/office ASINs",
        "beauty_spend": "Fraction of total spend on personal care/beauty ASINs",
        "grocery_spend": "Fraction of total spend on grocery/food ASINs",
        "snack_spend": "Fraction of total spend on snack/beverage ASINs",
        "kitchen_spend": "Fraction of total spend on kitchen/cookware ASINs",
    },
    "normalization_method": "min-max per dimension across 4 identity groups",
    "dim_mins": dim_mins,
    "dim_maxs": dim_maxs,
    "group_centroids_raw": {g: group_centroids_raw[g] for g in GROUP_PROFILES},
    "group_centroids_normalized": group_centroids_normalized,
    "generated_at": TODAY.isoformat(),
    "simulated_data": True,
}

with open(NORM_PARAMS_PATH, "w", encoding="utf-8") as f:
    json.dump(norm_params, f, indent=2, ensure_ascii=False)

print(f"\nWrote {NORM_PARAMS_PATH}")

# ---------------------------------------------------------------------------
# Final validation
# ---------------------------------------------------------------------------
print("\n=== FINAL VALIDATION ===")

# 1. All ASINs in catalog
all_asins_in_output = set()
for orders in purchase_history.values():
    for order in orders:
        for item in order["items"]:
            all_asins_in_output.add(item["asin"])

bad_asins = [a for a in all_asins_in_output if a not in catalog_map]
print(f"  Catalog ASIN check: {len(all_asins_in_output)} unique ASINs — {'PASS' if not bad_asins else f'FAIL ({bad_asins[:3]})'}")

# 2. U001 birthday demo ASINs
u001_asin_set = set()
for order in purchase_history["U001"]:
    for item in order["items"]:
        u001_asin_set.add(item["asin"])

birthday_check = all(a in u001_asin_set for a in DEMO_BIRTHDAY_ASINS)
reorder_check = all(a in u001_asin_set for a in DEMO_REORDER_ASINS)
print(f"  U001 birthday ASINs: {'PASS' if birthday_check else 'FAIL'}")
print(f"  U001 reorder ASINs: {'PASS' if reorder_check else 'FAIL'}")

# 3. U001 birthday order count
u001_bday_orders = [o for o in purchase_history["U001"] if o["occasion_tag"] == "kids_birthday"]
print(f"  U001 kids_birthday orders: {len(u001_bday_orders)} (need >= 2) — {'PASS' if len(u001_bday_orders) >= 2 else 'FAIL'}")

# 4. Food beverages in last 7 days for U001
cutoff = (TODAY - timedelta(days=7)).isoformat()
u001_recent_food = [
    o for o in purchase_history["U001"]
    if o["date"] >= cutoff and any(
        i["category"] == "food_beverages" for i in o["items"]
    )
]
print(f"  U001 food_beverages orders last 7d: {len(u001_recent_food)} (need >= 4) — {'PASS' if len(u001_recent_food) >= 4 else 'FAIL'}")

# 5. Order counts
below_60 = [uid for uid, orders in purchase_history.items() if len(orders) < 60]
print(f"  Users with < 60 orders: {len(below_60)} (should be 0) — {'PASS' if not below_60 else f'FAIL {below_60}'}")

# 6. Total orders
total = sum(len(v) for v in purchase_history.values())
print(f"  Total orders: {total}")

print("\nDone.")
