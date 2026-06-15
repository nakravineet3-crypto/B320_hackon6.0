"""
Retrieval engine for MissionCart.
Uses BLaIR (hyp1231/blair-roberta-large) for semantic product retrieval
and community intelligence scoring.
"""

import json
import math
from pathlib import Path
from typing import List, Dict, Optional


# Community priors — hardcoded for demo, would be computed from real sessions
COMMUNITY_PRIORS = {
    "plates": {
        "adoption_rate": 0.94,
        "sessions_total": 3847,
        "median_quantity_per_person": 2.1,
        "evidence_source": "demo_community_priors",
        "is_computed_from_raw_sessions": False,
    },
    "cups": {
        "adoption_rate": 0.91,
        "sessions_total": 3847,
        "median_quantity_per_person": 2.5,
        "evidence_source": "demo_community_priors",
        "is_computed_from_raw_sessions": False,
    },
    "napkins": {
        "adoption_rate": 0.87,
        "sessions_total": 3847,
        "median_quantity_per_person": 3.0,
        "evidence_source": "demo_community_priors",
        "is_computed_from_raw_sessions": False,
    },
    "balloon_set": {
        "adoption_rate": 0.89,
        "sessions_total": 3847,
        "median_quantity_per_person": 3.0,
        "evidence_source": "demo_community_priors",
        "is_computed_from_raw_sessions": False,
    },
    "balloon_pump": {
        "adoption_rate": 0.85,
        "sessions_total": 3847,
        "median_quantity_per_person": 0.08,
        "evidence_source": "demo_community_priors",
        "is_computed_from_raw_sessions": False,
    },
    "candles": {
        "adoption_rate": 0.92,
        "sessions_total": 3847,
        "median_quantity_per_person": 0.08,
        "evidence_source": "demo_community_priors",
        "is_computed_from_raw_sessions": False,
    },
    "cake_knife": {
        "adoption_rate": 0.78,
        "sessions_total": 3847,
        "median_quantity_per_person": 0.08,
        "evidence_source": "demo_community_priors",
        "is_computed_from_raw_sessions": False,
    },
    "return_gifts": {
        "adoption_rate": 0.82,
        "sessions_total": 3847,
        "median_quantity_per_person": 1.05,
        "evidence_source": "demo_community_priors",
        "is_computed_from_raw_sessions": False,
    },
    "decorations": {
        "adoption_rate": 0.86,
        "sessions_total": 3847,
        "median_quantity_per_person": 0.5,
        "evidence_source": "demo_community_priors",
        "is_computed_from_raw_sessions": False,
    },
    "decoration_streamers": {
        "adoption_rate": 0.74,
        "sessions_total": 3847,
        "median_quantity_per_person": 0.25,
        "evidence_source": "demo_community_priors",
        "is_computed_from_raw_sessions": False,
    },
    "banner": {
        "adoption_rate": 0.80,
        "sessions_total": 3847,
        "median_quantity_per_person": 0.08,
        "evidence_source": "demo_community_priors",
        "is_computed_from_raw_sessions": False,
    },
    "trash_bags": {
        "adoption_rate": 0.68,
        "sessions_total": 3847,
        "median_quantity_per_person": 0.25,
        "evidence_source": "demo_community_priors",
        "is_computed_from_raw_sessions": False,
    },
    "party_games": {
        "adoption_rate": 0.61,
        "sessions_total": 3847,
        "median_quantity_per_person": 0.08,
        "evidence_source": "demo_community_priors",
        "is_computed_from_raw_sessions": False,
    },
    "disposable_cups": {
        "adoption_rate": 0.88,
        "sessions_total": 3847,
        "median_quantity_per_person": 2.5,
        "evidence_source": "demo_community_priors",
        "is_computed_from_raw_sessions": False,
    },
    "disposable_spoons": {
        "adoption_rate": 0.72,
        "sessions_total": 3847,
        "median_quantity_per_person": 2.0,
        "evidence_source": "demo_community_priors",
        "is_computed_from_raw_sessions": False,
    },
    "tablecloth": {
        "adoption_rate": 0.65,
        "sessions_total": 3847,
        "median_quantity_per_person": 0.125,
        "evidence_source": "demo_community_priors",
        "is_computed_from_raw_sessions": False,
    },
    "tissue_pack": {
        "adoption_rate": 0.70,
        "sessions_total": 3847,
        "median_quantity_per_person": 1.5,
        "evidence_source": "demo_community_priors",
        "is_computed_from_raw_sessions": False,
    },
    # Home setup categories
    "mattress": {
        "adoption_rate": 0.95,
        "sessions_total": 2104,
        "median_quantity_per_person": 1.0,
        "evidence_source": "demo_community_priors",
        "is_computed_from_raw_sessions": False,
    },
    "bedsheet": {
        "adoption_rate": 0.93,
        "sessions_total": 2104,
        "median_quantity_per_person": 2.0,
        "evidence_source": "demo_community_priors",
        "is_computed_from_raw_sessions": False,
    },
    "pillow": {
        "adoption_rate": 0.91,
        "sessions_total": 2104,
        "median_quantity_per_person": 2.0,
        "evidence_source": "demo_community_priors",
        "is_computed_from_raw_sessions": False,
    },
    "towels": {
        "adoption_rate": 0.88,
        "sessions_total": 2104,
        "median_quantity_per_person": 1.0,
        "evidence_source": "demo_community_priors",
        "is_computed_from_raw_sessions": False,
    },
    "led_bulb": {
        "adoption_rate": 0.85,
        "sessions_total": 2104,
        "median_quantity_per_person": 4.0,
        "evidence_source": "demo_community_priors",
        "is_computed_from_raw_sessions": False,
    },
    "extension_board": {
        "adoption_rate": 0.82,
        "sessions_total": 2104,
        "median_quantity_per_person": 2.0,
        "evidence_source": "demo_community_priors",
        "is_computed_from_raw_sessions": False,
    },
}

