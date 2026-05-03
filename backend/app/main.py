from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models import NewsletterRequest, NewsletterResponse, SourceInfo
from app.newsletter import generate_newsletter, list_sources

app = FastAPI(title="Source-Constrained Newsletter Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
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
