"""
Rebuild MissionCart FAISS index after catalog update.

Run:
    python scripts/rebuild_faiss_index.py

Input:
    backend/app/data/catalog.json  (must exist — run build_amazon_catalog.py first)

Output:
    backend/app/data/product_faiss.index    (FAISS index — matches retrieval_engine.py)
    backend/app/data/catalog_embedded.json  (catalog copy with embedding position metadata)

Embedding model: hyp1231/blair-roberta-large
  - CLS token pooling + L2 normalisation (matches BlairEncoder in retrieval_engine.py)
  - Inner product index (cosine for unit-normalised vectors) = faiss.IndexFlatIP

Runtime estimate: ~10-30 min for 15,000 products on CPU; ~2 min on GPU.

The script is idempotent: rebuilding with the same catalog.json produces
a functionally identical index (deterministic encoder weights).
"""

import json
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths — must match retrieval_engine.py exactly
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).parent.resolve()
DATA_DIR = SCRIPT_DIR.parent / "app" / "data"

CATALOG_PATH = DATA_DIR / "catalog.json"
INDEX_PATH = DATA_DIR / "product_faiss.index"
EMBEDDED_CATALOG_PATH = DATA_DIR / "catalog_embedded.json"

BATCH_SIZE = 32          # Products per encoding batch
MAX_TEXT_LEN = 512       # Tokeniser truncation limit


# ---------------------------------------------------------------------------
# Corpus construction
# ---------------------------------------------------------------------------

def build_corpus(catalog: list[dict]) -> list[str]:
    """
    Build the text corpus fed to the encoder.
    Each string is: title + category + subcategory + brand + safety_tags
    This mirrors what the original build_faiss_index.py description says.
    """
    texts = []
    for p in catalog:
        parts = [
            p.get("title", ""),
            p.get("category", ""),
            p.get("subcategory", ""),
            p.get("brand", ""),
            " ".join(p.get("safety_tags", [])),
            " ".join(p.get("compatibility_tags", [])),
        ]
        text = " ".join(s for s in parts if s).strip()
        # Truncate very long strings to avoid tokeniser overhead
        texts.append(text[:400])
    return texts


# ---------------------------------------------------------------------------
# BLaIR encoder (mirrors BlairEncoder in retrieval_engine.py exactly)
# ---------------------------------------------------------------------------

def load_encoder():
    """Load hyp1231/blair-roberta-large. Returns (tokenizer, model, device)."""
    try:
        from transformers import AutoTokenizer, AutoModel
        import torch
    except ImportError:
        print("ERROR: Required packages not installed. Run:")
        print("  pip install transformers torch faiss-cpu numpy")
        sys.exit(1)

    model_name = "hyp1231/blair-roberta-large"
    print(f"Loading encoder: {model_name}")
    print("  (First run downloads ~1.3 GB model weights — cached after that)")

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)
    model.eval()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = model.to(device)
    print(f"  Device: {device}")
    return tokenizer, model, device


def encode_batch(
    texts: list[str],
    tokenizer,
    model,
    device: str,
) -> "np.ndarray":
    """
    CLS token pooling + L2 normalisation — mirrors BlairEncoder.encode().
    Returns float32 numpy array of shape (len(texts), hidden_dim).
    """
    import torch
    import numpy as np

    encoded = tokenizer(
        texts,
        padding=True,
        truncation=True,
        max_length=MAX_TEXT_LEN,
        return_tensors="pt",
    )
    encoded = {k: v.to(device) for k, v in encoded.items()}

    with torch.no_grad():
        out = model(**encoded)
        cls = out.last_hidden_state[:, 0, :]                # CLS token
        cls = torch.nn.functional.normalize(cls, p=2, dim=-1)  # L2 norm
        return cls.cpu().numpy().astype("float32")


def encode_all(
    corpus: list[str],
    tokenizer,
    model,
    device: str,
    batch_size: int = BATCH_SIZE,
) -> "np.ndarray":
    import numpy as np

    all_embeddings = []
    total = len(corpus)
    start = time.monotonic()

    for i in range(0, total, batch_size):
        batch = corpus[i: i + batch_size]
        embs = encode_batch(batch, tokenizer, model, device)
        all_embeddings.append(embs)

        done = min(i + batch_size, total)
        elapsed = time.monotonic() - start
        speed = done / elapsed if elapsed > 0 else 0
        eta = (total - done) / speed if speed > 0 else 0
        print(
            f"  {done:>6}/{total}  ({done / total * 100:.1f}%)  "
            f"{speed:.1f} products/s  ETA {eta:.0f}s",
            end="\r",
            flush=True,
        )

    print()
    return np.vstack(all_embeddings)


