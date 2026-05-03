#!/usr/bin/env python3
"""CLI: ingest corpus declared in data/sources_manifest.json -> data/processed/chunks.jsonl."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.ingestion import run_ingest


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest manifest sources into chunked JSONL.")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Path to backend/data (default: ../data next to app/)",
    )
    args = parser.parse_args()
    out = run_ingest(data_dir=args.data_dir)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
