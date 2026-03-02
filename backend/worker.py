"""
worker.py
---------
Celery background tasks for the full analysis pipeline.
Both URL and file tasks produce a rich JSON payload that includes:
  - source_analysis   (bias, factuality, political spectrum data)
  - related_coverage  (Ground News-style multi-outlet panel)
  - results           (per-claim verdict + evidence)
  - article_title, publish_date, text
"""

import json
import datetime
from .celery_app import celery

from .parser import (
    extract_text_from_url,
    extract_text_from_pdf_bytes,
    extract_text_from_docx_bytes,
)
from .claims import extract_candidate_claims
from .retriever import retrieve_from_trusted_sources
from .verifier import aggregate_verdict_from_evidence
from .source_analyzer import get_source_analysis
from .news_aggregator import find_related_coverage


def _run_claim_pipeline(text: str) -> list:
    """
    Extract claims from text and verify each against trusted sources.
    Returns a list of {claim, verdict, evidence} dicts.
    """
    claims = extract_candidate_claims(text) if text else []
    results = []
    for claim in claims:
        evidences = retrieve_from_trusted_sources(claim, top_n=3)
        verdict, evidence_results = aggregate_verdict_from_evidence(claim, evidences)
        results.append({
            "claim": claim,
            "verdict": verdict,
            "evidence": evidence_results,
        })
    return results


def _doc_status(results: list) -> str:
    if not results:
        return "not_enough_info"
    return (
        "clean_document"
        if all(r["verdict"] != "refuted" for r in results)
        else "inaccuracies_found"
    )


def _credibility_score(results: list) -> int:
    """Compute a 0–100 credibility score based on verdict distribution."""
    if not results:
        return 50  # neutral when no claims found
    supported = sum(1 for r in results if r["verdict"] == "supported")
    refuted = sum(1 for r in results if r["verdict"] == "refuted")
    total = len(results)
    # Start at 50, boost for supported, penalise for refuted
    score = 50 + int(40 * (supported / total)) - int(40 * (refuted / total))
    return max(0, min(100, score))


# ---------------------------------------------------------------------------
# URL task
# ---------------------------------------------------------------------------

@celery.task
def analyze_url_task(url: str):
    """Full analysis pipeline for a URL."""
    print(f"🔬 Starting URL analysis: {url}")

    # 1. Source metadata
    source_info = get_source_analysis(url)

    # 2. Extract article content (returns dict now)
    extracted = extract_text_from_url(url)
    text = extracted.get("text", "")
    article_title = extracted.get("title", "") or source_info.get("domain", "")
    publish_date = extracted.get("publish_date", "")

    # 3. Related coverage (uses article title to find same story elsewhere)
    related_coverage = find_related_coverage(article_title, url, top_n=10)

    # 4. Claim verification pipeline
    results = _run_claim_pipeline(text)

    # 5. Assemble final payload
    final_analysis = {
        "status": _doc_status(results),
        "credibility_score": _credibility_score(results),
        "article_title": article_title,
        "publish_date": publish_date,
        "source_analysis": source_info,
        "related_coverage": related_coverage,
        "results": results,
        "text": text,
    }

    # 6. Write back to DB cache (import here to avoid circular imports in Celery)
    try:
        from .database import SessionLocal
        from . import models
        db = SessionLocal()
        existing = db.query(models.VerifiedArticle).filter(models.VerifiedArticle.url == url).first()
        json_str = json.dumps(final_analysis)
        if existing:
            existing.analysis_json = json_str
            existing.article_title = article_title
            existing.checked_at = datetime.datetime.utcnow()
        else:
            db.add(models.VerifiedArticle(
                url=url,
                article_title=article_title,
                analysis_json=json_str,
            ))
        db.commit()
        db.close()
        print(f"💾 Cached result for {url}")
    except Exception as e:
        print(f"⚠️  DB write-back failed: {e}")

    print(f"✅ URL analysis complete: {url}")
    return json.dumps(final_analysis)


# ---------------------------------------------------------------------------
# File task
# ---------------------------------------------------------------------------

@celery.task
def analyze_file_task(content: bytes, filename: str):
    """Full analysis pipeline for an uploaded file."""
    print(f"🔬 Starting file analysis: {filename}")

    lower_name = filename.lower()
    if lower_name.endswith(".pdf"):
        extracted = extract_text_from_pdf_bytes(content)
    elif lower_name.endswith((".docx", ".doc")):
        extracted = extract_text_from_docx_bytes(content)
    else:
        extracted = {"text": content.decode(errors="ignore"), "title": "", "publish_date": ""}

    text = extracted.get("text", "")
    article_title = extracted.get("title", "") or filename

    # No URL for file uploads, so no source bias or related coverage
    source_info = {
        "domain": f"Uploaded: {filename}",
        "bias": "N/A",
        "political_leaning_score": None,
        "factual_reporting": "N/A",
        "country": None,
        "logo_url": None,
        "description": "Uploaded document",
    }
    related_coverage = []

    results = _run_claim_pipeline(text)

    final_analysis = {
        "status": _doc_status(results),
        "credibility_score": _credibility_score(results),
        "article_title": article_title,
        "publish_date": "",
        "source_analysis": source_info,
        "related_coverage": related_coverage,
        "results": results,
        "text": text,
    }

    print(f"✅ File analysis complete: {filename}")
    return json.dumps(final_analysis)


# ---------------------------------------------------------------------------
# Text task (plain-text paste)
# ---------------------------------------------------------------------------

@celery.task
def analyze_text_task(text: str):
    """Full analysis pipeline for pasted plain text."""
    print(f"🔬 Starting text analysis ({len(text)} chars)")

    # Derive a pseudo-title from the first sentence
    first_sentence = text.strip().split(".")[0][:120]
    article_title = first_sentence or "Pasted Text"

    source_info = {
        "domain": "Pasted Text",
        "bias": "N/A",
        "political_leaning_score": None,
        "factual_reporting": "N/A",
        "country": None,
        "logo_url": None,
        "description": "User-pasted text",
    }

    # Attempt related coverage using the pseudo-title
    related_coverage = find_related_coverage(article_title, "", top_n=10)

    results = _run_claim_pipeline(text)

    final_analysis = {
        "status": _doc_status(results),
        "credibility_score": _credibility_score(results),
        "article_title": article_title,
        "publish_date": "",
        "source_analysis": source_info,
        "related_coverage": related_coverage,
        "results": results,
        "text": text,
    }

    print(f"✅ Text analysis complete")
    return json.dumps(final_analysis)
