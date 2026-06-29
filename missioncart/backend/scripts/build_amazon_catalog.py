"""
Build MissionCart catalog from Amazon Product Metadata 2023 (McAuley Lab, UCSD)

Run:
    python scripts/build_amazon_catalog.py

Input:
    backend/app/data/amazon_raw/*.jsonl.gz

Output:
    backend/app/data/catalog.json           (replaces existing)
    backend/app/data/compatibility_graph.json  (replaces existing)
    backend/app/data/occasion_cooccurrence.json (new — extends existing)

The script is idempotent: running it twice produces the same output.
Processing is fully streaming — no raw file is loaded into RAM at once.

Catalog schema reference (every field catalog.json uses):
    asin, title, category, subcategory, brand, price, pack_size, unit,
    price_per_unit, rating, review_count, prime, amazon_now_eligible,
    delivery_eta, eta_days, return_risk, compatibility_tags, safety_tags,
    sponsored, stock_available, image_url
"""

import gzip
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).parent.resolve()
DATA_DIR = SCRIPT_DIR.parent / "app" / "data"
RAW_DIR = DATA_DIR / "amazon_raw"

CATALOG_OUT = DATA_DIR / "catalog.json"
COMPAT_OUT = DATA_DIR / "compatibility_graph.json"
COOCCUR_OUT = DATA_DIR / "occasion_cooccurrence.json"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
USD_TO_INR = 83.0
MAX_CATALOG_ENTRIES = 15_000
MAX_PER_FILE = 4_000             # Accepted products cap per source file
MAX_TOTAL_COLLECTED = 30_000     # Global cap before merge — prevents RAM blowup on large files
PROGRESS_INTERVAL = 10_000       # Print progress every N lines
MIN_RATING = 3.5
MIN_REVIEW_COUNT = 10

BAD_TITLE_TOKENS = {"used", "refurbished", "parts only", "for parts"}

# Demo ASINs that must always appear at the top of catalog.json unchanged.
# The values here are the exact ASINs from the current catalog.json.
# If the ASIN appears in the existing catalog, it is kept verbatim.
DEMO_ASINS_PRIORITY = [
    # Party/audit demo
    "B08BLCZ3NV",    # Paper Plates
    "B0PARTY002",
    "B0PARTY003",
    "B0PARTY004",
    "B0PARTY005",
    "B0PARTY006",
    "B0PARTY007",
    "B0PARTY008",
    # Reorder demo
    "MC_ARIEL_001",
    "MC_SHAMPOO_001",
    "MC_DOGFOOD_001",
    # Morning approval
    "MC_MILK_001",
    "MC_EGGS_001",
    "MC_BREAD_001",
    # Audit items (exact titles hardcoded in audit_engine.py)
    "B001PLATES",
    "B002BALLOONS",
    "B003STREAMERS",
    "B003BSTREAMERS",
    "B004CUPS",
    "B005MILK",
    "B006EGGS",
    "B007BREAD",
]

