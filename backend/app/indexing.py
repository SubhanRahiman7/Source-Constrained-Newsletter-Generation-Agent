"""Build FAISS index from chunked JSONL."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import faiss  # type: ignore[import-untyped]
import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import (
    CHUNKS_FILENAME,
    EMBEDDING_MODEL_NAME,
    INDEX_FILENAME,
    INDEX_META_FILENAME,
)


def _load_chunks(chunks_path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in chunks_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    if not rows:
        raise ValueError(f"No chunks in {chunks_path}")
    return rows


def build_faiss_index(
    *,
    data_dir: Path | None = None,
    model_name: str = EMBEDDING_MODEL_NAME,
) -> tuple[Path, Path]:
    if data_dir is None:
        data_dir = Path(__file__).resolve().parents[1] / "data"
    data_dir = data_dir.resolve()
    processed = data_dir / "processed"
    processed.mkdir(parents=True, exist_ok=True)
    chunks_path = processed / CHUNKS_FILENAME
    if not chunks_path.is_file():
        raise FileNotFoundError(
            f"Missing {chunks_path}. Run `python scripts/ingest.py` first.",
        )

    rows = _load_chunks(chunks_path)
    texts = [str(r["text"]) for r in rows]

    model = SentenceTransformer(model_name)
    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=False,
        convert_to_numpy=True,
    )
    if embeddings.ndim != 2:
        raise RuntimeError("Unexpected embedding shape")
    vectors = np.asarray(embeddings, dtype="float32")
    dim = vectors.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(vectors)

    index_path = processed / INDEX_FILENAME
    meta_path = processed / INDEX_META_FILENAME
    faiss.write_index(index, str(index_path))
    meta_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return index_path, meta_path
