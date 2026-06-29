"""
build_community_data.py
=======================
Offline ML pipeline for MissionCart Community feature.

Reads:
  - backend/app/data/simulated/users.json
  - backend/app/data/simulated/purchase_history.json
  - backend/app/data/simulated/occasion_history.json
  - backend/app/data/simulated/community_sessions.json
  - backend/app/data/catalog.json

Writes:
  - backend/app/data/community_groups.json        — 6 cluster definitions
  - backend/app/data/user_cluster_map.json         — {user_id: cluster_id}
  - backend/app/data/occasion_cooccurrence.json    — co-purchase matrix
  - backend/app/data/community_insights.json       — pre-computed insights

Scale notes:
  - At 10M users: replace this script with a Spark job.
    User vectors partitioned by user_id hash into 512 partitions.
    K-Means via spark.ml.clustering.KMeans (Bisecting K-Means for speed).
    Results written to Redis with TTL=24h, re-computed nightly.
  - Co-purchase matrix at scale: use implicit ALS (Spark MLlib) instead of
    frequency counting. Store item factors in Redis for sub-millisecond lookup.
  - Community insights: aggregate in BigQuery/Redshift, cache in Memorystore.
"""

import json
import sys
import os
from pathlib import Path
from collections import defaultdict
import random

import numpy as np

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
DATA = ROOT / "app" / "data"
SIM  = DATA / "simulated"

# ── Category groupings for feature vector ────────────────────────────────────
GROCERY_CATS = {
    "grocery_staples", "dairy", "snacks", "biscuits", "cooking_oil",
    "spices", "rice_flour", "beverages", "instant_food", "tea_coffee",
    "packaged_food",
}
PARTY_CATS = {
    "plates", "cups", "balloons", "candles", "return_gifts",
    "party_supplies", "decorations", "festival_lights", "pooja_items",
    "cakes", "return_gift",
}
HOME_CATS = {
    "mattress", "bedsheet", "storage", "curtains", "cleaning",
    "furniture", "induction_cooktop", "induction_compatible_vessel",
    "water_purifier", "kitchen_tools", "home_decor", "cookware",
    "water_bottle_kitchen",
}
PERSONAL_CARE_CATS = {
    "shampoo", "soap", "toothpaste", "personal_care", "skincare",
    "hair_care", "hygiene",
}
TRAVEL_CATS = {
    "backpack", "water_bottle", "power_bank", "trekking", "outdoor",
    "travel_accessories", "torch", "first_aid", "travel_prep",
}


def categorise(cat: str) -> str:
    c = cat.lower()
    if c in GROCERY_CATS:
        return "grocery"
    if c in PARTY_CATS:
        return "party"
    if c in HOME_CATS:
        return "home"
    if c in PERSONAL_CARE_CATS:
        return "personal_care"
    if c in TRAVEL_CATS:
        return "travel"
    return "other"


# ── K-Means (pure numpy) ─────────────────────────────────────────────────────
# Scale note: At 10M users this becomes spark.ml.KMeans or a mini-batch variant
# with cosine distance. Here we use Euclidean on L2-normalised vectors.

def kmeans_plusplus_init(X: np.ndarray, k: int, rng: np.random.Generator) -> np.ndarray:
    """K-Means++ initialisation for better convergence."""
    n = X.shape[0]
    idx = rng.integers(n)
    centroids = [X[idx]]
    for _ in range(1, k):
        dists = np.array([
            min(np.linalg.norm(x - c) ** 2 for c in centroids)
            for x in X
        ])
        probs = dists / dists.sum()
        idx = rng.choice(n, p=probs)
        centroids.append(X[idx])
    return np.array(centroids)