# ---------------------------------------------------------------------------
# Category mapping
# ---------------------------------------------------------------------------
# Keys are lowercase substrings found in Amazon's category path list.
# Values are our catalog category names (matching category values in catalog.json).
CATEGORY_MAP = {
    # Health & Personal Care ->personal_care / specific sub-cats
    "shampoo": "shampoo",
    "hair conditioner": "hair_care",
    "hair care": "hair_care",
    "hair color": "hair_care",
    "hair oil": "hair_care",
    "skin care": "skin_care",
    "face wash": "skin_care",
    "moisturizer": "skin_care",
    "sunscreen": "skin_care",
    "body lotion": "skin_care",
    "face mask": "skin_care",
    "eye care": "personal_care",
    "lip care": "personal_care",
    "oral care": "oral_care",
    "toothpaste": "oral_care",
    "toothbrush": "oral_care",
    "mouthwash": "oral_care",
    "deodorant": "personal_care",
    "body wash": "personal_care",
    "soap": "personal_care",
    "feminine care": "personal_care",
    "men's grooming": "personal_care",
    "shaving": "personal_care",
    "razor": "personal_care",
    "cotton": "personal_care",
    "bandage": "medicines_health",
    "first aid": "medicines_health",
    "vitamins": "medicines_health",
    "supplements": "medicines_health",
    "health monitors": "medicines_health",
    "blood pressure": "medicines_health",
    "thermometer": "medicines_health",
    "pain relief": "medicines_health",
    "cold & flu": "medicines_health",
    "allergy": "medicines_health",
    "antacid": "medicines_health",
    "medical": "medicines_health",
    # Grocery & Gourmet Food
    "milk": "dairy",
    "cheese": "dairy",
    "butter": "dairy",
    "yogurt": "dairy",
    "eggs": "dairy",
    "bread": "bakery",
    "biscuit": "biscuits",
    "cookies": "biscuits",
    "crackers": "biscuits",
    "snack": "snacks",
    "chips": "snacks",
    "popcorn": "snacks",
    "nuts": "snacks",
    "chocolate": "snacks",
    "candy": "snacks",
    "rice": "rice",
    "flour": "staples",
    "lentil": "pulses",
    "dal": "pulses",
    "pulses": "pulses",
    "cooking oil": "cooking_oil",
    "olive oil": "cooking_oil",
    "ghee": "cooking_oil",
    "coffee": "beverages",
    "tea": "beverages",
    "juice": "beverages",
    "soft drink": "beverages",
    "water": "beverages",
    "spice": "spices",
    "masala": "spices",
    "sauce": "condiments",
    "ketchup": "condiments",
    "pickle": "condiments",
    "jam": "condiments",
    "honey": "condiments",
    "sugar": "staples",
    "salt": "staples",
    "pasta": "staples",
    "noodle": "staples",
    "cereal": "breakfast",
    "oats": "breakfast",
    "breakfast": "breakfast",
    "frozen": "frozen_food",
    "ice cream": "frozen_food",
    "baby food": "baby_care",
    "formula": "baby_care",
    "organic": "organic",
    # Pet Supplies
    "dog food": "dog_food",
    "dog treat": "dog_food",
    "cat food": "cat_food",
    "cat treat": "cat_food",
    "cat litter": "pet_care",
    "pet shampoo": "pet_care",
    "pet bowl": "pet_care",
    "pet toy": "pet_care",
    "pet bed": "pet_care",
    "aquarium": "pet_care",
    "fish food": "pet_care",
    "bird food": "pet_care",
    "small animal": "pet_care",
    "flea": "pet_care",
    "collar": "pet_care",
    "leash": "pet_care",
    "crate": "pet_care",
    # Home & Kitchen
    "cookware": "cookware",
    "frying pan": "cookware",
    "pressure cooker": "cookware",
    "wok": "cookware",
    "bakeware": "cookware",
    "knife": "kitchen",
    "cutting board": "kitchen",
    "chopping board": "kitchen",
    "kitchen tool": "kitchen",
    "mixing bowl": "kitchen",
    "food storage": "kitchen",
    "lunch box": "kitchen",
    "water bottle": "kitchen",
    "kettle": "kitchen",
    "toaster": "kitchen",
    "blender": "kitchen",
    "mixer": "kitchen",
    "juicer": "kitchen",
    "laundry": "laundry",
    "washing": "laundry",
    "detergent": "detergent",
    "fabric softener": "laundry",
    "dish": "dishwashing",
    "dishwasher": "dishwashing",
    "cleaning": "household",
    "floor cleaner": "household",
    "toilet cleaner": "household",
    "air freshener": "household",
    "garbage bag": "household",
    "trash bag": "household",
    "broom": "household",
    "mop": "household",
    "bedsheet": "bedding",
    "pillow": "bedding",
    "blanket": "bedding",
    "mattress": "bedding",
    "towel": "bath",
    "shower": "bath",
    "bath mat": "bath",
    "curtain": "home_decor",
    "lamp": "home_decor",
    "candle": "candles",
    "frame": "home_decor",
    "storage": "storage",
    "shelf": "storage",
    "organizer": "storage",
    "hanger": "storage",
    "bulb": "electrical",
    "extension": "electrical",
    "adapter": "electrical",
    "battery": "electrical",
    # Toys & Games ->party_supplies / toys
    "balloon": "balloon_set",
    "streamer": "decoration_streamers",
    "confetti": "decorations",
    "party": "occasion_extras",
    "tablecloth": "tablecloth",
    "plate": "plates",
    "cup": "cups",
    "napkin": "napkins",
    "banner": "banner",
    "decoration": "decorations",
    "birthday": "occasion_extras",
    "doll": "toys_games",
    "action figure": "toys_games",
    "stuffed animal": "toys_games",
    "plush": "toys_games",
    "board game": "toys_games",
    "card game": "toys_games",
    "puzzle": "toys_games",
    "lego": "toys_games",
    "building block": "toys_games",
    "remote control": "toys_games",
    "video game": "toys_games",
    "outdoor toy": "outdoor_sports",
    "bike": "outdoor_sports",
    "scooter": "outdoor_sports",
    "cricket": "outdoor_sports",
    # Office Products ->stationery
    "notebook": "stationery",
    "pen": "stationery",
    "pencil": "stationery",
    "highlighter": "stationery",
    "marker": "stationery",
    "sticky note": "stationery",
    "folder": "stationery",
    "binder": "stationery",
    "stapler": "stationery",
    "tape": "stationery",
    "scissors": "stationery",
    "calculator": "stationery",
    "printer paper": "stationery",
    "printer": "electronics",
    "ink cartridge": "electronics",
    "toner": "electronics",
    "keyboard": "electronics",
    "mouse": "electronics",
    "monitor": "electronics",
    "laptop stand": "electronics",
    "webcam": "electronics",
    "headphone": "electronics",
    "speaker": "electronics",
    "usb": "electronics",
    "cable": "electronics",
    "charger": "electronics",
    "power bank": "electronics",
}

