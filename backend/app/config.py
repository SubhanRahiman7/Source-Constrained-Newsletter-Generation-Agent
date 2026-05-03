"""Backend configuration defaults."""

from __future__ import annotations

from pathlib import Path

# Embedding model (small, widely cached; good for demos).
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Retrieval
TOP_K = 8
MIN_SIMILARITY = 0.18  # cosine on normalized vectors via inner product

# Paths relative to backend/data/
CHUNKS_FILENAME = "chunks.jsonl"
INDEX_FILENAME = "index.faiss"
INDEX_META_FILENAME = "index_meta.json"


def default_data_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "data"