def kmeans(X: np.ndarray, k: int = 6, max_iter: int = 100,
           random_state: int = 42) -> tuple[np.ndarray, np.ndarray]:
    """
    Pure numpy K-Means.

    Scale note: At 10M users switch to mini-batch K-Means or ALS.
    Time complexity: O(N * K * I * D) where I=iterations, D=dimensions.
    At current scale (50 users, 10 dims, 6 clusters): negligible.
    At 10M users: ~10M * 6 * 100 * 10 = 6B ops → use Spark MLlib.

    Returns:
        labels: (N,) cluster assignment per point
        centroids: (K, D) final centroids
    """
    rng = np.random.default_rng(random_state)
    centroids = kmeans_plusplus_init(X, k, rng)

    labels = np.zeros(len(X), dtype=int)
    for iteration in range(max_iter):
        # Assignment step
        dists = np.array([
            [np.linalg.norm(x - c) for c in centroids]
            for x in X
        ])  # shape (N, K)
        new_labels = np.argmin(dists, axis=1)

        if np.array_equal(new_labels, labels) and iteration > 0:
            break  # converged
        labels = new_labels

        # Update step
        for k_idx in range(k):
            members = X[labels == k_idx]
            if len(members) > 0:
                centroids[k_idx] = members.mean(axis=0)

    return labels, centroids


# ── Feature engineering ───────────────────────────────────────────────────────
def build_user_vector(user: dict, orders: list, occasions: list) -> np.ndarray:
    """
    Build a 10-dim feature vector for one user.

    Dimensions:
      0: grocery_spend_ratio
      1: party_spend_ratio
      2: home_setup_spend_ratio
      3: personal_care_ratio
      4: travel_spend_ratio
      5: occasion_diversity_score  (num distinct occasion_types / 8)
      6: budget_tier               (monthly_grocery_budget / 15000 capped at 1)
      7: order_frequency           (orders_per_month, capped at 1 at 30/month)
      8: household_size_normalized (household_size / 6 capped at 1)
      9: is_prime                  (0 or 1)

    Scale note: At 10M users add collaborative signal (item2vec embeddings)
    as dims 10-49 for richer representation.
    """
    spend_by_group = defaultdict(float)
    total_spend = 0.0

    for order in orders:
        for item in order.get("items", []):
            price = item.get("price", 0) * item.get("quantity", 1)
            cat = item.get("category", "other")
            group = categorise(cat)
            spend_by_group[group] += price
            total_spend += price

    if total_spend == 0:
        total_spend = 1.0  # avoid div by zero

    # Occasion diversity
    occasion_types_seen = set()
    for occ in occasions:
        occasion_types_seen.add(occ.get("occasion_type", "general"))
    occ_diversity = min(len(occasion_types_seen) / 8.0, 1.0)

    # Order frequency: orders per month over data window (assume ~12 months)
    n_orders = len(orders)
    order_freq = min(n_orders / (12.0 * 4), 1.0)  # normalise: 48 orders/yr = 1.0

    # Budget tier
    budget = user.get("monthly_grocery_budget", 5000)
    budget_tier = min(budget / 15000.0, 1.0)

    # Household size
    hhsize = user.get("household_size", 3)
    hhsize_norm = min(hhsize / 6.0, 1.0)

    # is_prime
    is_prime = 1.0 if user.get("amazon_prime", False) else 0.0

    vec = np.array([
        spend_by_group["grocery"] / total_spend,
        spend_by_group["party"] / total_spend,
        spend_by_group["home"] / total_spend,
        spend_by_group["personal_care"] / total_spend,
        spend_by_group["travel"] / total_spend,
        occ_diversity,
        budget_tier,
        order_freq,
        hhsize_norm,
        is_prime,
    ], dtype=float)
    return vec


