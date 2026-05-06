"""
main.py
-------
FastAPI application entry point for Veritas.

API surface
-----------
  POST  /api/verify/url          Submit a URL for analysis → {job_id}
  POST  /api/verify/file         Upload PDF/DOCX/TXT → {job_id}
  POST  /api/verify/text         Paste text → {job_id}
  GET   /api/job/{job_id}        Poll job status (fallback for non-WS clients)
  GET   /api/result/{task_id}    Legacy Celery task poll (backward compat)
  GET   /api/recent              Last N cached analyses
  GET   /api/health              Health check
  WS    /ws/{job_id}             WebSocket push — single result event
"""

import json
import os
import datetime
import logging

from fastapi import FastAPI, Form, UploadFile, File, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import models
from .database import SessionLocal, engine
from .agents.orchestrator import launch_url, launch_file, launch_text
from .ws import router as ws_router
from .middleware.rate_limit import limiter, rate_limit_handler, RateLimitExceeded

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# DB bootstrap
# ---------------------------------------------------------------------------
models.Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Veritas — AI News Analysis API",
    version="3.0.0",
    description=(
        "Agentic fact-checker inspired by Ground News. "
        "Analyses news articles for claim accuracy, source credibility, "
        "and cross-outlet political bias coverage."
    ),
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Rate limiter state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
_raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,null",
)
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket router
app.include_router(ws_router)


# ---------------------------------------------------------------------------
# DB session dependency
# ---------------------------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/api/health", tags=["system"])
async def health():
    return {"status": "ok", "version": "3.0.0"}


# ---------------------------------------------------------------------------
# Verify endpoints — each returns a job_id immediately
# ---------------------------------------------------------------------------

@app.post("/api/verify/url", tags=["analysis"])
@limiter.limit("10/minute")
async def start_url_verification(
    request: Request,
    url: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    Submit a URL for analysis.

    Checks the cache first (24-hour TTL). On a hit, returns the result
    immediately with status=SUCCESS. On a miss, launches the agentic
    pipeline and returns a job_id for WebSocket / polling.
    """
    cache_ttl = datetime.timedelta(days=1)
    cached = (
        db.query(models.VerifiedArticle)
        .filter(models.VerifiedArticle.url == url)
        .first()
    )
    if cached and (datetime.datetime.utcnow() - cached.checked_at < cache_ttl):
        logger.info("Cache hit for %s", url)
        return {"status": "SUCCESS", "result": json.loads(cached.analysis_json)}

    job_id = launch_url(url)
    return {"status": "PENDING", "job_id": job_id}


@app.post("/api/verify/file", tags=["analysis"])
@limiter.limit("10/minute")
async def start_file_verification(request: Request, file: UploadFile = File(...)):
    """Upload a PDF, DOCX, or plain-text file for analysis."""
    content = await file.read()
    job_id = launch_file(content, file.filename or "upload")
    return {"status": "PENDING", "job_id": job_id}


@app.post("/api/verify/text", tags=["analysis"])
@limiter.limit("10/minute")
async def start_text_verification(request: Request, text: str = Form(...)):
    """Submit pasted plain text for analysis."""
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Text body cannot be empty.")
    job_id = launch_text(text)
    return {"status": "PENDING", "job_id": job_id}


# ---------------------------------------------------------------------------
# Job status polling (fallback for non-WS clients)
# ---------------------------------------------------------------------------

@app.get("/api/job/{job_id}", tags=["analysis"])
@limiter.limit("60/minute")
async def get_job_status(request: Request, job_id: str, db: Session = Depends(get_db)):
    """
    Poll the status of an analysis job.

    Returns:
      - {"status": "pending"|"running"}                     — not done yet
      - {"status": "done", "result": {...}}                  — completed
      - {"status": "failed", "error": "..."}                 — errored
    """
    job = db.query(models.AnalysisJob).filter(models.AnalysisJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    if job.status in ("pending", "running"):
        return {"status": job.status}

    if job.status == "failed":
        return {"status": "failed", "error": job.error}

    # Done — retrieve the cached result
    if job.input_type == "url" and job.input_ref:
        cached = (
            db.query(models.VerifiedArticle)
            .filter(models.VerifiedArticle.url == job.input_ref)
            .first()
        )
        if cached:
            return {"status": "done", "result": json.loads(cached.analysis_json)}

    return {"status": "done", "result": None}


# ---------------------------------------------------------------------------
# Legacy Celery result poll (backward compat — kept for existing integrations)
# ---------------------------------------------------------------------------

@app.get("/api/result/{task_id}", tags=["analysis"], deprecated=True)
@limiter.limit("60/minute")
async def get_legacy_result(request: Request, task_id: str):
    """
    Deprecated: poll via /api/job/{job_id} instead.
    Retained for backward compatibility with the v2 frontend.
    """
    from celery.result import AsyncResult
    from .celery_app import celery as _celery

    task_result = AsyncResult(task_id, app=_celery)
    if task_result.ready():
        if task_result.successful():
            return {"status": "SUCCESS", "result": json.loads(task_result.get())}
        return {"status": "FAILURE", "error": str(task_result.info)}
    return {"status": "PENDING"}


# ---------------------------------------------------------------------------
# Recent analyses
# ---------------------------------------------------------------------------

@app.get("/api/recent", tags=["analysis"])
@limiter.limit("30/minute")
async def get_recent_analyses(
    request: Request,
    limit: int = 10,
    db: Session = Depends(get_db),
):
    """Return the most recently analysed URLs."""
    rows = (
        db.query(models.VerifiedArticle)
        .order_by(models.VerifiedArticle.checked_at.desc())
        .limit(min(limit, 50))
        .all()
    )
    return [
        {
            "url": r.url,
            "article_title": r.article_title,
            "checked_at": r.checked_at.isoformat(),
        }
        for r in rows
    ]
