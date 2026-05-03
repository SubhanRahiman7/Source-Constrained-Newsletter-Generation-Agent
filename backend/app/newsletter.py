"""Source-constrained newsletter generation."""

from __future__ import annotations

import json
import os
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from app.citation import citation_from_chunk
from app.config import MIN_SIMILARITY, TOP_K, default_data_dir
from app.models import (
    DivergingView,
    NewsletterPayload,
    NewsletterRequest,
    NewsletterResponse,
    NewsletterSection,
    RetrievedContextBlock,
    SourceInfo,
)
from app.retriever import RetrievalHit, retrieve_chunks

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None  # type: ignore[misc, assignment]


def _manifest_source_count(data_dir: Path) -> int:
    manifest = data_dir / "sources_manifest.json"
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    return len(payload["sources"])


def list_sources(*, data_dir: Path | None = None) -> list[SourceInfo]:
    """Return source metadata so UI can explain each PDF to users."""
    if data_dir is None:
        data_dir = default_data_dir()
    manifest = data_dir / "sources_manifest.json"
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    out: list[SourceInfo] = []
    for raw in payload.get("sources", []):
        out.append(
            SourceInfo(
                id=str(raw.get("id", "")),
                source_name=str(raw.get("source_name", "")),
                publication_date=str(raw.get("publication_date", "")),
                description=(str(raw["description"]) if raw.get("description") is not None else None),
                url=(str(raw["url"]) if raw.get("url") is not None else None),
            )
        )
    return out


def _excerpt(text: str, max_len: int = 240) -> str:
    t = re.sub(r"\s+", " ", text.strip())
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"


def _conflict_views(hits: list[RetrievalHit]) -> list[DivergingView]:
    """
    Lightweight contradiction heuristic: different sources stress mandatory obligations
    vs voluntary / flexible industry-led approaches.
    """
    by_source: dict[str, list[RetrievalHit]] = defaultdict(list)
    for h in hits:
        sid = str(h.chunk.get("source_id", ""))
        if sid:
            by_source[sid].append(h)

    pos_kw = ("mandatory", "obligations", "insufficient", "risk assessments")
    neg_kw = ("voluntary", "safe harbor", "flexible", "industry-led", "chill")

    def pick_hit(keywords: tuple[str, ...]) -> RetrievalHit | None:
        best: RetrievalHit | None = None
        best_score = -1.0
        for h in hits:
            low = h.chunk["text"].lower()
            if any(k in low for k in keywords) and h.score > best_score:
                best = h
                best_score = h.score
        return best

    pos_hit = pick_hit(pos_kw)
    neg_hit = pick_hit(neg_kw)
    if not pos_hit or not neg_hit:
        return []
    if str(pos_hit.chunk.get("source_id")) == str(neg_hit.chunk.get("source_id")):
        return []

    ca = f'"{_excerpt(pos_hit.chunk["text"])}" {citation_from_chunk(pos_hit.chunk)}'
    cb = f'"{_excerpt(neg_hit.chunk["text"])}" {citation_from_chunk(neg_hit.chunk)}'
    return [
        DivergingView(
            claim_a=ca,
            claim_b=cb,
            notes=(
                "These excerpts emphasize different postures on how binding obligations should be "
                "relative to voluntary adoption."
            ),
        )
    ]


def _fallback_newsletter(topic: str, hits: list[RetrievalHit]) -> NewsletterPayload:
    by_source: dict[str, list[RetrievalHit]] = defaultdict(list)
    for h in hits:
        sid = str(h.chunk.get("source_id", "")) or "unknown"
        by_source[sid].append(h)

    sections: list[NewsletterSection] = []
    summary_bits: list[str] = []

    for sid, group in by_source.items():
        group = sorted(group, key=lambda h: h.score, reverse=True)
        name = str(group[0].chunk["source_name"])
        bullets: list[str] = []
        cited_chunks: list[str] = []
        for h in group[:3]:
            cite = citation_from_chunk(h.chunk)
            bullets.append(f"- \"{_excerpt(h.chunk['text'], 320)}\" {cite}")
            cited_chunks.append(str(h.chunk["chunk_id"]))
        body = "\n".join(bullets)
        sections.append(
            NewsletterSection(
                title=f"What `{name}` contributes",
                body=body,
                confidence=min(1.0, max(0.2, sum(h.score for h in group) / max(1, len(group)))),
                cited_chunks=cited_chunks,
            )
        )
        summary_bits.append(
            f"- From {name}: \"{_excerpt(group[0].chunk['text'])}\" {citation_from_chunk(group[0].chunk)}"
        )

    summary = "Corpus-grounded highlights (direct excerpts only):\n" + "\n".join(summary_bits)
    diverging = _conflict_views(hits)

    return NewsletterPayload(
        title=f"Newsletter — {topic}",
        summary=summary,
        sections=sections[:4],
        diverging_views=diverging,
    )


