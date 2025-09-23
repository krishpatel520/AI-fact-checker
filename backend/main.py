import json
import datetime
from fastapi import FastAPI, Form, UploadFile, File, Depends
from sqlalchemy.orm import Session
from celery.result import AsyncResult

# --- Import database components and worker tasks ---
from . import models
from .database import SessionLocal, engine
from .worker import analyze_url_task, analyze_file_task

# --- ADD THIS: Import the central Celery app instance ---
from .celery_app import celery

# Create database tables on startup
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Trusted Claim Verifier API")

# Dependency to get a DB session for each request
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Endpoint to START URL analysis (Your caching logic is preserved) ---
@app.post("/api/verify/url")
async def start_url_verification(url: str = Form(...), db: Session = Depends(get_db)):
    """
    Receives a URL. First, it checks the database for a recent, cached result.
    If none is found, it sends the URL to the background worker and returns a task ID.
    """
    cache_duration = datetime.timedelta(days=1)
    cached_article = db.query(models.VerifiedArticle).filter(models.VerifiedArticle.url == url).first()

    if cached_article and (datetime.datetime.utcnow() - cached_article.checked_at < cache_duration):
        print(f"✅ Returning cached result for {url}")
        # Note: The cached result is already a complete analysis object
        return json.loads(cached_article.analysis_json)

    print(f"🔄 No fresh cache found. Starting new analysis for {url}")
    task = analyze_url_task.delay(url)
    return {"status": "PENDING", "task_id": task.id}

# --- Endpoint to START File analysis (Preserved) ---
@app.post("/api/verify/file")
async def start_file_verification(file: UploadFile = File(...)):
    """
    Receives a file, sends its content to the background worker, and
    immediately returns a task ID.
    """
    content = await file.read()
    filename = file.filename
    task = analyze_file_task.delay(content, filename)
    return {"status": "PENDING", "task_id": task.id}

# --- Endpoint to GET the result of any task ---
@app.get("/api/result/{task_id}")
async def get_verification_result(task_id: str):
    """
    Checks the status of a task (URL or File). Returns the result if it's ready.
    """
    # --- CRITICAL CHANGE: Pass the 'app' context to AsyncResult ---
    task_result = AsyncResult(task_id, app=celery)
    
    if task_result.ready():
        if task_result.successful():
            # The result is a JSON string, so we parse it
            return {"status": "SUCCESS", "result": json.loads(task_result.get())}
        else:
            return {"status": "FAILURE", "error": str(task_result.info)}
    else:
        return {"status": "PENDING"}