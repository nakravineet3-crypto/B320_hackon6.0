"""
build_identity_data.py
======================
Computes cluster_product_affinities.json and identity_normalization_params.json
from purchase_history.json and user_cluster_map.json.

Run:
    python scripts/build_identity_data.py

Output files (written to backend/app/data/):
    cluster_product_affinities.json  -- top-20 lift products per cluster
    identity_normalization_params.json -- feature dimension names + per-dim max values

Lift formula:
    cluster_adoption(product, cluster) = buyers_in_cluster / cluster_size
    global_adoption(product)           = total_buyers / total_users
    lift                               = cluster_adoption / global_adoption

Laplace smoothing applied for clusters with size < 5:
    cluster_adoption_smoothed = (buyers_in_cluster + 1) / (cluster_size + 2)

Compatible with BOTH old data (grp_* prefix, 10-dim centroids) and new data
(bare cluster IDs like office_gym_dad, 4-6 dim centroids).
"""

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
BACKEND_DIR = Path(__file__).parent.parent
DATA_DIR    = BACKEND_DIR / "app" / "data"
SIM_DIR     = DATA_DIR / "simulated"

PURCHASE_HISTORY_PATH = SIM_DIR / "purchase_history.json"
USER_CLUSTER_MAP_PATH = DATA_DIR / "user_cluster_map.json"
COMMUNITY_GROUPS_PATH = DATA_DIR / "community_groups.json"
CATALOG_PATH          = DATA_DIR / "catalog.json"

AFFINITIES_OUT  = DATA_DIR / "cluster_product_affinities.json"
NORM_PARAMS_OUT = DATA_DIR / "identity_normalization_params.json"

# ── Cluster human-readable names for adoption_copy generation ─────────────────
# Covers both old grp_* format and new bare-ID format
CLUSTER_DISPLAY_NAMES = {
    # New 4-group format (no prefix)
    "office_gym_dad":  "Office Gym Dads",
    "jee_student":     "JEE Students",
    "college_girl":    "College Girls",
    "home_chef":       "Home Chefs",
    # Old 6-group format (grp_ prefix)
    "grp_family_first":        "Family First members",
    "grp_weekend_adventurers": "Weekend Adventurers",
    "grp_home_builders":       "Home Builders",
    "grp_celebration_circle":  "Celebration Circle members",
    "grp_daily_essentials":    "Daily Essentials members",
    "grp_urban_planners":      "Urban Planners",
}


def load_json(path: Path) -> dict | list:
    # utf-8-sig handles files saved with BOM (common on Windows)
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def build_affinities(
    purchase_history: dict,
    user_cluster_map: dict,
    community_groups: list[dict],
    catalog: list[dict],
) -> tuple[dict, dict]:
    """
    Returns:
        affinities: {cluster_id: [affinity_record, ...]}  sorted by lift desc, top 20
        norm_params: documentation of centroid dimensions
    """

    # ── Detect cluster ID field name (group_id or id) ─────────────────────────
    id_field = "group_id" if "group_id" in community_groups[0] else "id"

    # ── Build cluster membership from user_cluster_map ────────────────────────
    cluster_members: dict[str, list[str]] = defaultdict(list)
    for user_id, info in user_cluster_map.items():
        cid = info.get("cluster_id") or info.get("group_id") or info.get("cluster", "")
        if cid:
            cluster_members[cid].append(user_id)

    cluster_sizes: dict[str, int] = {
        cid: len(members) for cid, members in cluster_members.items()
    }
    total_users = len(user_cluster_map)

    print(f"  Cluster sizes: {dict(cluster_sizes)}")
    print(f"  Total users: {total_users}")

    # ── Build buyer sets per ASIN ─────────────────────────────────────────────
    global_buyers: dict[str, set[str]] = defaultdict(set)
    cluster_buyers: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))

    for user_id, orders in purchase_history.items():
        info = user_cluster_map.get(user_id, {})
        cluster_id = info.get("cluster_id") or info.get("group_id") or info.get("cluster", "")
        for order in orders:
            for item in order.get("items", []):
                asin = item.get("asin", "")
                if asin:
                    global_buyers[asin].add(user_id)
                    if cluster_id:
                        cluster_buyers[cluster_id][asin].add(user_id)

    print(f"  Unique ASINs purchased: {len(global_buyers)}")

    # ── Catalog lookup -- exclude sponsored products ───────────────────────────
    # Purchase history and catalog may use different ASIN namespaces.
    # We build affinities for ALL purchased ASINs; only skip catalog-known sponsored ones.
    sponsored_asins = {p["asin"] for p in catalog if p.get("sponsored", False)}
    catalog_by_asin = {p["asin"]: p for p in catalog}
    print(f"  Catalog ASINs: {len(catalog_by_asin)}, sponsored: {len(sponsored_asins)}")

    # ── Compute lift per (cluster, asin) ──────────────────────────────────────
    affinities: dict[str, list[dict]] = {}

    for group in community_groups:
        cluster_id         = group[id_field]
        cluster_size       = cluster_sizes.get(cluster_id, 0)
        display_name       = CLUSTER_DISPLAY_NAMES.get(cluster_id, group.get("group_name", cluster_id))
        small_cluster      = cluster_size < 5
        min_buyers_needed  = 1 if cluster_size < 3 else 2

        if cluster_size == 0:
            print(f"  WARNING: {cluster_id} has 0 members in user_cluster_map -- skipping")
            affinities[cluster_id] = []
            continue

        records: list[dict] = []

        for asin, global_buyer_set in global_buyers.items():
            if asin in sponsored_asins:
                continue

            buyers_in_cluster  = len(cluster_buyers[cluster_id].get(asin, set()))
            global_buyer_count = len(global_buyer_set)

            if buyers_in_cluster < min_buyers_needed:
                continue

            # Laplace smoothing for small clusters
            if small_cluster:
                cluster_adoption = (buyers_in_cluster + 1) / (cluster_size + 2)
            else:
                cluster_adoption = buyers_in_cluster / cluster_size

            global_adoption = global_buyer_count / total_users
            lift = cluster_adoption / max(global_adoption, 0.01)

            if lift < 1.2:
                continue

            adoption_pct = round(cluster_adoption * 100)

            # Honesty rules: suppress % for tiny clusters
            if cluster_size < 3:
                adoption_copy = "Trending in this community"
            elif cluster_size < 10:
                adoption_copy = f"{adoption_pct}% of {display_name} buy this"
            else:
                adoption_copy = f"{adoption_pct}% of {display_name} (n={cluster_size})"

            records.append({
                "asin":          asin,
                "lift":          round(lift, 3),
                "adoption_rate": round(cluster_adoption, 4),
                "buyer_count":   buyers_in_cluster,
                "adoption_copy": adoption_copy,
            })

        records.sort(key=lambda x: x["lift"], reverse=True)
        affinities[cluster_id] = records[:20]

    # ── Build norm_params ─────────────────────────────────────────────────────
    sample_centroid = community_groups[0].get("centroid", []) if community_groups else []
    n_dims = len(sample_centroid)

    if n_dims == 6:
        feature_names = [
            "office_tech_signal",
            "student_signal",
            "personal_care_signal",
            "cooking_signal",
            "lifestyle_variety",
            "premium_ratio",
        ]
    elif n_dims == 10:
        feature_names = [
            "dairy_frequency",
            "personal_care_frequency",
            "sporting_outdoor_frequency",
            "occasion_extras_frequency",
            "fitness_supplements_frequency",
            "premium_ratio",
            "occasion_diversity",
            "reorder_rate",
            "amazon_now_ratio",
            "family_pack_signal",
        ]
    else:
        feature_names = [f"dim_{i}" for i in range(n_dims)]

    norm_params = {
        "feature_order": feature_names,
        "centroid_dims":  n_dims,
        "max_values":     [1.0] * n_dims,
        "description": (
            f"{n_dims}-dimensional feature vector. "
            "Centroids are from community_groups.json. "
            "Use cosine similarity for cold-start cluster assignment."
        ),
    }

    return affinities, norm_params