def _llm_newsletter(topic: str, hits: list[RetrievalHit]) -> tuple[NewsletterPayload, dict[str, Any]]:
    if OpenAI is None:
        raise RuntimeError("openai package not available")

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
    numbered = []
    for i, h in enumerate(hits, start=1):
        cite = citation_from_chunk(h.chunk)
        numbered.append(f"### Context {i}\nCitation line (use verbatim in output): {cite}\n{h.chunk['text']}")

    context = "\n\n---\n\n".join(numbered)
    schema_hint = (
        "Return JSON with keys: title (string), summary (string), sections (array of 2-4 objects "
        "with title, body, confidence number 0-1, cited_chunks array of chunk_id strings), "
        "diverging_views (array of objects with claim_a, claim_b, optional notes). "
        "Every sentence in summary and each section body must end with a citation in parentheses "
        "matching one of the provided Citation lines exactly."
    )

    system = (
        "You write newsletters for policy researchers. Rules:\n"
        "- Use ONLY the provided context blocks.\n"
        "- Do NOT use outside knowledge.\n"
        "- If something is not supported by context, write: Not available in sources.\n"
        "- Every claim must include a citation copied verbatim from the context header.\n"
        "- If sources disagree, populate diverging_views with two opposing claims, each cited.\n"
        + schema_hint
    )
    user = f"Topic: {topic}\n\n{context}"

    client = OpenAI()
    resp = client.chat.completions.create(
        model=model,
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    raw_text = resp.choices[0].message.content or "{}"
    raw: dict[str, Any] = json.loads(raw_text)
    payload = NewsletterPayload.model_validate(raw)
    meta: dict[str, Any] = {"model": model, "raw": raw}
    usage_obj = getattr(resp, "usage", None)
    if usage_obj is not None and hasattr(usage_obj, "model_dump"):
        meta["usage"] = usage_obj.model_dump()
    return payload, meta


def _hits_to_blocks(hits: list[RetrievalHit]) -> list[RetrievedContextBlock]:
    blocks: list[RetrievedContextBlock] = []
    for h in hits:
        c = h.chunk
        blocks.append(
            RetrievedContextBlock(
                chunk_id=str(c["chunk_id"]),
                score=float(h.score),
                text=str(c["text"]),
                citation=citation_from_chunk(c),
                source_id=str(c.get("source_id", "")),
            )
        )
    return blocks


def _source_coverage(hits: list[RetrievalHit], total_sources: int) -> float:
    if total_sources <= 0:
        return 0.0
    used = {str(h.chunk.get("source_id", "")) for h in hits if h.chunk.get("source_id")}
    return round(len(used) / total_sources * 100.0, 2)


def _most_cited_source(hits: list[RetrievalHit]) -> str | None:
    if not hits:
        return None
    c = Counter(str(h.chunk.get("source_id", "")) for h in hits if h.chunk.get("source_id"))
    sid, _ = c.most_common(1)[0]
    for h in hits:
        if str(h.chunk.get("source_id")) == sid:
            return str(h.chunk["source_name"])
    return None


def generate_newsletter(req: NewsletterRequest, *, data_dir: Path | None = None) -> NewsletterResponse:
    if data_dir is None:
        data_dir = default_data_dir()
    data_dir = data_dir.resolve()

    retrieval_date = date.today().isoformat()
    min_sim = float(req.retrieval_min_score) if req.retrieval_min_score is not None else float(MIN_SIMILARITY)

    hits = retrieve_chunks(
        req.topic,
        data_dir=data_dir,
        top_k=TOP_K,
        min_similarity=min_sim,
        excluded_source_ids=req.excluded_sources,
    )
    total_sources = _manifest_source_count(data_dir)

    if not hits:
        return NewsletterResponse(
            status="not_found_in_sources",
            topic=req.topic,
            retrieval_date=retrieval_date,
            newsletter=None,
            context_blocks=[],
            source_coverage_percent=0.0,
            most_cited_source=None,
            raw_llm=None,
        )

    blocks = _hits_to_blocks(hits)

    raw_llm: dict[str, Any] | None = None
    if os.getenv("OPENAI_API_KEY", "").strip():
        try:
            newsletter, raw_llm = _llm_newsletter(req.topic, hits)
        except Exception:
            newsletter = _fallback_newsletter(req.topic, hits)
            raw_llm = {"fallback": True, "reason": "llm_failed"}
    else:
        newsletter = _fallback_newsletter(req.topic, hits)
        raw_llm = {"fallback": True, "reason": "no_openai_key"}

    return NewsletterResponse(
        status="ok",
        topic=req.topic,
        retrieval_date=retrieval_date,
        newsletter=newsletter,
        context_blocks=blocks,
        source_coverage_percent=_source_coverage(hits, total_sources),
        most_cited_source=_most_cited_source(hits),
        raw_llm=raw_llm,
    )
