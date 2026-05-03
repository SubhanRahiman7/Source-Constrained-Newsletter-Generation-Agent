"""Citation formatting for strict source traceability."""

from __future__ import annotations

from typing import Any


def format_citation(
    *,
    source_name: str,
    publication_date: str,
    retrieval_date: str,
    location: str,
) -> str:
    return (
        f"(Source: {source_name}, {publication_date} | "
        f"Retrieved: {retrieval_date} | Location: {location})"
    )


def citation_from_chunk(chunk: dict[str, Any]) -> str:
    return format_citation(
        source_name=str(chunk["source_name"]),
        publication_date=str(chunk["publication_date"]),
        retrieval_date=str(chunk["retrieval_date"]),
        location=str(chunk["location"]),
    )
