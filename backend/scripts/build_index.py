#!/usr/bin/env python3
"""Build FAISS index from data/processed/chunks.jsonl."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.indexing import build_faiss_index


def main() -> None:
    parser = argparse.ArgumentParser(description="Build FAISS index for ingested chunks.")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Path to backend/data (default: ../data next to app/)",
    )
    args = parser.parse_args()
    index_path, meta_path = build_faiss_index(data_dir=args.data_dir)
    print(f"Wrote index: {index_path}")
    print(f"Wrote meta: {meta_path}")


if __name__ == "__main__":
    main()
