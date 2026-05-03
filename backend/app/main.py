import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models import NewsletterRequest, NewsletterResponse, SourceInfo
from app.newsletter import generate_newsletter, list_sources


@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.getenv("SKIP_RETRIEVER_WARMUP", "").strip().lower() not in ("1", "true", "yes"):
        from app.retriever import warm_retriever_bundle

        warm_retriever_bundle()
    yield

_DEFAULT_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
]


def _cors_origins() -> list[str]:
    raw = os.getenv("ALLOWED_ORIGINS", "").strip()
    extra = [o.strip() for o in raw.split(",") if o.strip()]
    # De-dupe while preserving order
    seen: set[str] = set()
    out: list[str] = []
    for o in _DEFAULT_ORIGINS + extra:
        if o not in seen:
            seen.add(o)
            out.append(o)
    return out


# Any Vercel host (*.vercel.app) so preview/production URLs work without listing each one on Render.
# Set CORS_VERCEL_REGEX= to empty in env to disable (only ALLOWED_ORIGINS + defaults then).
_VERCEL_ORIGIN_REGEX = os.getenv(
    "CORS_VERCEL_REGEX", r"https://[\w.-]+\.vercel\.app$"
).strip() or None

app = FastAPI(title="Source-Constrained Newsletter Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_origin_regex=_VERCEL_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/generate-newsletter", response_model=NewsletterResponse)
def generate_newsletter_route(body: NewsletterRequest) -> NewsletterResponse:
    return generate_newsletter(body)


@app.get("/sources", response_model=list[SourceInfo])
def get_sources() -> list[SourceInfo]:
    return list_sources()
