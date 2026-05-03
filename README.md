# Source-Constrained Newsletter Generation Agent

A full-stack system that produces **structured newsletters** exclusively from a **fixed, declared corpus** of policy PDFs. The **Next.js** client calls a **FastAPI** service that **embeds the topic**, searches a **FAISS** index over ingested chunks, and returns **JSON** with sections, summaries, and **source citations**. Optional **OpenAI** (JSON mode) refines wording; without it, output remains **excerpt-grounded** and traceable to retrieved text.

---

## Live deployments

Set these to match **your** production setup. The frontend must expose the backend origin via `NEXT_PUBLIC_NEWSLETTER_API_URL`.

| Component | Base URL |
|-----------|----------|
| **Frontend** (Next.js) | `https://source-constrained-newsletter-gener.vercel.app` — *replace with your **Vercel → Deployments → Production → Visit** URL if this project uses a different hostname.* |
| **Backend** (FastAPI) | `https://source-constrained-newsletter-generation.onrender.com` |

**Environment sync:** On Vercel, set `NEXT_PUBLIC_NEWSLETTER_API_URL` to the **backend** URL (scheme + host, no path). The API allows browser calls from `https://*.vercel.app` via CORS; use `ALLOWED_ORIGINS` for custom domains (see `backend/.env.example`).

---

## Overview

| Concern | Approach |
|---------|-----------|
| **Retrieval** | FastEmbed (ONNX) query vectors; **FAISS** inner-product search over normalized embeddings; configurable top‑k and similarity floor. |
| **Grounding** | Newsletter content is driven by retrieved chunks only; citations reference manifest metadata and chunk locations. |
| **Source exclusion** | Request body may list `excluded_sources` (manifest `id` values) to demonstrate constraint under a reduced corpus. |
| **Failure mode** | When no chunks meet the threshold, the API returns `not_found_in_sources` instead of fabricating a newsletter. |

---

## Dataset

- **Manifest:** `backend/data/sources_manifest.json` — source `id`, display name, dates, optional `description` and `url`.
- **Corpus:** `backend/data/corpus/*.pdf` — India AI governance materials (IndiaAI / MeitY, NITI Aayog, MeitY advisory) as shipped in-repo.

After adding or changing PDFs:

```bash
cd backend
python scripts/ingest.py
python scripts/build_index.py
```

Artifacts under `backend/data/processed/` (`chunks.jsonl`, `index.faiss`, `index_meta.json`) are **not committed**; rebuild after clone or on the server **build** step.

---

## Configuration

### Backend (`backend/.env.example`)

| Variable | Purpose |
|----------|---------|
| `ALLOWED_ORIGINS` | Comma-separated extra browser origins (e.g. custom domain). |
| `CORS_VERCEL_REGEX` | Optional override; default permits `https://*.vercel.app`. |
| `OPENAI_API_KEY` / `OPENAI_MODEL` | Optional LLM polish (JSON mode). |
| `SKIP_RETRIEVER_WARMUP` | Set to `1` if startup model load conflicts with host health checks. |

### Frontend (`.env.example`)

| Variable | Purpose |
|----------|---------|
| `NEXT_PUBLIC_NEWSLETTER_API_URL` | Public FastAPI base URL (local, Render, etc.). |

---

## Local development

### API service

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python scripts/ingest.py
python scripts/build_index.py
uvicorn app.main:app --host 127.0.0.1 --port 8001
```

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness |
| `GET` | `/sources` | Source metadata for the UI |
| `POST` | `/generate-newsletter` | Body: `{ "topic": string, "excluded_sources": string[] }` |

### Web application

```bash
cp .env.example .env.local
# NEXT_PUBLIC_NEWSLETTER_API_URL=http://127.0.0.1:8001
npm install
npm run dev -- -p 3001
```

Open [http://localhost:3001](http://localhost:3001).

```bash
npm run build
npm run start
npm run lint
```

---

## Production deployment notes

- **Frontend:** Vercel (or equivalent). Repository root must contain `package.json` and `src/`; **do not** set the Vercel root directory to `backend`.
- **Backend:** Python host with sufficient RAM for FastEmbed + FAISS (see Render **Starter** or above if the free tier is tight). **Build** should run `pip install -r requirements.txt`, ingest, and index build; **start** should run `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
- **Python version:** `.python-version` pins **3.12** so dependency wheels (e.g. FastEmbed) install without Rust toolchain builds on hosts such as Render.
- **Do not** set arbitrary `PORT` in Render env vars; the platform injects it.

---

## Repository layout

```
backend/
  app/           # FastAPI, retrieval, newsletter pipeline, CORS
  data/          # Manifest + corpus + generated processed/ (ignored)
  scripts/       # ingest.py, build_index.py
src/
  app/           # Next.js App Router entry
  components/    # Newsletter UI (e.g. newsletter-panel.tsx)
.python-version  # 3.12 for compatible wheels on PaaS builders
```

---

## License

Use is governed by your course or organization; the repository owner may specify a formal license separately.