# Default prior for categories not in the lookup
DEFAULT_PRIOR = {
    "adoption_rate": 0.75,
    "sessions_total": 1500,
    "median_quantity_per_person": 1.0,
    "evidence_source": "demo_community_priors",
    "is_computed_from_raw_sessions": False,
}


class BlairEncoder:
    """
    Correct BLaIR encoding per hyp1231/blair-roberta-large.
    CLS token pooling + L2 normalization.
    """

    def __init__(self):
        model_name = "hyp1231/blair-roberta-large"
        from transformers import AutoTokenizer, AutoModel
        import torch

        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)
        self.model.eval()
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = self.model.to(self.device)
        self._torch = torch

    def encode(self, texts: list, batch_size: int = 32):
        import numpy as np

        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            encoded = self.tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt",
            )
            encoded = {k: v.to(self.device) for k, v in encoded.items()}

            with self._torch.no_grad():
                out = self.model(**encoded)
                cls = out.last_hidden_state[:, 0, :]
                cls = self._torch.nn.functional.normalize(cls, p=2, dim=-1)
                all_embeddings.append(cls.cpu().numpy())

        return np.vstack(all_embeddings)


def _add_community(product: dict, headcount: int = 1, occasion_type: str = "event") -> dict:
    """
    Enrich a product dict with community intelligence fields.
    Uses community priors from session analysis.
    """
    category = product.get("category", "")
    cat = COMMUNITY_PRIORS.get(category, DEFAULT_PRIOR)

    adoption = cat["adoption_rate"]
    total = cat["sessions_total"]
    median_per_person = cat["median_quantity_per_person"]

    # Compute quantity basis string
    if median_per_person >= 1.0:
        quantity_basis = (
            f"median {median_per_person:.1f} per person × {headcount} guests "
            f"across {total:,} occasions"
        )
    else:
        quantity_basis = f"based on {total:,} similar {occasion_type} occasions"

    product.update({
        "community_adoption_score": adoption,
        "sessions_analyzed": total,
        "quantity_basis": quantity_basis,
        "evidence_source": cat.get("evidence_source", "demo_community_priors"),
        "is_computed_from_raw_sessions": cat.get("is_computed_from_raw_sessions", False),
    })

    return product


