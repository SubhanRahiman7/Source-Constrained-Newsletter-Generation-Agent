# Source-Constrained Newsletter Generation Agent

A small full-stack app: **Next.js** frontend + **FastAPI** backend. It builds a **FAISS** index over a fixed corpus, retrieves only from that index, and returns a **structured newsletter** with citations. Optional **OpenAI** improves prose; without it, output stays excerpt-based and fully traceable to retrieved text.

## Dataset

Declared in `backend/data/sources_manifest.json`. PDFs live in `backend/data/corpus/`. Each entry can include `description` and `url` for UI context.

After changing sources:

```bash
cd backend
python scripts/ingest.py
python scripts/build_index.py
```

Generated artifacts (`chunks.jsonl`, `index.faiss`) are gitignored; rebuild on each machine or in CI.

## Run locally

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python scripts/ingest.py
python scripts/build_index.py

uvicorn app.main:app --host 127.0.0.1 --port 8001
```

- `GET /health` — health check  
- `GET /sources` — source metadata (names, descriptions, URLs)  
- `POST /generate-newsletter` — body: `{ "topic": "...", "excluded_sources": [] }`

Optional: set `OPENAI_API_KEY` (see `backend/.env.example`) for JSON-mode generation.

### Frontend

```bash
cp .env.example .env.local
# Set NEXT_PUBLIC_NEWSLETTER_API_URL to match the backend (e.g. http://127.0.0.1:8001)

npm install
npm run dev -- -p 3001
```

Open [http://localhost:3001](http://localhost:3001).

## Deploy (outline)

- **Frontend:** Vercel (or similar) — set `NEXT_PUBLIC_NEWSLETTER_API_URL` to your public API URL.  
- **Backend:** any Python host (Railway, Render, Fly.io, VM) — run `uvicorn`, persist or rebuild `data/processed` after deploy. **`https://*.vercel.app`** is allowed for CORS by default; add **`ALLOWED_ORIGINS`** for custom domains. Local dev origins are always allowed.  
- **Render / small RAM:** Retrieval uses **FastEmbed** (ONNX), not PyTorch `sentence-transformers`, so `POST /generate-newsletter` is far less likely to OOM than before. If deploy health checks time out while the embedding model downloads, trigger a redeploy or set **`SKIP_RETRIEVER_WARMUP=1`** (first newsletter request may be slower).

## Project layout

- `backend/app/` — FastAPI app, retrieval, newsletter logic  
- `backend/data/` — manifest + corpus  
- `backend/scripts/` — ingest + index build  
- `src/components/newsletter-panel.tsx` — UI  
