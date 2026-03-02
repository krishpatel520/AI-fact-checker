# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.0.0] — 2026-03-02

### Added
- **Vite + React + Tailwind CSS** frontend replacing the CDN-based single-file prototype
- **Celery + Redis** async task queue for non-blocking article analysis
- **File upload** support: PDF, DOCX, and plain text in addition to URLs
- **Text input** mode: paste any article text directly into the UI
- **Source bias database** covering 3 000+ media outlets (political lean + factuality)
- **Coverage map**: automatically finds how multiple outlets cover the same story
- **SQLite caching**: repeated requests for the same URL return instantly from cache
- **Docker Compose** setup: `docker compose up --build` starts the full stack
- **Configurable CORS** via `ALLOWED_ORIGINS` environment variable
- **GitHub Actions CI** pipeline: runs pytest on every push and pull request
- `CONTRIBUTING.md`, `SECURITY.md`, `CHANGELOG.md`, `LICENSE`, `.env.example`

### Changed
- Frontend dev server proxies `/api` to the backend — no more manual CORS configuration during development
- Celery worker uses `gevent` pool for efficient I/O concurrency
- Backend `Dockerfile` uses `python:3.11-slim` with spaCy model pre-downloaded

### Removed
- Old monolithic `index.html` CDN-based frontend (replaced by Vite SPA)

---

## [1.0.0] — 2026-02-01

### Added
- Initial proof-of-concept: single `index.html` with CDN React and vanilla FastAPI
- Basic URL scraping via `newspaper3k`
- Claim extraction with spaCy
- Heuristic NLI verification using Hugging Face `transformers`
- Serper.dev evidence retrieval
- SQLAlchemy + SQLite persistence
