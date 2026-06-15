import json
from pathlib import Path
from typing import Optional
from collections import defaultdict

DATA_PATH = Path(__file__).parent.parent / "data"

TRUSTED_BRANDS = {
    "tata", "amul", "surf excel", "parle", "ariel",
    "colgate", "dettol", "wildcraft", "decathlon",
    "kent", "wipro", "havells", "philips", "bosch",
    "prestige", "bajaj", "milton", "cello", "tupperware",
    "himalaya", "dabur", "patanjali", "nestle", "britannia",
}

BADGE_COLORS = {
    "best_value":       {"bg": "#E7F5EA", "text": "#007600"},
    "most_popular":     {"bg": "#FFF8E1", "text": "#F57F17"},
    "top_rated":        {"bg": "#FFF8E1", "text": "#F57F17"},
    "instant_delivery": {"bg": "#E3F2FD", "text": "#1565C0"},
    "trusted_brand":    {"bg": "#F3E5F5", "text": "#6A1B9A"},
    "rarely_returned":  {"bg": "#E8F5E9", "text": "#2E7D32"},
    "amazon_now":       {"bg": "#E3F2FD", "text": "#1565C0"},
}


class BadgeEngine:
    def __init__(self):
        self.catalog = []
        self.session_adoption = {}
        self.category_price_rank = {}
        self._badges = {}
        self._load()

    def _load(self):
        # Load catalog
        cat_path = DATA_PATH / "catalog.json"
        if cat_path.exists():
            with open(cat_path, encoding="utf-8") as f:
                self.catalog = json.load(f)

        # Load community sessions for adoption rates
        sess_path = DATA_PATH / "simulated" / "community_sessions.json"
        if sess_path.exists():
            with open(sess_path, encoding="utf-8") as f:
                sessions_data = json.load(f)
            sessions = sessions_data.get("sessions", [])
            self._compute_adoption(sessions)

        # Compute price rankings per category
        self._compute_price_ranks()

        # Pre-compute badge for every product
        for product in self.catalog:
            asin = product.get("asin", "")
            if asin:
                self._badges[asin] = self._assign(product)

        print(f"BadgeEngine: {len(self._badges)} badges computed")

    def _compute_adoption(self, sessions: list):
        """Compute adoption_rate per category per occasion."""
        counts = defaultdict(lambda: defaultdict(int))
        totals = defaultdict(int)

        for session in sessions:
            occ = session.get("occasion_type", "general")
            totals[occ] += 1
            for item in session.get("items_purchased", []):
                cat = item.get("category", "")
                if cat:
                    counts[occ][cat] += 1

        for occ, cat_counts in counts.items():
            total = totals[occ]
            if total == 0:
                continue
            for cat, count in cat_counts.items():
                key = f"{occ}:{cat}"
                self.session_adoption[key] = round(count / total, 3)

    def _compute_price_ranks(self):
        """Rank products by price-per-unit within category (cheapest = rank 0)."""
        by_category = defaultdict(list)
        for p in self.catalog:
            cat = p.get("category", "")
            price = p.get("price", 999)
            pack = p.get("pack_size", 1)
            ppu = price / max(pack, 1)
            by_category[cat].append((ppu, p.get("asin", "")))

        for cat, items in by_category.items():
            items.sort(key=lambda x: x[0])
            for rank, (_, asin) in enumerate(items):
                self.category_price_rank[asin] = rank

    def _assign(self, product: dict) -> dict:
        """Assign ONE badge per product. Priority waterfall."""
        asin = product.get("asin", "")
        cat = product.get("category", "")
        title = product.get("title", "").lower()
        rating = product.get("rating", 0)
        return_risk = product.get("return_risk", 0.2)
        now = product.get("amazon_now_eligible", False)
        price = product.get("price", 0)
        pack = product.get("pack_size", 1)

        # Get adoption rate from session data
        adoption = max(
            self.session_adoption.get(f"kids_birthday:{cat}", 0),
            self.session_adoption.get(f"home_setup:{cat}", 0),
            self.session_adoption.get(f"travel_prep:{cat}", 0),
        )

        # RULE 1: BEST VALUE
        rank = self.category_price_rank.get(asin, 99)
        if rank == 0:
            return {
                "badge_type": "best_value",
                "badge_label": "Best value",
                "badge_reason": (
                    f"₹{price / max(pack, 1):.1f} per unit — "
                    f"lowest in this category"
                ),
                "colors": BADGE_COLORS["best_value"],
                "simulated_data": False,
            }

        # RULE 2: MOST POPULAR
        if adoption >= 0.85:
            return {
                "badge_type": "most_popular",
                "badge_label": "Most popular",
                "badge_reason": (
                    f"Chosen in {adoption:.0%} of similar "
                    f"occasions (simulation-based prior)"
                ),
                "colors": BADGE_COLORS["most_popular"],
                "simulated_data": True,
            }

        # RULE 3: TOP RATED
        if rating >= 4.4:
            return {
                "badge_type": "top_rated",
                "badge_label": "Top rated",
                "badge_reason": f"{rating}★ — among highest rated in this category",
                "colors": BADGE_COLORS["top_rated"],
                "simulated_data": False,
            }

        # RULE 4: INSTANT DELIVERY
        if now and product.get("delivery_eta") == "now_20min":
            return {
                "badge_type": "instant_delivery",
                "badge_label": "Now · 20 min",
                "badge_reason": "Available on Amazon Now — arrives in 20 minutes",
                "colors": BADGE_COLORS["instant_delivery"],
                "simulated_data": False,
            }

        # RULE 5: TRUSTED BRAND
        if any(b in title for b in TRUSTED_BRANDS):
            matched_brand = next(b for b in TRUSTED_BRANDS if b in title)
            return {
                "badge_type": "trusted_brand",
                "badge_label": "Trusted brand",
                "badge_reason": f"{matched_brand.title()} — established brand",
                "colors": BADGE_COLORS["trusted_brand"],
                "simulated_data": False,
            }

        # RULE 6: RARELY RETURNED
        if return_risk < 0.06:
            return {
                "badge_type": "rarely_returned",
                "badge_label": "Rarely returned",
                "badge_reason": (
                    f"Only {return_risk:.0%} return rate — customers keep this"
                ),
                "colors": BADGE_COLORS["rarely_returned"],
                "simulated_data": False,
            }

        # RULE 7: DEFAULT
        if now:
            return {
                "badge_type": "amazon_now",
                "badge_label": "Amazon Now",
                "badge_reason": "Available for instant delivery",
                "colors": BADGE_COLORS["amazon_now"],
                "simulated_data": False,
            }

        return {
            "badge_type": "amazon_now",
            "badge_label": "Prime",
            "badge_reason": "Prime eligible",
            "colors": BADGE_COLORS["amazon_now"],
            "simulated_data": False,
        }

    def get_badge(self, asin: str) -> dict:
        return self._badges.get(asin, {
            "badge_type": "amazon_now",
            "badge_label": "Prime",
            "badge_reason": "Prime eligible",
            "colors": BADGE_COLORS["amazon_now"],
            "simulated_data": False,
        })

    def get_products_with_badges(
        self, products: list, occasion_type: str = "general"
    ) -> list:
        """Add badge to each product dict."""
        result = []
        for p in products:
            p_copy = dict(p)
            asin = p.get("asin", "")
            badge = dict(self.get_badge(asin))

            # Override with occasion-specific adoption if available
            cat = p.get("category", "")
            occ_adoption = self.session_adoption.get(f"{occasion_type}:{cat}", 0)
            if occ_adoption >= 0.85 and badge["badge_type"] not in ["best_value"]:
                badge = {
                    "badge_type": "most_popular",
                    "badge_label": "Popular choice",
                    "badge_reason": (
                        f"In {occ_adoption:.0%} of "
                        f"{occasion_type.replace('_', ' ')} "
                        f"carts (simulation-based)"
                    ),
                    "colors": BADGE_COLORS["most_popular"],
                    "simulated_data": True,
                }

            p_copy["badge"] = badge
            result.append(p_copy)
        return result


# Singleton — computed once at startup
badge_engine = BadgeEngine()
