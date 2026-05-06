"""
worker.py
---------
Backward-compatible Celery task shims.

The three original task names (analyze_url_task, analyze_file_task,
analyze_text_task) are preserved so that any existing callers or
queued messages continue to work. Internally they now delegate to
the new agentic orchestrator and return the job_id.

NOTE: The main analysis logic no longer lives here — see backend/agents/.
"""

import json
import logging

from .celery_app import celery
from .agents.orchestrator import launch_url, launch_file, launch_text

logger = logging.getLogger(__name__)


@celery.task(name="backend.worker.analyze_url_task", queue="high")
def analyze_url_task(url: str) -> str:
    """Legacy shim — delegates to orchestrator.launch_url."""
    job_id = launch_url(url)
    logger.info("analyze_url_task delegated → job_id=%s", job_id)
    return json.dumps({"job_id": job_id, "status": "PENDING"})


@celery.task(name="backend.worker.analyze_file_task", queue="default")
def analyze_file_task(content: bytes, filename: str) -> str:
    """Legacy shim — delegates to orchestrator.launch_file."""
    raw = bytes(content) if isinstance(content, list) else content
    job_id = launch_file(raw, filename)
    logger.info("analyze_file_task delegated → job_id=%s", job_id)
    return json.dumps({"job_id": job_id, "status": "PENDING"})


@celery.task(name="backend.worker.analyze_text_task", queue="default")
def analyze_text_task(text: str) -> str:
    """Legacy shim — delegates to orchestrator.launch_text."""
    job_id = launch_text(text)
    logger.info("analyze_text_task delegated → job_id=%s", job_id)
    return json.dumps({"job_id": job_id, "status": "PENDING"})
