<div align="center">

# Veritas — AI-Powered News Fact-Checker

**Analyze any news article for claim accuracy, source credibility, and political bias.**  
Inspired by Ground News. Built with FastAPI · Celery · React · Tailwind.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-3-06B6D4?logo=tailwindcss&logoColor=white)](https://tailwindcss.com)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## What is Veritas?

Veritas is a full-stack media analysis platform that takes a news article (by URL, file upload, or pasted text) and returns:

- ✅ **Claim verdict** — Supported / Refuted / Unverified, backed by web evidence
- 📰 **Coverage map** — How multiple outlets are covering the same story
- ⚖️ **Political bias** — Left / Center / Right rating from a curated database of 3 000+ sources
- 🌐 **Source credibility** — Factuality score and trust tier
- 🔍 **NLI verification** — Transformer-based Natural Language Inference for each extracted claim

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       Browser (React SPA)                   │
│              Vite · Tailwind · fetch / polling              │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP  (Vite proxy in dev / direct in prod)
┌────────────────────────▼────────────────────────────────────┐
│                    FastAPI  (port 8000)                     │
│    /api/verify/url   /api/verify/file   /api/verify/text    │
│    /api/result/{id}  /api/recent        /api/health         │
└───────────┬─────────────────────────────────────────────────┘
            │ enqueue task
┌───────────▼─────────────────────────────────────────────────┐
│                Redis  (broker + result backend)              │
└───────────┬─────────────────────────────────────────────────┘
            │ consume task
┌───────────▼─────────────────────────────────────────────────┐
│                   Celery Worker                             │
│  spaCy claim extraction → Serper.dev evidence retrieval     │
│  Transformers NLI verification → source bias lookup         │
│  Result stored in SQLite (or PostgreSQL)                    │
└─────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
veritas/
├── backend/
│   ├── main.py              # FastAPI app & all API routes
│   ├── worker.py            # Celery tasks (analyze_url, analyze_file, analyze_text)
│   ├── verifier.py          # Heuristic NLI claim verifier
│   ├── claims.py            # spaCy claim extractor
│   ├── retriever.py         # Serper.dev evidence search
│   ├── news_aggregator.py   # Related coverage finder
│   ├── source_analyzer.py   # Media bias lookup
│   ├── parser.py            # URL / PDF / DOCX / TXT parser
│   ├── celery_app.py        # Celery configuration
│   ├── database.py          # SQLAlchemy engine & session
│   ├── models.py            # ORM models
│   ├── source_bias.json     # Bias & factuality database (3 000+ sources)
│   └── trusted_sources.json # Curated trusted outlet list
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Full React application
│   │   ├── main.jsx         # Entry point
│   │   └── index.css        # Global styles
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js       # Dev proxy → backend :8000
│   ├── tailwind.config.js
│   └── postcss.config.js
├── tests/
│   ├── test_verifier.py     # Unit tests for verifier
│   ├── test_worker.py       # Unit tests for worker tasks
│   └── test_api.py          # Integration tests for API
├── .github/
│   ├── workflows/
│   │   └── ci.yml           # GitHub Actions CI pipeline
│   └── ISSUE_TEMPLATE/
│       ├── bug_report.md
│       └── feature_request.md
├── Dockerfile               # Backend image (api + worker share one image)
├── docker-compose.yml       # Full stack: redis + api + worker
├── requirements.txt
├── .env.example             # ← copy this to .env and fill in secrets
└── .gitignore
```

---

## Quick Start

### Option A — Docker (recommended)

> Requires: Docker ≥ 24 with Compose plugin

```bash
# 1. Clone and enter the repo
git clone https://github.com/YOUR_USERNAME/veritas.git
cd veritas

# 2. Configure secrets
cp .env.example .env
# Edit .env — fill in SERPER_API_KEY (and optionally SCRAPINGBEE_API_KEY)

# 3. Start the full backend stack
docker compose up --build

# 4. Build & serve the frontend (in a separate terminal)
cd frontend
cp .env.example .env          # VITE_API_BASE_URL=http://localhost:8000
npm install
npm run build
npx serve dist                # → http://localhost:3000
```

| Service | URL |
|---|---|
| API (FastAPI docs) | http://localhost:8000/docs |
| API (health check) | http://localhost:8000/api/health |
| Frontend | http://localhost:3000 |

---

### Option B — Local Development (manual)

#### 1. Backend

```bash
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

# Install dependencies
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm

# Copy and configure environment variables
cp .env.example .env          # Fill in SERPER_API_KEY at minimum
```

#### 2. Start Redis

```bash
# Option 1 — Docker (easiest)
docker run -d -p 6379:6379 redis:7-alpine

# Option 2 — Windows (WSL2 or native Redis)
# See: https://github.com/tporadowski/redis/releases

# Option 3 — macOS
brew install redis && brew services start redis
```

#### 3. Start the API server

```bash
# From project root
uvicorn backend.main:app --reload --port 8000
```

#### 4. Start the Celery worker

```bash
# In a second terminal (activate .venv first)
celery -A backend.celery_app.celery worker --loglevel=info --pool=gevent
```

#### 5. Start the frontend dev server

```bash
cd frontend
cp .env.example .env          # Leave VITE_API_BASE_URL empty for dev (Vite proxy handles it)
npm install
npm run dev
# → http://localhost:5173
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your values. **Never commit `.env` — it is git-ignored.**

### Root `.env` (backend)

| Variable | Required | Description |
|---|---|---|
| `SERPER_API_KEY` | ✅ | Google Search API key via [serper.dev](https://serper.dev) |
| `SCRAPINGBEE_API_KEY` | Optional | JS-rendered page scraping via [ScrapingBee](https://scrapingbee.com). Falls back to direct download if unset. |
| `DATABASE_URL` | ✅ | `sqlite:///./verified_articles.db` or a PostgreSQL URL |
| `REDIS_URL` | ✅ | `redis://localhost:6379/0` |
| `ALLOWED_ORIGINS` | ✅ | Comma-separated list of allowed frontend origins (CORS) |

### `frontend/.env` (frontend build)

| Variable | Required | Description |
|---|---|---|
| `VITE_API_BASE_URL` | Production only | Full URL of the deployed backend, e.g. `https://api.yourdomain.com`. Leave **empty** for local dev (Vite proxy handles it). |

---

## API Reference

Interactive docs auto-generated by FastAPI: **http://localhost:8000/docs**

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Health check — returns `{"status": "ok"}` |
| `POST` | `/api/verify/url` | Submit a URL for analysis. Returns `task_id` or cached result. |
| `POST` | `/api/verify/file` | Upload a PDF, DOCX, or TXT file for analysis. |
| `POST` | `/api/verify/text` | Submit pasted plain text for analysis. |
| `GET` | `/api/result/{task_id}` | Poll for the result of an async analysis task. |
| `GET` | `/api/recent` | Return the last 10 cached article analyses. |

**Polling pattern**

```
POST /api/verify/url  →  { "status": "PENDING", "task_id": "abc123" }

  Loop:
  GET /api/result/abc123  →  { "status": "PENDING" }
  GET /api/result/abc123  →  { "status": "SUCCESS", "result": { ... } }
```

---

## Running Tests

```bash
# Activate the virtual environment first
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

# Unit tests (no Redis or Celery needed)
python -m pytest tests/test_worker.py tests/test_verifier.py -v

# Integration tests (requires running API + Redis + Celery worker)
python -m pytest tests/test_api.py -v -s

# All tests with coverage
python -m pytest --tb=short -q
```

---

## Deployment

### Cloud VM (AWS EC2, DigitalOcean, GCP, etc.)

```bash
# On the server
git clone https://github.com/YOUR_USERNAME/veritas.git && cd veritas
curl -fsSL https://get.docker.com | sh          # Install Docker

cp .env.example .env
# Set ALLOWED_ORIGINS=https://your-frontend-domain.com in .env

docker compose up -d --build
```

Then build the frontend locally and deploy `frontend/dist/` to **Vercel**, **Netlify**, **Cloudflare Pages**, or any static host:

```bash
# Locally
cd frontend
VITE_API_BASE_URL=https://your-backend-domain.com npm run build
# Upload dist/ to your static host
```

### Environment-Specific Notes

- **SQLite** is fine for personal use and demos. For production with multiple workers, switch `DATABASE_URL` to PostgreSQL.
- **Celery concurrency**: The default `--concurrency=4` (gevent) can be tuned via the `command:` key in `docker-compose.yml`.
- **Reverse proxy**: Place nginx or Caddy in front of port 8000 to handle TLS and rate limiting in production.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines, branch naming, and the PR process.

---

## Security

To report a vulnerability, see [SECURITY.md](SECURITY.md).

---

## License

This project is licensed under the **MIT License** — see [LICENSE](LICENSE) for details.