class RetrievalEngine:
    """
    Retrieval engine with FAISS semantic search and community enrichment.
    Loads pre-built FAISS index + catalog at init.
    Query encoding: averages embeddings of category exemplars (no runtime model needed).
    """

    def __init__(self):
        self._encoder = None
        self.index = None
        self.catalog = []
        self._category_centroids = {}
        self._load()

    def _load(self):
        """Load FAISS index and embedded catalog."""
        data_path = Path(__file__).parent.parent / "data"
        try:
            import faiss
            import numpy as np

            # Load FAISS index
            index_path = data_path / "product_faiss.index"
            if index_path.exists():
                self.index = faiss.read_index(str(index_path))
                print(f"FAISS index loaded: {self.index.ntotal} products, dim={self.index.d}")

            # Load embedded catalog
            catalog_path = data_path / "catalog_embedded.json"
            if catalog_path.exists():
                with open(catalog_path, encoding="utf-8") as f:
                    self.catalog = json.load(f)

            # Pre-compute category centroids from FAISS vectors
            if self.index and self.catalog:
                self._build_category_centroids(np)

        except ImportError as e:
            print(f"FAISS/numpy not available: {e}. Using keyword fallback.")
        except Exception as e:
            print(f"FAISS load failed: {e}. Using keyword fallback.")

    def _build_category_centroids(self, np):
        """Pre-compute average embedding per category for query-free retrieval."""
        category_indices = {}
        for i, product in enumerate(self.catalog):
            cat = product.get("category", "")
            if cat not in category_indices:
                category_indices[cat] = []
            category_indices[cat].append(i)

        for cat, indices in category_indices.items():
            if indices:
                vectors = []
                for idx in indices:
                    vec = self.index.reconstruct(idx)
                    vectors.append(vec)
                centroid = np.mean(vectors, axis=0).astype("float32")
                # L2 normalize
                norm = np.linalg.norm(centroid)
                if norm > 0:
                    centroid = centroid / norm
                self._category_centroids[cat] = centroid

    def retrieve(
        self,
        need_label: str,
        category_candidates: List[str],
        occasion_type: str = "event",
        budget_ceiling: float = 5000,
        headcount: int = 1,
        top_k: int = 15,
    ) -> List[dict]:
        """Retrieve products using FAISS semantic search.

        If FAISS loaded: uses category centroid vectors for nearest-neighbor search.
        If not: falls back to keyword category matching.
        """
        if self.index and self._category_centroids:
            return self._faiss_retrieve(
                category_candidates, budget_ceiling, top_k
            )
        return self._keyword_retrieve(
            category_candidates, budget_ceiling
        )

    def _faiss_retrieve(
        self,
        category_candidates: List[str],
        budget_ceiling: float,
        top_k: int,
    ) -> List[dict]:
        """FAISS-based retrieval using pre-computed category centroids."""
        import numpy as np

        # Build query vector: average of target category centroids
        query_vectors = []
        for cat in category_candidates:
            if cat in self._category_centroids:
                query_vectors.append(self._category_centroids[cat])

        if not query_vectors:
            return self._keyword_retrieve(category_candidates, budget_ceiling)

        query = np.mean(query_vectors, axis=0).astype("float32").reshape(1, -1)
        # Normalize for cosine similarity
        norm = np.linalg.norm(query)
        if norm > 0:
            query = query / norm

        # Search FAISS
        distances, indices = self.index.search(query, min(top_k * 3, self.index.ntotal))

        # Filter and score results
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(self.catalog):
                continue
            product = dict(self.catalog[idx])
            # Filter by category and budget
            if product.get("category") not in category_candidates:
                continue
            if product.get("price", 0) > budget_ceiling:
                continue
            if not product.get("stock_available", True):
                continue
            product["retrieval_score"] = float(1.0 / (1.0 + dist))
            product["retrieval_method"] = "blair_faiss"
            results.append(product)

        return results[:top_k]

    def _keyword_retrieve(
        self,
        category_candidates: List[str],
        budget_ceiling: float,
    ) -> List[dict]:
        """Fallback: simple category + price filter."""
        results = []
        for product in self.catalog:
            if product.get("category") in category_candidates:
                if product.get("price", 0) <= budget_ceiling:
                    if product.get("stock_available", True):
                        product_copy = dict(product)
                        product_copy["retrieval_score"] = 0.5
                        product_copy["retrieval_method"] = "keyword_category"
                        results.append(product_copy)
        return results

    @property
    def encoder(self):
        if self._encoder is None:
            self._encoder = BlairEncoder()
        return self._encoder

    def _add_community(self, product: dict, headcount: int = 1, occasion_type: str = "event") -> dict:
        return _add_community(product, headcount=headcount, occasion_type=occasion_type)

    def encode(self, texts: list, batch_size: int = 32):
        return self.encoder.encode(texts, batch_size=batch_size)


# Module-level singleton used across the app
retrieval_engine = RetrievalEngine()


def enrich_cart_with_community(cart_items: List[dict], headcount: int = 1, occasion_type: str = "event") -> List[dict]:
    """Enrich all cart items with community intelligence data."""
    return [_add_community(item, headcount, occasion_type) for item in cart_items]
