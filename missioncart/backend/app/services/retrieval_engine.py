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
    Retrieval engine wrapper exposing community enrichment and (lazy) BLaIR encoding.
    """

    def __init__(self):
        self._encoder: Optional[BlairEncoder] = None

    @property
    def encoder(self) -> BlairEncoder:
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
