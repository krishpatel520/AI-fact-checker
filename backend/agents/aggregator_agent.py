"""
aggregator_agent.py
-------------------
Final Celery agent in the pipeline. Receives all partial results from
Phase 2 of the chord (verifier results + coverage list), assembles the
canonical analysis payload, writes it to PostgreSQL, and publishes the
result to the Redis pub/sub channel so the WebSocket endpoint can push
it to the waiting browser client.
"""

from __future__ import annotations

import datetime
import json
import logging
import os

import redis

from ..celery_app import celery

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


# ---------------------------------------------------------------------------
# Scoring helpers (same logic as original worker.py)
# ---------------------------------------------------------------------------

def _doc_status(results: list) -> str:
    if not results:
        return "not_enough_info"
    return (
        "clean_document"
        if all(r["verdict"] != "refuted" for r in results)
        else "inaccuracies_found"
    )


def _credibility_score(results: list) -> int:
    if not results:
        return 50
    supported = sum(1 for r in results if r["verdict"] == "supported")
    refuted = sum(1 for r in results if r["verdict"] == "refuted")
    total = len(results)
    score = 50 + int(40 * (supported / total)) - int(40 * (refuted / total))
    return max(0, min(100, score))


# ---------------------------------------------------------------------------
# DB write-back
# ---------------------------------------------------------------------------

def _write_to_db(url: str, article_title: str, analysis_json: str) -> None:
    """Persist analysis result to PostgreSQL. Upserts by URL."""
    try:
        from ..database import SessionLocal
        from .. import models

        db = SessionLocal()
        existing = (
            db.query(models.VerifiedArticle)
            .filter(models.VerifiedArticle.url == url)
            .first()
        )
        now = datetime.datetime.utcnow()
        if existing:
            existing.analysis_json = analysis_json
            existing.article_title = article_title
            existing.checked_at = now
        else:
            db.add(
                models.VerifiedArticle(
                    url=url,
                    article_title=article_title,
                    analysis_json=analysis_json,
                )
            )
        db.commit()
        db.close()
        logger.info("DB write-back OK for %s", url)
    except Exception as exc:
        logger.error("DB write-back failed: %s", exc)


def _update_job_status(job_id: str, status: str, error: str | None = None) -> None:
    """Update the AnalysisJob row status."""
    try:
        from ..database import SessionLocal
        from .. import models

        db = SessionLocal()
        job = db.query(models.AnalysisJob).filter(models.AnalysisJob.id == job_id).first()
        if job:
            job.status = status
            job.completed_at = datetime.datetime.utcnow()
            if error:
                job.error = error
            db.commit()
        db.close()
    except Exception as exc:
        logger.warning("Job status update failed: %s", exc)


# ---------------------------------------------------------------------------
# WebSocket push
# ---------------------------------------------------------------------------

def _publish_ws(job_id: str, payload: dict) -> None:
    """Publish final payload to Redis pub/sub so the WS endpoint can push it."""
    try:
        r = redis.from_url(REDIS_URL)
        r.publish(f"job:{job_id}", json.dumps(payload))
        r.close()
        logger.info("WS event published for job %s", job_id)
    except Exception as exc:
        logger.warning("Redis publish failed: %s", exc)


# ---------------------------------------------------------------------------
# Celery task
# ---------------------------------------------------------------------------

@celery.task(queue="high", name="agents.aggregator_agent")
def run_aggregator(
    phase2_results: list,
    url: str,
    job_id: str,
    parser_result: dict,
    source_info: dict,
    claims: list,
) -> str:
    """
    Assemble the final analysis payload from all agent outputs.

    Args:
        phase2_results: Celery chord results list.
                        Layout: [verifier_result_0, ..., verifier_result_n-1, coverage_list]
        url:            Original article URL (or "" for text/file).
        job_id:         UUID for this analysis job.
        parser_result:  Output of run_parser.
        source_info:    Output of run_source_bias.
        claims:         List of claim strings (used to correlate verifier results).

    Returns:
        JSON string of the final analysis (stored as Celery task result too).
    """
    num_claims = len(claims)

    # Split results: verifier outputs come first, coverage is last
    verifier_outputs = phase2_results[:num_claims]
    coverage = phase2_results[num_claims] if len(phase2_results) > num_claims else []

    # Normalise coverage to always be a list
    if not isinstance(coverage, list):
        coverage = []

    article_title = parser_result.get("title", "") or source_info.get("domain", "Unknown")
    publish_date = parser_result.get("publish_date", "")

    final_payload = {
        "status": _doc_status(verifier_outputs),
        "credibility_score": _credibility_score(verifier_outputs),
        "article_title": article_title,
        "publish_date": publish_date,
        "source_analysis": source_info,
        "related_coverage": coverage,
        "results": verifier_outputs,
        "text": parser_result.get("text", ""),
    }

    json_str = json.dumps(final_payload)

    # Persist to DB (URL analyses only)
    if url:
        _write_to_db(url, article_title, json_str)

    # Update job record
    _update_job_status(job_id, "done")

    # Push to WebSocket clients
    ws_payload = {**final_payload, "job_id": job_id, "status_event": "done"}
    ws_payload.pop("text", None)  # omit full text from WS push (large)
    _publish_ws(job_id, ws_payload)

    logger.info("Analysis complete for job %s", job_id)
    return json_str
