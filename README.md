# Veritas — AI-Powered News Fact-Checker

AI-powered media bias and fact-checking platform inspired by Ground News. Analyzes news articles to reveal claim verdicts, source credibility, political bias, and how multiple outlets cover the same story.

---

## Project Structure

```
fake_news/
├── backend/               # FastAPI application
│   ├── main.py            # API endpoints
│   ├── worker.py          # Celery background tasks
│   ├── verifier.py        # Heuristic NLI claim verifier
│   ├── claims.py          # spaCy claim extractor
│   ├── retriever.py       # Serper.dev evidence search
│   ├── news_aggregator.py # Related coverage finder
│   ├── source_analyzer.py # Media bias lookup
│   ├── source_bias.json   # Bias/factuality database
│   └── trusted_sources.json
├── frontend/              # Vite + React + Tailwind SPA
│   ├── src/
│   │   ├── App.jsx        # Full React application
│   │   ├── main.jsx       # Entry point
│   │   └── index.css      # All styles
│   ├── index.html
│   ├── package.json
│   └── vite.config.js     # Dev proxy → backend :8000
├── tests/
│   ├── test_verifier.py
│   ├── test_worker.py
│   └── test_api.py
├── Dockerfile             # Backend image (api + worker)
├── docker-compose.yml     # Full stack: redis + api + worker
├── requirements.txt
├── .env                   # Your secrets (git-ignored)
└── .env.example           # Template — copy to .env
```

---

## Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| Python | ≥ 3.11 | Backend |
| Node.js | ≥ 18 | Frontend build |
| Redis | ≥ 7 | Celery broker |
| Docker + Compose | any | Containerized deployment |

---

## Option A — Docker (Recommended for Deployment)

### 1. Configure environment
```bash
cp .env.example .env
# Edit .env with your real API keys:
#   SCRAPINGBEE_API_KEY=...
#   SERPER_API_KEY=...
#   ALLOWED_ORIGINS=https://your-frontend-domain.com
```

### 2. Build and start everything
```bash
docker compose up --build
```

This starts three containers:
- **redis** — message broker on port 6379
- **api** — FastAPI on port 8000
- **worker** — Celery background worker

### 3. Build and serve the frontend
```bash
cd frontend
cp .env.example .env
# Set VITE_API_BASE_URL=http://your-server-ip:8000 (or your domain)
npm install
npm run build
# The dist/ folder is a static site — serve it with any web server:
# e.g. nginx, Vercel, Netlify, S3+CloudFront, or:
npx serve dist
```

---

## Option B — Local Development (Manual)

### Step 1 — Backend setup
```bash
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Download spaCy language model
python -m spacy download en_core_web_sm

# Copy and fill in your environment variables
cp .env.example .env
```

### Step 2 — Start Redis
Make sure Redis is running locally. Options:
- **Windows**: Use [Redis for Windows](https://github.com/tporadowski/redis/releases) or WSL2
- **macOS**: `brew install redis && brew services start redis`
- **Docker (Redis only)**: `docker run -d -p 6379:6379 redis:7-alpine`

### Step 3 — Start the API server
```bash
# From the project root (fake_news/)
uvicorn backend.main:app --reload --port 8000
```

### Step 4 — Start the Celery worker
```bash
# In a second terminal (activate .venv first)
celery -A backend.celery_app.celery worker --loglevel=info --pool=gevent
```

### Step 5 — Start the frontend dev server
```bash
cd frontend
cp .env.example .env        # VITE_API_BASE_URL can stay empty for dev
npm install
npm run dev
# Open http://localhost:5173
```

---

## Running Tests

```bash
# Activate the backend venv first
.venv\Scripts\activate

# Unit tests (no Redis/Celery needed)
python -m pytest tests/test_worker.py tests/test_verifier.py -v

# Integration test (requires running API + Celery + Redis)
python -m pytest tests/test_api.py -v -s
```

---

## Deploying to a Cloud VM (e.g. AWS EC2, DigitalOcean, GCP)

1. SSH into your server and clone the repo
2. Install Docker: `curl -fsSL https://get.docker.com | sh`
3. Configure `.env` with your API keys and set:
   ```
   ALLOWED_ORIGINS=https://your-frontend-domain.com
   ```
4. `docker compose up -d --build`
5. Point your DNS to the server's IP
6. Build the frontend locally with `VITE_API_BASE_URL=https://your-server-ip-or-domain:8000`, then deploy the `dist/` folder to Vercel/Netlify/S3

---

## Key API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/verify/url` | Submit URL for analysis |
| `POST` | `/api/verify/file` | Upload PDF/DOCX/TXT |
| `POST` | `/api/verify/text` | Submit pasted plain text |
| `GET` | `/api/result/{task_id}` | Poll task result |
| `GET` | `/api/recent` | Last 10 analysed articles |

---

## Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `SERPER_API_KEY` | ✅ | Google Search API via serper.dev |
| `SCRAPINGBEE_API_KEY` | Optional | JS-rendered page scraping |
| `DATABASE_URL` | ✅ | SQLite path or PostgreSQL URL |
| `REDIS_URL` | ✅ | Celery broker URL |
| `ALLOWED_ORIGINS` | ✅ | Comma-separated CORS origins |
| `VITE_API_BASE_URL` | Frontend | Backend URL for production builds |
