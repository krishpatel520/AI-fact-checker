"""
orchestrator.py
---------------
Top-level Celery orchestrator for the Veritas agentic pipeline.

Execution graph (two-phase parallel chord):

  Phase 1 — PARALLEL:
    ┌─ run_parser(url)       → parser_result
    └─ run_source_bias(url)  → source_info

  Phase 2 — PARALLEL (dispatched by phase2_callback after Phase 1):
    ┌─ run_verifier(claim_0) ┐
    ├─ run_verifier(claim_1) ┤  → verifier_outputs[0..n-1]
    ├─ ...                   ┘
    └─ run_coverage(title, url) → coverage_list

  Aggregation:
    run_aggregator receives [*verifier_outputs, coverage_list]
    and assembles the final JSON payload.

Three entry points (URL / file / text) all funnel through this graph.
"""

from __future__ import annotations

import datetime
import json
import logging
import uuid

from celery import chord, group

from ..celery_app import celery
from ..claims import extract_candidate_claims

from .parser_agent import run_parser
from .source_bias_agent import run_source_bias
from .coverage_agent import run_coverage
from .verifier_agent import run_verifier
from .aggregator_agent import run_aggregator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Job status helpers
# ---------------------------------------------------------------------------

def _create_job(job_id: str, input_type: str, input_ref: str) -> None:
    try:
        from ..database import SessionLocal
        from .. import models

        db = SessionLocal()
        db.add(
            models.AnalysisJob(
                id=job_id,
                status="pending",
                input_type=input_type,
                input_ref=input_ref[:500],
            )
        )
        db.commit()
        db.close()
    except Exception as exc:
        logger.error("Failed to create AnalysisJob: %s", exc)


def _set_job_running(job_id: str) -> None:
    try:
        from ..database import SessionLocal
        from .. import models

        db = SessionLocal()
        job = db.query(models.AnalysisJob).filter(models.AnalysisJob.id == job_id).first()
        if job:
            job.status = "running"
            db.commit()
        db.close()
    except Exception as exc:
        logger.warning("Could not set job running: %s", exc)


# ---------------------------------------------------------------------------
# Phase 2 callback (intermediate step after Phase 1 chord completes)
# ---------------------------------------------------------------------------

@celery.task(queue="high", name="agents.phase2_callback")
def phase2_callback(phase1_results: list, url: str, job_id: str,
                    input_type: str, file_content=None, filename: str = "") -> None:
    """
    Receives [parser_result, source_info] from the Phase 1 chord,
    extracts claims, and dispatches the Phase 2 parallel chord.
    """
    _set_job_running(job_id)

    parser_result, source_info = phase1_results
    text = parser_result.get("text", "")
    title = parser_result.get("title", "") or source_info.get("domain", "")

    # Extract claims synchronously (fast — pure Python spaCy, no I/O)
    claims = extract_candidate_claims(text, max_claims=20) if text.strip() else []

    # Build Phase 2 task group: one verifier per claim + one coverage search
    verifier_tasks = [run_verifier.s(claim) for claim in claims]
    coverage_task = run_coverage.s(title, url)

    # If no claims, still run coverage; aggregator handles empty verifier list
    all_tasks = verifier_tasks + [coverage_task]

    aggregator_callback = run_aggregator.s(
        url=url,
        job_id=job_id,
        parser_result=parser_result,
        source_info=source_info,
        claims=claims,
    )

    chord(group(*all_tasks), aggregator_callback).delay()
    logger.info("Phase 2 dispatched for job %s: %d claims + coverage", job_id, len(claims))


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

def _launch(input_ref: str, input_type: str,
            file_content=None, filename: str = "") -> str:
    """
    Common launch logic for all three input types.
    Creates the AnalysisJob, kicks off Phase 1 chord, returns job_id.
    """
    job_id = str(uuid.uuid4())
    _create_job(job_id, input_type, input_ref)

    # Phase 1: parse + source bias in parallel
    phase1 = chord(
        group(
            run_parser.s(input_ref, input_type, file_content, filename),
            run_source_bias.s(input_ref if input_type == "url" else ""),
        ),
        phase2_callback.s(
            url=input_ref if input_type == "url" else "",
            job_id=job_id,
            input_type=input_type,
            file_content=file_content,
            filename=filename,
        ),
    )
    phase1.delay()
    logger.info("Pipeline launched — job_id=%s type=%s", job_id, input_type)
    return job_id


def launch_url(url: str) -> str:
    """Start analysis for a news article URL. Returns job_id."""
    return _launch(url, "url")


def launch_file(content: bytes, filename: str) -> str:
    """Start analysis for an uploaded file. Returns job_id."""
    # Celery JSON serialiser can't handle raw bytes — convert to list[int]
    return _launch(filename, "file", list(content), filename)


def launch_text(text: str) -> str:
    """Start analysis for pasted plain text. Returns job_id."""
    return _launch(text[:200], "text", None, "")