# ── Cluster naming ────────────────────────────────────────────────────────────
CLUSTER_NAMES = {
    "celebration_circle": {
        "name": "The Celebration Circle",
        "tagline": "They plan every occasion like a pro",
        "emoji": "🎉",
        "color": "#FF6B6B",
    },
    "home_builders": {
        "name": "The Home Builders",
        "tagline": "Nesting, optimising, building comfort",
        "emoji": "🏠",
        "color": "#4ECDC4",
    },
    "weekend_adventurers": {
        "name": "The Weekend Adventurers",
        "tagline": "Always ready for the next trip",
        "emoji": "🏔️",
        "color": "#45B7D1",
    },
    "daily_essentials": {
        "name": "The Daily Essentials",
        "tagline": "Never run out of anything",
        "emoji": "🛒",
        "color": "#96CEB4",
    },
    "urban_planners": {
        "name": "The Urban Planners",
        "tagline": "High budget, high expectations",
        "emoji": "🏙️",
        "color": "#FFEAA7",
    },
    "family_first": {
        "name": "The Family First",
        "tagline": "Large families, diverse needs",
        "emoji": "👨‍👩‍👧‍👦",
        "color": "#DDA0DD",
    },
}


def assign_cluster_name(centroid: np.ndarray, cluster_idx: int) -> str:
    """
    Map centroid to a meaningful cluster name based on dominant feature.

    centroid dims:
      0: grocery, 1: party, 2: home, 3: personal_care, 4: travel,
      5: occ_diversity, 6: budget_tier, 7: order_freq, 8: hhsize, 9: is_prime
    """
    grocery, party, home, personal_care, travel = centroid[:5]
    occ_div, budget, order_freq, hhsize, is_prime = centroid[5:]

    # Score each archetype
    scores = {
        "celebration_circle": party * 2 + occ_div * 1.5,
        "home_builders":      home * 2 + (1 - occ_div),
        "weekend_adventurers": travel * 2 + (1 - hhsize),
        "daily_essentials":   grocery * 2 + order_freq * 1.5,
        "urban_planners":     budget * 2 + is_prime,
        "family_first":       hhsize * 2 + occ_div,
    }
    return max(scores, key=scores.get)


# ── Co-occurrence matrix ──────────────────────────────────────────────────────
def build_cooccurrence(sessions: list) -> dict:
    """
    For each occasion_type, build co-purchase matrix.

    co_matrix[occasion][asin_a][asin_b] = count of sessions containing both.
    Normalized to confidence: P(B | A) = count(A,B) / count(A).

    Scale note: At 10M sessions, use implicit ALS (Spark MLlib) for matrix
    factorization. Store item factors as 64-dim vectors in Redis with FAISS
    index for nearest-neighbor co-purchase retrieval in < 5ms.
    """
    # occasion -> list of item sets
    occasion_item_sets = defaultdict(list)
    occasion_item_counts = defaultdict(lambda: defaultdict(int))
    occasion_total = defaultdict(int)

    for session in sessions:
        occ = session.get("occasion_type", "general")
        items = session.get("items_purchased", [])
        asins = [i["asin"] for i in items if "asin" in i]
        categories = [i["category"] for i in items if "category" in i]

        occasion_item_sets[occ].append(asins)
        occasion_total[occ] += 1

        for asin in asins:
            occasion_item_counts[occ][asin] += 1

    # Build co-occurrence
    cooccurrence = {}
    for occ, item_sets in occasion_item_sets.items():
        pair_counts = defaultdict(lambda: defaultdict(int))
        item_counts = occasion_item_counts[occ]
        total = occasion_total[occ]

        for basket in item_sets:
            for i, a in enumerate(basket):
                for b in basket:
                    if a != b:
                        pair_counts[a][b] += 1

        # Compute confidence scores and top co-items
        occ_matrix = {}
        for asin, co_items in pair_counts.items():
            count_a = item_counts.get(asin, 1)
            top_co = sorted(co_items.items(), key=lambda x: -x[1])[:10]
            occ_matrix[asin] = {
                "frequency": count_a,
                "frequency_rate": round(count_a / total, 3),
                "co_asins": [
                    {
                        "asin": co_asin,
                        "count": cnt,
                        "confidence": round(cnt / count_a, 3),
                    }
                    for co_asin, cnt in top_co
                ],
            }
        cooccurrence[occ] = occ_matrix

    return cooccurrence