# Source-file-level default categories when no keyword match found.
SOURCE_DEFAULT_CATEGORY = {
    "meta_Health_and_Personal_Care.jsonl.gz": "personal_care",
    "meta_Grocery_and_Gourmet_Food.jsonl.gz": "food_beverages",
    "meta_Pet_Supplies.jsonl.gz": "pet_care",
    "meta_Home_and_Kitchen.jsonl.gz": "household",
    "meta_Toys_and_Games.jsonl.gz": "toys_games",
    "meta_Office_Products.jsonl.gz": "stationery",
}

# ---------------------------------------------------------------------------
# Category mapping logic
# ---------------------------------------------------------------------------

def map_category(categories_list: list, source_file: str) -> str:
    """Map Amazon category path to our catalog category name."""
    combined = " ".join(str(c) for c in categories_list).lower()
    # Walk the map longest-match first to avoid "cup" matching "cupboard"
    for keyword in sorted(CATEGORY_MAP.keys(), key=len, reverse=True):
        if keyword in combined:
            return CATEGORY_MAP[keyword]
    # Fall back to source-file default
    return SOURCE_DEFAULT_CATEGORY.get(source_file, "general")


# ---------------------------------------------------------------------------
# Price parsing
# ---------------------------------------------------------------------------

_PRICE_RE = re.compile(r"[\$£€₹]?\s*([\d,]+\.?\d*)")


