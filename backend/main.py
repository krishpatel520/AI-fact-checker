"""
main.py
-------
FastAPI application entry point.
Exposes endpoints to submit articles for analysis and retrieve results.
"""

import json
import os
import datetime
from fastapi import FastAPI, Form, UploadFile, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from celery.result import AsyncResult

from . import models
from .database import SessionLocal, engine
from .worker import analyze_url_task, analyze_file_task, analyze_text_task
from .celery_app import celery

# Create DB tables on startup
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Veritas – AI News Analysis API", version="2.0.0")

# ---------------------------------------------------------------------------
# CORS – origins are configured via the ALLOWED_ORIGINS env variable.
# For local dev, the Vite proxy handles /api → :8000, so CORS is mostly
# needed for direct file:// access or non-proxied deployments.
# ---------------------------------------------------------------------------
_raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5500,http://127.0.0.1:5500,http://localhost:8000,null",
)
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}


# ---------------------------------------------------------------------------
# Submit URL for analysis (with caching)
# ---------------------------------------------------------------------------
@app.post("/api/verify/url")
async def start_url_verification(
    url: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    Check for a fresh cached result first. If found, return it immediately.
    Otherwise, queue a background Celery task and return a task_id.
    """
    cache_duration = datetime.timedelta(days=1)
    cached = (
        db.query(models.VerifiedArticle)
        .filter(models.VerifiedArticle.url == url)
        .first()
    )

    if cached and (datetime.datetime.utcnow() - cached.checked_at < cache_duration):
        print(f"✅ Cache hit for {url}")
        return {
            "status": "SUCCESS",
            "result": json.loads(cached.analysis_json),
        }

    print(f"🔄 Queuing new analysis for {url}")
    task = analyze_url_task.delay(url)
    return {"status": "PENDING", "task_id": task.id}


# ---------------------------------------------------------------------------
# Submit file for analysis
# ---------------------------------------------------------------------------
@app.post("/api/verify/file")
async def start_file_verification(file: UploadFile = File(...)):
    """Receive a file, queue analysis, return task_id."""
    content = await file.read()
    filename = file.filename
    task = analyze_file_task.delay(content, filename)
    return {"status": "PENDING", "task_id": task.id}


# ---------------------------------------------------------------------------
# Submit plain text for analysis
# ---------------------------------------------------------------------------
@app.post("/api/verify/text")
async def start_text_verification(text: str = Form(...)):
    """Receive pasted text, queue analysis, return task_id."""
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Text body cannot be empty.")
    task = analyze_text_task.delay(text)
    return {"status": "PENDING", "task_id": task.id}


# ---------------------------------------------------------------------------
# Poll for task result
# ---------------------------------------------------------------------------
@app.get("/api/result/{task_id}")
async def get_verification_result(task_id: str):
    """Return SUCCESS/FAILURE/PENDING for a queued task."""
    task_result = AsyncResult(task_id, app=celery)

    if task_result.ready():
        if task_result.successful():
            return {
                "status": "SUCCESS",
                "result": json.loads(task_result.get()),
            }
        else:
            return {"status": "FAILURE", "error": str(task_result.info)}

    return {"status": "PENDING"}


# ---------------------------------------------------------------------------
# Get recent cached analyses (optional convenience endpoint)
# ---------------------------------------------------------------------------
@app.get("/api/recent")
async def get_recent_analyses(limit: int = 10, db: Session = Depends(get_db)):
    """Return the most recently analysed URLs."""
    rows = (
        db.query(models.VerifiedArticle)
        .order_by(models.VerifiedArticle.checked_at.desc())
        .limit(limit)
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
