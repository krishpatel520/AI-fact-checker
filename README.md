<div align="center">

# Veritas — AI-Powered News Fact-Checker

**Agentic media analysis platform. Verify claims, reveal bias, map coverage across the political spectrum.**  
Inspired by Ground News · Built with FastAPI · Celery · Ollama · React · PostgreSQL · Kubernetes

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![Celery](https://img.shields.io/badge/Celery-5-37814A?logo=celery&logoColor=white)](https://docs.celeryq.dev)
[![Ollama](https://img.shields.io/badge/Ollama-llama3.2:3b-000000?logo=ollama&logoColor=white)](https://ollama.com)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-ready-326CE5?logo=kubernetes&logoColor=white)](https://kubernetes.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## What is Veritas?

Veritas is a full-stack **agentic media analysis platform** that takes a news article — by URL, file upload, or pasted text — and returns:

| Feature | Description |
|---|---|
| ✅ **Claim verdict** | Supported / Refuted / Unverified, backed by evidence from trusted outlets |
| 🤖 **LLM verification** | Ollama `llama3.2:3b` performs true semantic NLI — not keyword matching |
| 📰 **Coverage map** | How many outlets cover the same story, sorted left → right on the political spectrum |
| ⚖️ **Political bias** | Left / Center / Right rating from a curated database of 3,000+ sources |
| 🌐 **Source credibility** | Factuality score and trust tier per outlet |
| ⚡ **Real-time push** | Results delivered via WebSocket — no polling loop in the browser |

---

## Architecture

### The Agentic Pipeline

Unlike a monolithic task, Veritas runs a **parallel agent graph**:

```
  POST /api/verify/url
         │
  OrchestratorAgent (Phase 1 — PARALLEL)
    ├─ ParserAgent         → extracts {text, title, publish_date}
    └─ SourceBiasAgent     → looks up {bias, factuality, country}
         │ (both complete)
  phase2_callback (Phase 2 — PARALLEL fan-out)
    ├─ VerifierAgent × N   → one Celery task per claim (Ollama LLM NLI)
    └─ CoverageAgent       → Serper.dev news search for related articles
         │ (all complete)
  AggregatorAgent
    ├─ Assembles final JSON
    ├─ Writes PostgreSQL cache
    ├─ Updates AnalysisJob status
    └─ Publishes to Redis pub/sub → WebSocket push to browser
```

**Why agents?** Independent steps that don't depend on each other run concurrently — Source bias lookup + article parsing run in parallel (saves ~3–5s). Each claim gets its own Celery task, so 10 claims verify in the time it takes one claim to verify serially.

### Full Stack

```
Browser (React SPA)
  │  WebSocket /ws/{job_id}  ←── instant push when done
  │  REST /api/*             ←── submit + health + recent
  ▼
Nginx (reverse proxy, static files, WS upgrade)
  ▼
FastAPI :8000  (uvicorn, 2 workers)
  │  rate limiting (slowapi + Redis)
  ▼
Redis :6379  (Celery broker + result backend + pub/sub + rate limiter)
  ▼
Celery Workers  (gevent, 4 concurrent, queues: high / default / low)
  │  agents: ParserAgent, SourceBiasAgent, CoverageAgent,
  │          ClaimsAgent, VerifierAgent × N, AggregatorAgent
  ▼
Ollama :11434  (llama3.2:3b for semantic NLI — runs locally, free)
  ▼
PostgreSQL :5432  (verified_articles + analysis_jobs tables)
```

---

## Project Structure

```
veritas/
├── backend/
│   ├── agents/                  ← NEW: agentic pipeline
│   │   ├── orchestrator.py      #   two-phase Celery chord entry point
│   │   ├── parser_agent.py      #   URL/PDF/DOCX content extraction
│   │   ├── source_bias_agent.py #   media bias lookup
│   │   ├── coverage_agent.py    #   related outlet coverage search
│   │   ├── claims_agent.py      #   spaCy NLP claim extraction
│   │   ├── verifier_agent.py    #   Ollama LLM NLI + heuristic fallback
│   │   └── aggregator_agent.py  #   final assembly, DB write, WS push
│   ├── middleware/
│   │   └── rate_limit.py        #   slowapi per-IP rate limiter
│   ├── main.py                  #   FastAPI routes + WebSocket router
│   ├── ws.py                    #   /ws/{job_id} WebSocket endpoint
│   ├── worker.py                #   backward-compat Celery shims
│   ├── celery_app.py            #   Celery config, 3 queues
│   ├── models.py                #   VerifiedArticle + AnalysisJob ORM
│   ├── database.py              #   SQLAlchemy engine (PostgreSQL)
│   ├── verifier.py              #   heuristic NLI fallback
│   ├── claims.py                #   spaCy sentence extractor
│   ├── retriever.py             #   Serper.dev evidence search
│   ├── news_aggregator.py       #   related coverage finder
│   ├── parser.py                #   newspaper3k + ScrapingBee
│   ├── source_analyzer.py       #   bias lookup
│   ├── source_bias.json         #   3,000+ outlet bias database
│   └── trusted_sources.json     #   evidence search whitelist
├── frontend/
│   └── src/
│       ├── App.jsx              #   thin shell (60 lines)
│       ├── hooks/
│       │   └── useAnalysis.js   #   WebSocket + polling state machine
│       └── components/
│           ├── ui/
│           │   ├── Badge.jsx    #   BiasBadge, VerdictBadge, etc.
│           │   └── Spinner.jsx
│           ├── HomePage.jsx
│           ├── LoadingState.jsx
│           ├── ResultsPage.jsx
│           ├── EvidenceItem.jsx #   LLM + heuristic evidence cards
│           ├── CredibilityRing.jsx
│           └── SpectrumBar.jsx
├── tests/
│   ├── conftest.py
│   ├── agents/
│   │   ├── test_verifier_agent.py
│   │   └── test_aggregator_agent.py
│   ├── test_verifier.py
│   ├── test_worker.py
│   └── test_api.py              #   integration tests (needs live stack)
├── k8s/                         #   10 Kubernetes manifests
├── nginx/nginx.conf
├── Dockerfile                   #   multi-stage, one image, 3 roles via MODE=
├── docker-entrypoint.sh
├── docker-compose.yml           #   redis + postgres + ollama + api + worker + flower + nginx
├── pytest.ini
├── requirements.txt
└── .env.example
```

---

## Quick Start

### Option A — Docker Compose (Recommended)

> Requires: Docker ≥ 24 with Compose plugin · ~10 GB free disk (for Ollama model)

```bash
# 1. Clone
git clone https://github.com/YOUR_ORG/veritas.git && cd veritas

# 2. Configure
cp .env.example .env
# Edit .env — set SERPER_API_KEY (get free key at serper.dev)

# 3. Start everything
docker compose up --build
# ⚠️  First boot: Ollama downloads llama3.2:3b (~2.0 GB) — takes 5-10 min
# Watch for: "▶ Starting FastAPI" in the api container logs

# 4. Build & serve the frontend (separate terminal)
cd frontend
cp .env.example .env      # leave VITE_API_BASE_URL empty for Docker dev
npm install
npm run dev               # → http://localhost:5173 (proxied to Nginx/API)
```

| Service | URL |
|---|---|
| API docs | http://localhost:8000/api/docs |
| Frontend | http://localhost:5173 (dev) or http://localhost:80 (Nginx) |
| Flower (Celery monitor) | http://localhost:5555 (admin / veritas) |
| Ollama API | http://localhost:11434 |

---

### Option B — Local Development (Manual)

#### 1. Install Ollama and pull the model
```bash
# Windows: download from https://ollama.com/download
# macOS:
brew install ollama
ollama serve                        # start the daemon (separate terminal)
ollama pull llama3.2:3b             # ~2.0 GB download — one time
```

#### 2. Backend
```bash
python -m venv .venv
.venv\Scripts\activate              # Windows
# source .venv/bin/activate         # macOS/Linux

pip install -r requirements.txt
python -m spacy download en_core_web_sm

cp .env.example .env
# Edit .env: set SERPER_API_KEY, OLLAMA_HOST=http://localhost:11434
```

#### 3. Start Redis
```bash
docker run -d -p 6379:6379 redis:7-alpine
```

#### 4. Start PostgreSQL
```bash
docker run -d -p 5432:5432 \
  -e POSTGRES_USER=veritas \
  -e POSTGRES_PASSWORD=veritas \
  -e POSTGRES_DB=veritas \
  postgres:16-alpine
```

#### 5. Start FastAPI
```bash
uvicorn backend.main:app --reload --port 8000
```

#### 6. Start Celery worker
```bash
# In a new terminal (activate .venv first)
celery -A backend.celery_app.celery worker --loglevel=info --pool=gevent --queues=high,default,low
```

#### 7. Start frontend
```bash
cd frontend
cp .env.example .env
npm install
npm run dev     # → http://localhost:5173
```

---

## Environment Variables

### Root `.env` (backend + workers)

| Variable | Required | Default | Description |
|---|---|---|---|
| `SERPER_API_KEY` | ✅ | — | Google Search via [serper.dev](https://serper.dev) (free: 2,500/month) |
| `DATABASE_URL` | ✅ | — | PostgreSQL connection string, e.g. `postgresql://veritas:veritas@localhost:5432/veritas` |
| `REDIS_URL` | ✅ | `redis://localhost:6379/0` | Redis broker + backend + rate limiter |
| `OLLAMA_HOST` | ✅ | `http://localhost:11434` | Ollama REST API URL |
| `OLLAMA_MODEL` | — | `llama3.2:3b` | Model for NLI verification |
| `OLLAMA_TIMEOUT_SECONDS` | — | `45` | Per-claim LLM call timeout |
| `ALLOWED_ORIGINS` | ✅ | localhost variants | Comma-separated CORS origins |
| `SCRAPINGBEE_API_KEY` | Optional | — | JS-rendered page scraping fallback |

### `frontend/.env`

| Variable | Required | Description |
|---|---|---|
| `VITE_API_BASE_URL` | Production only | Full backend URL, e.g. `https://api.yourveritas.com` |
| `VITE_WS_URL` | Production only | WebSocket URL, e.g. `wss://api.yourveritas.com` |

---

## API Reference

Interactive docs: **http://localhost:8000/api/docs**

| Method | Path | Description |
|---|---|---|
| `GET`  | `/api/health` | Health check |
| `POST` | `/api/verify/url` | Submit URL → `{job_id}` or cached `{result}` |
| `POST` | `/api/verify/file` | Upload PDF/DOCX/TXT → `{job_id}` |
| `POST` | `/api/verify/text` | Paste text → `{job_id}` |
| `GET`  | `/api/job/{job_id}` | Poll job status: pending / running / done / failed |
| `GET`  | `/api/recent` | Last N cached analyses |
| `WS`   | `/ws/{job_id}` | WebSocket push — single result event |
| `GET`  | `/api/result/{task_id}` | ⚠️ Deprecated — use `/api/job/{job_id}` |

**Flow:**
```
POST /api/verify/url  →  { "status": "PENDING", "job_id": "uuid" }
WS   /ws/{job_id}     →  { "status_event": "done", ...full result... }
   (or poll)  GET /api/job/{job_id}  →  { "status": "done", "result": {...} }
```

---

## Running Tests

```bash
# Activate your virtual environment first
.venv\Scripts\activate

# Unit tests (no running services needed)
python -m pytest tests/test_verifier.py tests/agents/ -v

# All unit tests
python -m pytest tests/ --ignore=tests/test_api.py -v

# Integration tests (requires full stack running)
python -m pytest tests/test_api.py -v -s
```

---

## Deployment

### Kubernetes

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml       # update with real base64 values first
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/ollama.yaml
# Wait for Ollama model download (~5 min)
kubectl wait --for=condition=ready pod -l app=ollama -n veritas --timeout=600s
kubectl apply -f k8s/api-deployment.yaml
kubectl apply -f k8s/worker-deployment.yaml
kubectl apply -f k8s/flower-deployment.yaml
kubectl apply -f k8s/ingress.yaml
```

Update `k8s/ingress.yaml` hostname and `k8s/configmap.yaml` ALLOWED_ORIGINS before deploying.

### Docker Compose (Production)
```bash
# Build and deploy
VITE_API_BASE_URL=https://api.yourdomain.com npm run build --prefix frontend
docker compose up -d --build
```

---

## Ollama Model Notes

| Model | Size | Speed (CPU) | Quality |
|---|---|---|---|
| `llama3.1:8b` ⭐ | 4.7 GB | ~8–15s/claim | Excellent |
| `mistral:7b` | 4.1 GB | ~6–12s/claim | Very good |
| `phi3:medium` | 7.9 GB | ~15–25s/claim | Best quality |
| `llama3.2:3b` | 2.0 GB | ~3–6s/claim | Good for low-RAM |

For **GPU acceleration**, uncomment the `deploy.resources` block in `docker-compose.yml` (Ollama service) and the `nvidia.com/gpu` lines in `k8s/ollama.yaml`.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Security

See [SECURITY.md](SECURITY.md) to report vulnerabilities.

## License

MIT — see [LICENSE](LICENSE).