# ---------------------------------------------------------------------------
# FAISS index construction
# ---------------------------------------------------------------------------

def build_faiss_index(embeddings: "np.ndarray"):
    """
    Build an IndexFlatIP (inner product = cosine for unit vectors).
    Matches the index type expected by retrieval_engine.py:
      - self.index.reconstruct(idx) used for centroid building
      - index.search(query, k) used for retrieval
    IndexFlatIP supports reconstruct(), unlike IVF variants.
    """
    try:
        import faiss
    except ImportError:
        print("ERROR: faiss not installed. Run:  pip install faiss-cpu")
        sys.exit(1)

    dim = embeddings.shape[1]
    print(f"Building IndexFlatIP: {len(embeddings):,} vectors, dim={dim}")
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    print(f"  Index built: {index.ntotal} vectors")
    return index


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 60)
    print("MissionCart FAISS Index Rebuild")
    print("=" * 60)

    # Pre-flight
    if not CATALOG_PATH.exists():
        print(f"\nERROR: Catalog not found at {CATALOG_PATH}")
        print("Run:  python scripts/build_amazon_catalog.py  first.")
        sys.exit(1)

    # Load catalog
    print(f"\nLoading catalog: {CATALOG_PATH}")
    with open(CATALOG_PATH, encoding="utf-8") as f:
        catalog = json.load(f)
    print(f"  {len(catalog):,} products loaded")

    # Build text corpus
    corpus = build_corpus(catalog)
    print(f"  Corpus built: {len(corpus):,} texts")
    print(f"  Sample: {corpus[0][:80]!r}")

    # Load encoder
    print()
    tokenizer, model, device = load_encoder()

    # Encode
    print(f"\nEncoding {len(corpus):,} products in batches of {BATCH_SIZE}...")
    try:
        import numpy as np
    except ImportError:
        print("ERROR: numpy not installed. Run:  pip install numpy")
        sys.exit(1)

    t0 = time.monotonic()
    embeddings = encode_all(corpus, tokenizer, model, device)
    encode_time = time.monotonic() - t0
    print(f"Encoding complete in {encode_time:.1f}s  shape={embeddings.shape}")

    # Build FAISS index
    print()
    index = build_faiss_index(embeddings)

    # Write index
    try:
        import faiss
    except ImportError:
        print("ERROR: faiss not installed.")
        sys.exit(1)

    faiss.write_index(index, str(INDEX_PATH))
    print(f"  FAISS index written -> {INDEX_PATH}")

    # Write embedded catalog (same structure as catalog.json — retrieval_engine.py
    # reads catalog_embedded.json as the authoritative catalog for retrieval results)
    with open(EMBEDDED_CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
    print(f"  Embedded catalog written -> {EMBEDDED_CATALOG_PATH}")

    # Sanity check: one search
    print("\nSanity check: querying index with first product vector...")
    query = embeddings[0:1]
    distances, indices = index.search(query, 5)
    print("  Top-5 nearest products:")
    for rank, (dist, idx) in enumerate(zip(distances[0], indices[0]), 1):
        title = catalog[idx]["title"][:60] if idx < len(catalog) else "?"
        print(f"    {rank}. [{idx}] score={dist:.4f}  {title!r}")

    print("\n" + "=" * 60)
    print("FAISS INDEX REBUILD COMPLETE")
    print("=" * 60)
    print(f"Index:  {INDEX_PATH}")
    print(f"  Vectors : {index.ntotal:,}")
    print(f"  Dim     : {index.d}")
    print(f"Catalog : {EMBEDDED_CATALOG_PATH}")
    print(f"  Products: {len(catalog):,}")
    print(f"\nTotal encode time: {encode_time:.1f}s")
    print("\nRestart the backend server to pick up the new index.")


if __name__ == "__main__":
    main()