def main():
    print("Loading data files...")
    purchase_history = load_json(PURCHASE_HISTORY_PATH)
    user_cluster_map = load_json(USER_CLUSTER_MAP_PATH)
    community_groups = load_json(COMMUNITY_GROUPS_PATH)
    catalog          = load_json(CATALOG_PATH)

    print(f"  {len(purchase_history)} users in purchase_history")
    print(f"  {len(user_cluster_map)} users in user_cluster_map")
    print(f"  {len(community_groups)} community groups")
    print(f"  {len(catalog)} catalog products")

    id_field = "group_id" if "group_id" in community_groups[0] else "id"
    group_ids = [g[id_field] for g in community_groups]
    print(f"  Group IDs: {group_ids}")
    centroid_dims = len(community_groups[0].get("centroid", []))
    print(f"  Centroid dimensionality: {centroid_dims}")

    print("\nComputing cluster product affinities (LIFT scores)...")
    affinities, norm_params = build_affinities(
        purchase_history, user_cluster_map, community_groups, catalog
    )

    # Write affinities
    with open(AFFINITIES_OUT, "w", encoding="utf-8") as f:
        json.dump(affinities, f, indent=2, ensure_ascii=False)
    print(f"\nWrote {AFFINITIES_OUT}")

    for cluster_id, records in affinities.items():
        print(f"  {cluster_id}: {len(records)} products with lift >= 1.2")
        if records:
            top = records[0]
            print(f"    Top: {top['asin']} lift={top['lift']} "
                  f"adoption={top['adoption_rate']} buyers={top['buyer_count']}")
            print(f"    Copy: \"{top['adoption_copy']}\"")

    # Write normalization params
    with open(NORM_PARAMS_OUT, "w", encoding="utf-8") as f:
        json.dump(norm_params, f, indent=2, ensure_ascii=False)
    print(f"\nWrote {NORM_PARAMS_OUT}")

    # Validate JSON round-trips
    with open(AFFINITIES_OUT, encoding="utf-8") as f:
        loaded = json.load(f)
    assert isinstance(loaded, dict), "affinities must be a dict"
    assert len(loaded) == len(community_groups), (
        f"Expected {len(community_groups)} cluster keys, got {len(loaded)}"
    )

    with open(NORM_PARAMS_OUT, encoding="utf-8") as f:
        loaded_params = json.load(f)
    assert "feature_order" in loaded_params
    assert len(loaded_params["feature_order"]) == centroid_dims

    print("\nValidation passed. Both output files are valid JSON.")
    print("Done.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"FATAL: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