# ── Coverage gaps ─────────────────────────────────────────────────────────────
def build_coverage_gaps(sessions: list, catalog: list) -> dict:
    """
    For each occasion_type, identify categories that frequently appear in
    completed missions with high outcome_rating but have low coverage —
    meaning most sessions that should include them don't.

    Scale note: At production scale, track coverage gaps as a streaming
    metric via Kafka + Flink. Emit a "gap alert" event when coverage for a
    category drops below 40% in a sliding 7-day window.
    """
    catalog_by_asin = {p["asin"]: p for p in catalog}

    # Get all categories per occasion from high-rating sessions
    occ_category_presence = defaultdict(lambda: defaultdict(int))
    occ_category_sessions = defaultdict(lambda: defaultdict(int))
    occ_totals = defaultdict(int)

    for session in sessions:
        occ = session.get("occasion_type", "general")
        items = session.get("items_purchased", [])
        occ_totals[occ] += 1

        cats_in_session = set(i["category"] for i in items if "category" in i)
        for cat in cats_in_session:
            occ_category_presence[occ][cat] += 1

    # For each occasion, find categories bought in 20-80% of sessions (mid-coverage = gap opportunity)
    gaps = {}
    for occ, cat_counts in occ_category_presence.items():
        total = occ_totals[occ]
        gap_list = []
        for cat, count in cat_counts.items():
            coverage = count / total
            if 0.15 <= coverage <= 0.80:  # bought sometimes but not always = gap
                # Find representative product for this category
                rep_product = None
                for p in catalog:
                    if p.get("category") == cat:
                        rep_product = p
                        break
                gap_list.append({
                    "category": cat,
                    "coverage_rate": round(coverage, 3),
                    "miss_rate": round(1 - coverage, 3),
                    "sessions_with": count,
                    "sessions_total": total,
                    "sample_asin": rep_product["asin"] if rep_product else None,
                    "sample_title": rep_product["title"] if rep_product else cat,
                })
        # Sort by miss_rate descending (biggest gaps first)
        gap_list.sort(key=lambda x: -x["miss_rate"])
        gaps[occ] = gap_list[:8]  # top 8 gaps per occasion

    return gaps


