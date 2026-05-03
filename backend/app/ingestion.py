"""Ingest declared sources into chunked JSONL with citation metadata."""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterator

# Rough token bounds: ~4 chars/token for English prose.
_MIN_CHARS = 300 * 4
_MAX_CHARS = 800 * 4


@dataclass(frozen=True)
class SourceSpec:
    id: str
    source_name: str
    publication_date: str
    file: str
    type: str


def _load_manifest(manifest_path: Path) -> list[SourceSpec]:
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    sources = raw.get("sources")
    if not isinstance(sources, list):
        raise ValueError("manifest must contain a 'sources' array")
    out: list[SourceSpec] = []
    for item in sources:
        if not isinstance(item, dict):
            raise ValueError("each source must be an object")
        out.append(
            SourceSpec(
                id=str(item["id"]),
                source_name=str(item["source_name"]),
                publication_date=str(item["publication_date"]),
                file=str(item["file"]),
                type=str(item["type"]),
            )
        )
    return out


def _paragraphs(text: str) -> list[str]:
    parts = re.split(r"\n\s*\n", text)
    return [p.strip() for p in parts if p.strip()]


def chunk_text(
    text: str,
    *,
    min_chars: int = _MIN_CHARS,
    max_chars: int = _MAX_CHARS,
) -> list[str]:
    """Chunk plain text into ~300–800 token segments using paragraph boundaries."""
    paras = _paragraphs(text)
    if not paras:
        return []
    chunks: list[str] = []
    buf: list[str] = []
    buf_len = 0
    for p in paras:
        add_len = len(p) if not buf else len(p) + 2
        if buf and buf_len + add_len > max_chars and buf_len >= min_chars:
            chunks.append("\n\n".join(buf))
            buf = [p]
            buf_len = len(p)
        else:
            buf.append(p)
            buf_len += add_len
    if buf:
        chunks.append("\n\n".join(buf))
    # Merge undersized tail into previous chunk if possible
    if len(chunks) >= 2 and len(chunks[-1]) < min_chars:
        tail = chunks.pop()
        chunks[-1] = chunks[-1] + "\n\n" + tail
    return chunks


def _extract_pdf_pages(path: Path) -> list[tuple[int, str]]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    out: list[tuple[int, str]] = []
    for i, page in enumerate(reader.pages, start=1):
        t = page.extract_text() or ""
        if t.strip():
            out.append((i, t))
    return out


def _read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def iter_chunks_for_source(
    spec: SourceSpec,
    data_dir: Path,
    *,
    retrieval_date: str,
) -> Iterator[dict[str, Any]]:
    file_path = (data_dir / spec.file).resolve()
    if not file_path.is_file():
        raise FileNotFoundError(f"Source file missing: {spec.file}")

    t = spec.type.lower()
    if t in ("text", "markdown", "md"):
        body = _read_text_file(file_path)
        parts = chunk_text(body)
        total = len(parts)
        for i, chunk in enumerate(parts):
            loc = f"Section chunk {i + 1}/{total}" if total > 1 else "Full document"
            yield {
                "chunk_id": f"{spec.id}-{i:04d}-{uuid.uuid4().hex[:8]}",
                "text": chunk,
                "source_name": spec.source_name,
                "publication_date": spec.publication_date,
                "retrieval_date": retrieval_date,
                "location": loc,
                "source_id": spec.id,
            }
    elif t == "pdf":
        pages = _extract_pdf_pages(file_path)
        idx = 0
        for page_num, page_text in pages:
            for chunk in chunk_text(page_text):
                yield {
                    "chunk_id": f"{spec.id}-{idx:04d}-{uuid.uuid4().hex[:8]}",
                    "text": chunk,
                    "source_name": spec.source_name,
                    "publication_date": spec.publication_date,
                    "retrieval_date": retrieval_date,
                    "location": f"Page {page_num}",
                    "source_id": spec.id,
                }
                idx += 1
    else:
        raise ValueError(f"Unsupported source type: {spec.type}")


def run_ingest(
    *,
    data_dir: Path | None = None,
    manifest_name: str = "sources_manifest.json",
    output_relative: str = "processed/chunks.jsonl",
) -> Path:
    """
    Read manifest under data_dir, write chunks.jsonl to data_dir/processed/.
    Returns path to chunks.jsonl.
    """
    if data_dir is None:
        data_dir = Path(__file__).resolve().parents[1] / "data"
    data_dir = data_dir.resolve()
    manifest_path = data_dir / manifest_name
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    processed_dir = data_dir / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    out_path = processed_dir / Path(output_relative).name

    retrieval_date = date.today().isoformat()
    specs = _load_manifest(manifest_path)
    lines: list[str] = []
    for spec in specs:
        for row in iter_chunks_for_source(spec, data_dir, retrieval_date=retrieval_date):
            lines.append(json.dumps(row, ensure_ascii=False))

    out_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return out_path
