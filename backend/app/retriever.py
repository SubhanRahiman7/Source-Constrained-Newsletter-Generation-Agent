"""FAISS retrieval over ingested chunks only."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import faiss  # type: ignore[import-untyped]
import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import (
    EMBEDDING_MODEL_NAME,
    INDEX_FILENAME,
    INDEX_META_FILENAME,
    MIN_SIMILARITY,
    TOP_K,
    default_data_dir,
)


@dataclass(frozen=True)
class RetrievalHit:
    chunk: dict[str, Any]
    score: float


_index: faiss.Index | None = None
_meta: list[dict[str, Any]] | None = None
_model: SentenceTransformer | None = None
_loaded_for: Path | None = None


def reset_retriever_cache() -> None:
    global _index, _meta, _model, _loaded_for
    _index = None
    _meta = None
    _model = None
    _loaded_for = None


def _load_retriever_bundle(data_dir: Path) -> tuple[faiss.Index, list[dict[str, Any]], SentenceTransformer]:
    global _index, _meta, _model, _loaded_for
    data_dir = data_dir.resolve()
    if _index is not None and _meta is not None and _model is not None and _loaded_for == data_dir:
        return _index, _meta, _model

    processed = data_dir / "processed"
    index_path = processed / INDEX_FILENAME
    meta_path = processed / INDEX_META_FILENAME
    if not index_path.is_file() or not meta_path.is_file():
        raise FileNotFoundError(
            f"Missing FAISS index or meta under {processed}. Run `python scripts/build_index.py`.",
        )
    _index = faiss.read_index(str(index_path))
    _meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if not isinstance(_meta, list):
        raise ValueError("index_meta must be a JSON array")
    _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    _loaded_for = data_dir
    return _index, _meta, _model


def retrieve_chunks(
    query: str,
    *,
    top_k: int = TOP_K,
    min_similarity: float = MIN_SIMILARITY,
    data_dir: Path | None = None,
    excluded_source_ids: list[str] | None = None,
) -> list[RetrievalHit]:
    """
    Return top-k chunks from the dataset index only.
    Scores are inner-product / cosine similarity for L2-normalized embeddings.
    """
    if data_dir is None:
        data_dir = default_data_dir()
    q = (query or "").strip()
    if not q:
        return []

    index, meta, model = _load_retriever_bundle(data_dir)
    excluded = set(excluded_source_ids or [])

    qv = model.encode([q], normalize_embeddings=True, convert_to_numpy=True)
    qv = np.asarray(qv, dtype="float32")
    # Oversample then filter exclusions / threshold.
    n_probe = min(len(meta), max(top_k * 6, top_k))
    scores, idxs = index.search(qv, n_probe)
    hits: list[RetrievalHit] = []
    for score, idx in zip(scores[0].tolist(), idxs[0].tolist(), strict=False):
        if idx < 0:
            continue
        chunk = meta[idx]
        sid = str(chunk.get("source_id", ""))
        if sid and sid in excluded:
            continue
        if float(score) < float(min_similarity):
            continue
        hits.append(RetrievalHit(chunk=chunk, score=float(score)))
        if len(hits) >= top_k:
            break

    return hits