def parse_price_usd(raw: object) -> Optional[float]:
    """Parse Amazon's price field (string or numeric) into a USD float."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        val = float(raw)
        return val if val > 0 else None
    s = str(raw).strip()
    m = _PRICE_RE.search(s)
    if m:
        try:
            val = float(m.group(1).replace(",", ""))
            return val if val > 0 else None
        except ValueError:
            return None
    return None


def usd_to_inr(usd: float) -> int:
    """Convert USD to INR, rounded to nearest ₹10."""
    return int(round(usd * USD_TO_INR / 10) * 10)


# ---------------------------------------------------------------------------
# Safety / unit / pack inference
# ---------------------------------------------------------------------------

def infer_safety_tags(product: dict) -> list:
    tags = []
    title_lower = (product.get("title") or "").lower()
    cats = " ".join(str(c) for c in (product.get("categories") or [])).lower()
    features = " ".join(str(f) for f in (product.get("features") or [])).lower()
    combined = f"{title_lower} {cats} {features}"

    if any(k in combined for k in ["toy", "game", "school", "kids", "children", "baby",
                                    "toddler", "infant", "educational"]):
        tags.append("child_safe")
    if any(k in combined for k in ["food", "grocery", "snack", "beverage", "milk",
                                    "cereal", "organic"]):
        tags.append("food_grade")
    if any(k in combined for k in ["eco", "biodegradable", "compostable", "recycled"]):
        tags.append("eco")
    if any(k in combined for k in ["bpa free", "bpa-free", "non-toxic"]):
        tags.append("non_toxic")
    return tags


def infer_unit(product: dict) -> str:
    title = (product.get("title") or "").lower()
    details = str(product.get("details") or "").lower()
    combined = f"{title} {details}"
    if any(k in combined for k in ["ml ", "milliliter", "liter", "litre", "fl oz", "fl. oz"]):
        return "ml"
    if any(k in combined for k in [" kg", " gram", "grams", " g ", " lbs", " oz "]):
        return "g"
    if "pack" in combined or "count" in combined or "ct " in combined:
        return "pack"
    return "unit"


def infer_pack_size(product: dict) -> int:
    title = product.get("title") or ""
    match = re.search(
        r"pack\s+of\s+(\d+)|(\d+)\s*[-\s]?\s*pack\b|(\d+)\s*count\b|(\d+)\s*\bct\b",
        title,
        re.IGNORECASE,
    )
    if match:
        val = next((g for g in match.groups() if g is not None), None)
        if val:
            return max(1, int(val))
    return 1


# ---------------------------------------------------------------------------
# Subcategory inference (minor enrichment)
# ---------------------------------------------------------------------------

def infer_subcategory(product: dict, category: str) -> str:
    title = (product.get("title") or "").lower()
    if "premium" in title or "luxury" in title or "gold" in title:
        return "premium"
    if "eco" in title or "biodegradable" in title or "organic" in title:
        return "eco"
    if "kids" in title or "children" in title or "themed" in title:
        return "themed"
    if "budget" in title or "value" in title or "economy" in title:
        return "budget"
    return "standard"


# ---------------------------------------------------------------------------
# Core record mapper
# ---------------------------------------------------------------------------

def map_amazon_to_catalog(product: dict, source_file: str) -> Optional[dict]:
    """
    Map a raw Amazon 2023 product record to our catalog schema.
    Returns None if the product should be filtered out.
    """
    # --- Filter checks ---
    title = (product.get("title") or "").strip()
    if not title or len(title) < 5:
        return None

    title_lower = title.lower()
    if any(bad in title_lower for bad in BAD_TITLE_TOKENS):
        return None

    rating = product.get("average_rating")
    try:
        rating = float(rating) if rating is not None else 0.0
    except (ValueError, TypeError):
        rating = 0.0
    if rating < MIN_RATING:
        return None

    review_count = product.get("rating_number")
    try:
        review_count = int(review_count) if review_count is not None else 0
    except (ValueError, TypeError):
        review_count = 0
    if review_count < MIN_REVIEW_COUNT:
        return None

    price_usd = parse_price_usd(product.get("price"))
    if price_usd is None:
        return None
    price_inr = usd_to_inr(price_usd)
    if price_inr <= 0:
        return None

    # --- Category ---
    categories = product.get("categories") or []
    category = map_category(categories, source_file)

    # --- Derived fields ---
    pack_size = infer_pack_size(product)
    unit = infer_unit(product)
    price_per_unit = round(price_inr / pack_size, 2) if pack_size > 0 else price_inr
    safety_tags = infer_safety_tags(product)
    subcategory = infer_subcategory(product, category)

    return_risk = round(max(0.01, min(0.35, (5.0 - rating) * 0.08)), 3)

    # Amazon Now: fast-moving items priced under ₹2000
    amazon_now = price_inr < 2000

    # Delivery ETA based on Amazon Now eligibility
    if amazon_now:
        delivery_eta = "now_20min"
        eta_days = 0
    else:
        delivery_eta = "tomorrow"
        eta_days = 1

    return {
        "asin": product["parent_asin"],
        "title": title[:120],
        "category": category,
        "subcategory": subcategory,
        "brand": (product.get("store") or "").strip()[:60],
        "price": price_inr,
        "pack_size": pack_size,
        "unit": unit,
        "price_per_unit": price_per_unit,
        "rating": round(rating, 1),
        "review_count": review_count,
        "prime": True,
        "amazon_now_eligible": amazon_now,
        "delivery_eta": delivery_eta,
        "eta_days": eta_days,
        "return_risk": return_risk,
        "compatibility_tags": [],
        "safety_tags": safety_tags,
        "sponsored": False,
        "stock_available": True,
        "image_url": "",
        # Internal fields for compatibility graph construction — stripped before final write
        "_bought_together": product.get("bought_together") or [],
        "_categories_raw": categories,
    }


# ---------------------------------------------------------------------------
# Pass 1: stream all raw files, collect products
# ---------------------------------------------------------------------------

def load_raw_products(raw_dir: Path) -> tuple[list[dict], dict[str, int]]:
    """
    Stream all .jsonl.gz files and return:
      - list of mapped catalog entries (with _bought_together still attached)
      - category distribution dict

    Memory-bounded: stops accepting from a file once MAX_PER_FILE is reached,
    and stops entirely once MAX_TOTAL_COLLECTED is reached. This prevents RAM
    exhaustion when processing large files like Home_and_Kitchen (2.8 GB gzip).
    """
    gz_files = sorted(raw_dir.glob("*.jsonl.gz"))
    if not gz_files:
        print(f"ERROR: No .jsonl.gz files found in {raw_dir}")
        print("Run:  python scripts/download_amazon_data.py  first.")
        sys.exit(1)

    all_products: list[dict] = []
    seen_asins: set[str] = set()
    category_dist: dict[str, int] = defaultdict(int)

    for gz_path in gz_files:
        # Stop processing further files once global cap is reached
        if len(all_products) >= MAX_TOTAL_COLLECTED:
            print(f"\nGlobal cap {MAX_TOTAL_COLLECTED:,} reached — skipping remaining files.")
            break

        source_file = gz_path.name
        print(f"\nProcessing: {source_file}")
        line_count = 0
        accepted = 0
        skipped = 0
        file_accepted = 0

        with gzip.open(gz_path, "rt", encoding="utf-8", errors="replace") as fh:
            for raw_line in fh:
                line_count += 1

                if line_count % PROGRESS_INTERVAL == 0:
                    print(f"  Lines processed: {line_count:,}  accepted: {accepted:,}", end="\r")

                # Per-file cap: move to next file once we have enough from this one
                if file_accepted >= MAX_PER_FILE:
                    print(f"\n  Per-file cap {MAX_PER_FILE:,} reached — moving to next file.")
                    break

                # Global cap check inside the loop too
                if len(all_products) >= MAX_TOTAL_COLLECTED:
                    print(f"\n  Global cap {MAX_TOTAL_COLLECTED:,} reached — stopping.")
                    break

                raw_line = raw_line.strip()
                if not raw_line:
                    continue

                try:
                    record = json.loads(raw_line)
                except json.JSONDecodeError:
                    skipped += 1
                    continue

                asin = record.get("parent_asin") or record.get("asin")
                if not asin or asin in seen_asins:
                    skipped += 1
                    continue

                mapped = map_amazon_to_catalog(record, source_file)
                if mapped is None:
                    skipped += 1
                    continue

                seen_asins.add(asin)
                all_products.append(mapped)
                category_dist[mapped["category"]] += 1
                accepted += 1
                file_accepted += 1

        print(f"  Lines processed: {line_count:,}  accepted: {accepted:,}  skipped: {skipped:,}")

    return all_products, dict(category_dist)


# ---------------------------------------------------------------------------
# Pass 2: merge with existing demo products, enforce cap
# ---------------------------------------------------------------------------

def merge_with_existing(
    new_products: list[dict],
    existing_path: Path,
    demo_asins: list[str],
    cap: int,
) -> list[dict]:
    """
    1. Load existing catalog.json
    2. Keep demo ASINs verbatim at the top
    3. Append highest-rated new Amazon products up to cap
    4. De-duplicate by ASIN throughout
    """
    existing: list[dict] = []
    if existing_path.exists():
        with open(existing_path, encoding="utf-8") as f:
            existing = json.load(f)

    # Build lookup for existing products
    existing_by_asin: dict[str, dict] = {p["asin"]: p for p in existing}

    # Collect demo items first (in priority order), falling back gracefully
    result: list[dict] = []
    used_asins: set[str] = set()

    for asin in demo_asins:
        if asin in existing_by_asin:
            result.append(existing_by_asin[asin])
            used_asins.add(asin)

    # Sort new Amazon products by rating desc, review_count desc
    new_products_sorted = sorted(
        new_products,
        key=lambda p: (p["rating"], p["review_count"]),
        reverse=True,
    )

    for product in new_products_sorted:
        if len(result) >= cap:
            break
        asin = product["asin"]
        if asin in used_asins:
            continue
        # Strip internal pipeline fields before writing
        clean = {k: v for k, v in product.items() if not k.startswith("_")}
        result.append(clean)
        used_asins.add(asin)

    return result


# ---------------------------------------------------------------------------
# Compatibility graph from bought_together edges
# ---------------------------------------------------------------------------

def build_compatibility_graph(
    products: list[dict],
    existing_graph_path: Path,
) -> dict:
    """
    Build compatibility graph from bought_together co-purchase signals.
    Merges with existing handcrafted edges (compatibility_graph.json).
    Output format matches existing compatibility_graph.json: category-keyed dict.
    """
    # Load existing handcrafted graph
    existing_graph: dict = {}
    if existing_graph_path.exists():
        with open(existing_graph_path, encoding="utf-8") as f:
            existing_graph = json.load(f)

    asin_to_category: dict[str, str] = {p["asin"]: p["category"] for p in products}
    # Add existing catalog items' categories too (loaded earlier as demo items)
    # (they don't have _bought_together so nothing extra to add)

    # Tally category-pair co-occurrences
    cat_pair_counts: dict[tuple[str, str], int] = defaultdict(int)
    cat_pair_total: dict[str, int] = defaultdict(int)

    for product in products:
        from_cat = product.get("category", "")
        bought_together = product.get("_bought_together") or []
        for related_asin in bought_together[:5]:
            to_cat = asin_to_category.get(related_asin)
            if to_cat and to_cat != from_cat:
                key = (from_cat, to_cat)
                cat_pair_counts[key] += 1
                cat_pair_total[from_cat] += 1

    # Build new graph entries from strong co-purchase signals
    # Threshold: pair must appear in at least 3 products and > 10% of from_cat's edges
    new_graph = dict(existing_graph)  # start from existing

    for (from_cat, to_cat), count in cat_pair_counts.items():
        total = cat_pair_total[from_cat]
        if count < 3 or total == 0:
            continue
        strength = count / total
        if strength < 0.10:
            continue

        # Only add a "recommends" edge if the category pair isn't already handled
        if from_cat not in new_graph:
            new_graph[from_cat] = {
                "requires": [],
                "recommends": [],
                "incompatible_with": [],
            }
        entry = new_graph[from_cat]
        if to_cat not in entry["recommends"] and to_cat not in entry.get("requires", []):
            # High-strength (>40%) pairs become "recommends"
            if strength > 0.40:
                entry["recommends"].append(to_cat)

    return new_graph


# ---------------------------------------------------------------------------
# Occasion co-occurrence: preserve existing + add category-level pairs
# ---------------------------------------------------------------------------

def build_occasion_cooccurrence(
    products: list[dict],
    existing_path: Path,
) -> dict:
    """
    The existing occasion_cooccurrence.json is keyed by occasion ->ASIN ->co_asins.
    We preserve all existing entries and append a new top-level key:
    "category_pairs" listing strong bought-together category associations.
    This is additive — existing occasion data is never modified.
    """
    existing: dict = {}
    if existing_path.exists():
        with open(existing_path, encoding="utf-8") as f:
            existing = json.load(f)

    asin_to_category: dict[str, str] = {p["asin"]: p["category"] for p in products}

    cat_pair_counts: dict[tuple[str, str], int] = defaultdict(int)
    cat_total: dict[str, int] = defaultdict(int)

    for product in products:
        from_cat = product.get("category", "")
        for related_asin in (product.get("_bought_together") or [])[:5]:
            to_cat = asin_to_category.get(related_asin)
            if to_cat and to_cat != from_cat:
                cat_pair_counts[(from_cat, to_cat)] += 1
                cat_total[from_cat] += 1

    pairs = []
    for (cat_a, cat_b), count in sorted(cat_pair_counts.items(), key=lambda x: -x[1]):
        total = cat_total[cat_a]
        if total == 0 or count < 5:
            continue
        cooccurrence = round(count / total, 3)
        if cooccurrence >= 0.05:
            pairs.append({
                "cat_a": cat_a,
                "cat_b": cat_b,
                "cooccurrence": cooccurrence,
                "support_count": count,
            })

    # Sort by cooccurrence descending
    pairs.sort(key=lambda x: -x["cooccurrence"])

    # Merge: preserve existing data, add/update category_pairs section
    result = dict(existing)
    result["category_pairs"] = pairs

    return result


# ---------------------------------------------------------------------------
# Main ETL flow
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 60)
    print("MissionCart Amazon Catalog ETL")
    print("=" * 60)

    # Pre-flight check
    if not RAW_DIR.exists():
        print(f"\nERROR: Raw data directory not found: {RAW_DIR}")
        print("Run:  python scripts/download_amazon_data.py  first.")
        sys.exit(1)

    gz_files = list(RAW_DIR.glob("*.jsonl.gz"))
    if not gz_files:
        print(f"\nERROR: No .jsonl.gz files in {RAW_DIR}")
        print("Run:  python scripts/download_amazon_data.py  first.")
        sys.exit(1)

    print(f"\nFound {len(gz_files)} raw files in {RAW_DIR}")

    # --- Step 1: Stream and map raw products ---
    print("\n--- Step 1: Loading and filtering raw Amazon data ---")
    new_products, category_dist = load_raw_products(RAW_DIR)
    print(f"\nProducts loaded from Amazon data: {len(new_products):,}")

    # --- Step 2: Merge with existing demo catalog ---
    print("\n--- Step 2: Merging with existing catalog ---")
    final_catalog = merge_with_existing(
        new_products=new_products,
        existing_path=CATALOG_OUT,
        demo_asins=DEMO_ASINS_PRIORITY,
        cap=MAX_CATALOG_ENTRIES,
    )
    print(f"Final catalog size: {len(final_catalog):,} products")

    # Verify demo ASINs made it in
    final_asin_set = {p["asin"] for p in final_catalog}
    demo_preserved = sum(1 for a in DEMO_ASINS_PRIORITY if a in final_asin_set)
    print(f"Demo products preserved: {demo_preserved}/{len(DEMO_ASINS_PRIORITY)}")

    # --- Step 3: Compatibility graph ---
    print("\n--- Step 3: Building compatibility graph ---")
    compat_graph = build_compatibility_graph(new_products, COMPAT_OUT)
    edge_count = sum(
        len(v.get("requires", [])) + len(v.get("recommends", []))
        for v in compat_graph.values()
    )
    print(f"Compatibility graph: {len(compat_graph)} nodes, ~{edge_count} edges")

    # --- Step 4: Occasion co-occurrence ---
    print("\n--- Step 4: Building occasion co-occurrence ---")
    cooccurrence = build_occasion_cooccurrence(new_products, COOCCUR_OUT)
    pair_count = len(cooccurrence.get("category_pairs", []))
    print(f"Co-occurrence pairs: {pair_count}")

    # --- Step 5: Write outputs ---
    print("\n--- Step 5: Writing outputs ---")

    # Strip internal _ fields from catalog before writing
    catalog_clean = []
    for p in final_catalog:
        catalog_clean.append({k: v for k, v in p.items() if not k.startswith("_")})

    with open(CATALOG_OUT, "w", encoding="utf-8") as f:
        json.dump(catalog_clean, f, ensure_ascii=False, indent=2)
    print(f"  catalog.json written: {len(catalog_clean):,} products ->{CATALOG_OUT}")

    with open(COMPAT_OUT, "w", encoding="utf-8") as f:
        json.dump(compat_graph, f, ensure_ascii=False, indent=2)
    print(f"  compatibility_graph.json written ->{COMPAT_OUT}")

    with open(COOCCUR_OUT, "w", encoding="utf-8") as f:
        json.dump(cooccurrence, f, ensure_ascii=False, indent=2)
    print(f"  occasion_cooccurrence.json written ->{COOCCUR_OUT}")

    # --- Final stats ---
    print("\n" + "=" * 60)
    print("CATALOG BUILD COMPLETE")
    print("=" * 60)
    print(f"Products loaded from Amazon data : {len(new_products):,}")
    print(f"Final catalog size (capped at {MAX_CATALOG_ENTRIES:,}): {len(catalog_clean):,}")
    print(f"Demo products preserved          : {demo_preserved}/{len(DEMO_ASINS_PRIORITY)}")
    print(f"Compatibility graph edges        : {edge_count}")
    print(f"Co-occurrence pairs              : {pair_count}")
    print("\nCategory distribution (top 30):")
    for cat, count in sorted(category_dist.items(), key=lambda x: -x[1])[:30]:
        print(f"  {cat:<30} {count:>6}")
    print("\nNext step:")
    print("  python scripts/rebuild_faiss_index.py")


if __name__ == "__main__":
    main()
