"""API and newsletter payload models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class NewsletterRequest(BaseModel):
    topic: str = Field(min_length=3, max_length=500)
    excluded_sources: list[str] = Field(
        default_factory=list,
        description="Source IDs from `sources_manifest.json` to exclude (not display names).",
    )
    retrieval_min_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional override for similarity threshold (cosine/IP on normalized embeddings).",
    )


class SourceInfo(BaseModel):
    id: str
    source_name: str
    publication_date: str
    description: str | None = None
    url: str | None = None


class SourceAttribution(BaseModel):
    source_id: str
    source_name: str
    publication_date: str
    retrieval_date: str
    location: str
    citation: str


class RetrievedContextBlock(BaseModel):
    chunk_id: str
    score: float
    text: str
    citation: str
    source_id: str


class NewsletterSection(BaseModel):
    title: str
    body: str
    confidence: float = Field(ge=0.0, le=1.0)
    cited_chunks: list[str] = Field(default_factory=list)


class DivergingView(BaseModel):
    claim_a: str
    claim_b: str
    notes: str | None = None


class NewsletterPayload(BaseModel):
    title: str
    summary: str
    sections: list[NewsletterSection]
    diverging_views: list[DivergingView] = Field(default_factory=list)


class NewsletterResponse(BaseModel):
    status: Literal["ok", "not_found_in_sources"]
    topic: str
    retrieval_date: str
    newsletter: NewsletterPayload | None = None
    context_blocks: list[RetrievedContextBlock] = Field(default_factory=list)
    source_coverage_percent: float = Field(ge=0.0, le=100.0)
    most_cited_source: str | None = None
    raw_llm: dict[str, Any] | None = Field(
        default=None,
        description="Optional raw model output for debugging; omit in production if undesired.",
    )