# ── Per-city trending ─────────────────────────────────────────────────────────
def build_city_trends(sessions: list) -> dict:
    """
    Count occasions per city, identify trending occasion_type.

    Scale note: At production scale, compute via a Redis INCR per
    city:occasion key, expiring at midnight. Serve via read-through cache.
    """
    city_occ_counts = defaultdict(lambda: defaultdict(int))
    for session in sessions:
        city = session.get("city", "Unknown")
        occ = session.get("occasion_type", "general")
        city_occ_counts[city][occ] += 1

    trends = {}
    for city, occ_counts in city_occ_counts.items():
        sorted_occs = sorted(occ_counts.items(), key=lambda x: -x[1])
        trends[city] = {
            "top_occasion": sorted_occs[0][0] if sorted_occs else "general",
            "occasion_counts": dict(sorted_occs[:5]),
            "total_active": sum(occ_counts.values()),
        }
    return trends


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("Loading data...")

    with open(SIM / "users.json", encoding="utf-8") as f:
        users_list = json.load(f)
    users = {u["user_id"]: u for u in users_list}

    with open(SIM / "purchase_history.json", encoding="utf-8") as f:
        purchase_history = json.load(f)

    with open(SIM / "occasion_history.json", encoding="utf-8") as f:
        occasion_history = json.load(f)

    with open(SIM / "community_sessions.json", encoding="utf-8") as f:
        sessions_data = json.load(f)
    sessions = sessions_data["sessions"]

    with open(DATA / "catalog.json", encoding="utf-8") as f:
        catalog = json.load(f)

    print(f"  {len(users)} users, {len(sessions)} sessions, {len(catalog)} catalog items")

    # ── Step 1: Build user feature matrix ─────────────────────────────────────
    print("Building user feature vectors...")
    user_ids = list(users.keys())
    X_list = []
    for uid in user_ids:
        user = users[uid]
        orders = purchase_history.get(uid, [])
        occasions = occasion_history.get(uid, [])
        vec = build_user_vector(user, orders, occasions)
        X_list.append(vec)

    X = np.array(X_list, dtype=float)
    print(f"  Feature matrix shape: {X.shape}")

    # ── Step 2: K-Means clustering ────────────────────────────────────────────
    print("Running K-Means (k=6)...")
    K = 6
    labels, centroids = kmeans(X, k=K, max_iter=100, random_state=42)
    print(f"  Cluster sizes: {dict(zip(*np.unique(labels, return_counts=True)))}")

    # ── Step 3: Assign cluster names ──────────────────────────────────────────
    cluster_id_to_archetype = {}
    used_archetypes = {}
    for k_idx in range(K):
        archetype = assign_cluster_name(centroids[k_idx], k_idx)
        # Handle collisions: append cluster index if name already used
        if archetype in used_archetypes:
            # Fall back to second best
            scores = {}
            c = centroids[k_idx]
            grocery, party, home, personal_care, travel = c[:5]
            occ_div, budget, order_freq, hhsize, is_prime = c[5:]
            all_scores = {
                "celebration_circle": party * 2 + occ_div * 1.5,
                "home_builders":      home * 2 + (1 - occ_div),
                "weekend_adventurers": travel * 2 + (1 - hhsize),
                "daily_essentials":   grocery * 2 + order_freq * 1.5,
                "urban_planners":     budget * 2 + is_prime,
                "family_first":       hhsize * 2 + occ_div,
            }
            sorted_archetypes = sorted(all_scores.items(), key=lambda x: -x[1])
            for arch, _ in sorted_archetypes:
                if arch not in used_archetypes:
                    archetype = arch
                    break
        used_archetypes[archetype] = k_idx
        cluster_id_to_archetype[k_idx] = archetype

    print("  Cluster assignments:")
    for k_idx, arch in cluster_id_to_archetype.items():
        name = CLUSTER_NAMES[arch]["name"]
        members_in = [user_ids[i] for i in range(len(user_ids)) if labels[i] == k_idx]
        # Force U001 (Sneha) into celebration_circle
        if arch == "celebration_circle" or "U001" in members_in:
            pass
        print(f"    Cluster {k_idx} -> {name} ({len(members_in)} members)")

    # ── Step 3b: Force U001 into celebration_circle ───────────────────────────
    # Sneha (U001) is our demo user: home_chef + new_parent, 6 occasions/year,
    # Diwali + kids birthday history. She should be in The Celebration Circle.
    u001_idx = user_ids.index("U001")
    target_cluster = None
    for k_idx, arch in cluster_id_to_archetype.items():
        if arch == "celebration_circle":
            target_cluster = k_idx
            break
    if target_cluster is not None and labels[u001_idx] != target_cluster:
        print(f"  Overriding U001 cluster: {labels[u001_idx]} -> {target_cluster} (celebration_circle)")
        labels[u001_idx] = target_cluster

    # ── Step 4: Build cluster definitions ─────────────────────────────────────
    print("Building cluster definitions...")

    # Per-cluster: top categories from purchase_history
    cluster_category_spend = defaultdict(lambda: defaultdict(float))
    cluster_occasion_types = defaultdict(lambda: defaultdict(int))

    for i, uid in enumerate(user_ids):
        cluster = int(labels[i])
        orders = purchase_history.get(uid, [])
        occasions = occasion_history.get(uid, [])

        for order in orders:
            for item in order.get("items", []):
                cat = item.get("category", "other")
                spend = item.get("price", 0) * item.get("quantity", 1)
                cluster_category_spend[cluster][cat] += spend

        for occ in occasions:
            occ_type = occ.get("occasion_type", "general")
            cluster_occasion_types[cluster][occ_type] += 1

    # Per-cluster top products (by category spend)
    cluster_top_categories = {}
    for cluster, cat_spend in cluster_category_spend.items():
        sorted_cats = sorted(cat_spend.items(), key=lambda x: -x[1])[:6]
        cluster_top_categories[cluster] = [
            {"category": cat, "total_spend": round(spend, 2)}
            for cat, spend in sorted_cats
        ]

    # Per-cluster top occasion
    cluster_top_occasion = {}
    for cluster, occ_counts in cluster_occasion_types.items():
        if occ_counts:
            cluster_top_occasion[cluster] = max(occ_counts.items(), key=lambda x: x[1])[0]
        else:
            cluster_top_occasion[cluster] = "general"

    # Build groups JSON
    community_groups = []
    for k_idx in range(K):
        archetype = cluster_id_to_archetype[k_idx]
        arch_info = CLUSTER_NAMES[archetype]
        members = [user_ids[i] for i in range(len(user_ids)) if labels[i] == k_idx]

        # Random but seeded activity count (simulates live shoppers)
        rng = random.Random(k_idx * 7 + 13)
        active_now = rng.randint(8, 45)

        group = {
            "group_id": f"grp_{archetype}",
            "group_name": arch_info["name"],
            "archetype": archetype,
            "tagline": arch_info["tagline"],
            "emoji": arch_info["emoji"],
            "color": arch_info["color"],
            "member_count": len(members),
            "members": members,
            "active_now": active_now,
            "top_categories": cluster_top_categories.get(k_idx, []),
            "top_occasion": cluster_top_occasion.get(k_idx, "general"),
            "centroid": centroids[k_idx].tolist(),
        }
        community_groups.append(group)

    # ── Step 5: Co-occurrence matrix ──────────────────────────────────────────
    print("Building co-purchase matrix from community sessions...")
    cooccurrence = build_cooccurrence(sessions)
    total_pairs = sum(len(v) for v in cooccurrence.values())
    print(f"  Co-occurrence pairs: {total_pairs}")

    # ── Step 6: Coverage gaps ─────────────────────────────────────────────────
    print("Computing coverage gaps...")
    coverage_gaps = build_coverage_gaps(sessions, catalog)

    # ── Step 7: City trends ───────────────────────────────────────────────────
    print("Computing city trends...")
    city_trends = build_city_trends(sessions)

    # ── Step 8: Community insights per cluster + per occasion ─────────────────
    print("Building community insights...")

    # Per-occasion stats from community_sessions
    occ_stats = defaultdict(lambda: {
        "total_sessions": 0,
        "completed": 0,
        "total_spend": 0.0,
        "total_headcount": 0,
        "total_budget": 0.0,
        "ratings": [],
        "category_presence": defaultdict(int),
        "city_counts": defaultdict(int),
    })

    for session in sessions:
        occ = session.get("occasion_type", "general")
        st = occ_stats[occ]
        st["total_sessions"] += 1
        if session.get("completed_mission"):
            st["completed"] += 1
        st["total_spend"] += session.get("total_spent", 0)
        st["total_headcount"] += session.get("headcount", 0)
        st["total_budget"] += session.get("budget_max", 0)
        if session.get("outcome_rating"):
            st["ratings"].append(session["outcome_rating"])
        st["city_counts"][session.get("city", "Unknown")] += 1
        for item in session.get("items_purchased", []):
            cat = item.get("category", "other")
            st["category_presence"][cat] += 1

    # Build catalog lookup
    catalog_by_cat = defaultdict(list)
    for p in catalog:
        catalog_by_cat[p["category"]].append(p)

    occasion_insights = {}
    for occ, st in occ_stats.items():
        total = st["total_sessions"]
        avg_spend = st["total_spend"] / total if total else 0
        avg_headcount = st["total_headcount"] / total if total else 0
        avg_budget = st["total_budget"] / total if total else 0
        success_rate = st["completed"] / total if total else 0
        avg_rating = sum(st["ratings"]) / len(st["ratings"]) if st["ratings"] else 0

        # Top categories by presence rate
        top_cats = sorted(
            st["category_presence"].items(),
            key=lambda x: -x[1]
        )[:10]
        top_items_with_product = []
        for cat, count in top_cats:
            products = catalog_by_cat.get(cat, [])
            best = products[0] if products else None
            top_items_with_product.append({
                "category": cat,
                "adoption_rate": round(count / total, 3),
                "asin": best["asin"] if best else None,
                "title": best["title"] if best else cat,
                "price": best["price"] if best else None,
            })

        # Top city
        top_city = max(st["city_counts"].items(), key=lambda x: x[1])[0] if st["city_counts"] else "Bangalore"

        occasion_insights[occ] = {
            "occasion_type": occ,
            "sessions_analyzed": total,
            "success_rate": round(success_rate, 3),
            "avg_spend": round(avg_spend, 2),
            "avg_headcount": round(avg_headcount, 1),
            "avg_budget": round(avg_budget, 2),
            "avg_rating": round(avg_rating, 2),
            "top_items": top_items_with_product,
            "top_city": top_city,
            "city_distribution": dict(st["city_counts"]),
            "coverage_gaps": coverage_gaps.get(occ, []),
        }

    community_insights = {
        "clusters": {
            f"grp_{cluster_id_to_archetype[k_idx]}": {
                "group_id": f"grp_{cluster_id_to_archetype[k_idx]}",
                "top_categories": cluster_top_categories.get(k_idx, []),
                "top_occasion": cluster_top_occasion.get(k_idx, "general"),
                "member_count": len([
                    uid for i, uid in enumerate(user_ids) if labels[i] == k_idx
                ]),
            }
            for k_idx in range(K)
        },
        "occasions": occasion_insights,
        "city_trends": city_trends,
        "coverage_gaps": coverage_gaps,
        "generated_at": "2026-06-23T00:00:00",
    }

    # ── Step 9: User → cluster map ────────────────────────────────────────────
    user_cluster_map = {}
    for i, uid in enumerate(user_ids):
        k_idx = int(labels[i])
        user_cluster_map[uid] = {
            "cluster_id": f"grp_{cluster_id_to_archetype[k_idx]}",
            "cluster_name": CLUSTER_NAMES[cluster_id_to_archetype[k_idx]]["name"],
            "archetype": cluster_id_to_archetype[k_idx],
        }

    # ── Step 10: Write output files ───────────────────────────────────────────
    print("Writing output files...")

    out_groups = DATA / "community_groups.json"
    with open(out_groups, "w", encoding="utf-8") as f:
        json.dump(community_groups, f, indent=2)
    print(f"  Written: {out_groups}")

    out_cluster_map = DATA / "user_cluster_map.json"
    with open(out_cluster_map, "w", encoding="utf-8") as f:
        json.dump(user_cluster_map, f, indent=2)
    print(f"  Written: {out_cluster_map}")

    out_cooccurrence = DATA / "occasion_cooccurrence.json"
    with open(out_cooccurrence, "w", encoding="utf-8") as f:
        json.dump(cooccurrence, f, indent=2)
    print(f"  Written: {out_cooccurrence}")

    out_insights = DATA / "community_insights.json"
    with open(out_insights, "w", encoding="utf-8") as f:
        json.dump(community_insights, f, indent=2)
    print(f"  Written: {out_insights}")

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n=== Summary ===")
    for group in community_groups:
        print(f"  {group['group_name']}: {group['member_count']} members")

    u001_cluster = user_cluster_map.get("U001", {})
    print(f"\n  U001 (Sneha) -> {u001_cluster.get('cluster_name')} ({u001_cluster.get('cluster_id')})")
    print("\nDone.")


if __name__ == "__main__":
    main()
