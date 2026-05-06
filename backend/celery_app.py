"""
celery_app.py
-------------
Celery application factory for Veritas.

Queues
------
  high    — User-facing tasks where someone is actively waiting (URL analysis, WS push)
  default — Background steps (verifier fan-out, coverage search)
  low     — Housekeeping / batch re-analysis (reserved for future use)
"""

import os
from dotenv import load_dotenv
from celery import Celery

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery = Celery(
    "veritas",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "backend.worker",           # backward-compat shims
        "backend.agents.parser_agent",
        "backend.agents.source_bias_agent",
        "backend.agents.coverage_agent",
        "backend.agents.claims_agent",
        "backend.agents.verifier_agent",
        "backend.agents.aggregator_agent",
        "backend.agents.orchestrator",
    ],
)

celery.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # Route tasks to named queues
    task_routes={
        "agents.parser_agent":      {"queue": "high"},
        "agents.source_bias_agent": {"queue": "high"},
        "agents.phase2_callback":   {"queue": "high"},
        "agents.aggregator_agent":  {"queue": "high"},
        "agents.coverage_agent":    {"queue": "default"},
        "agents.verifier_agent":    {"queue": "default"},
        "agents.claims_agent":      {"queue": "default"},
        # Legacy tasks keep the default queue
        "backend.worker.analyze_url_task":  {"queue": "high"},
        "backend.worker.analyze_file_task": {"queue": "default"},
        "backend.worker.analyze_text_task": {"queue": "default"},
    },
    # Prevent a single slow task from starving others
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Result TTL — keep results in Redis for 24 hours
    result_expires=86400,
)