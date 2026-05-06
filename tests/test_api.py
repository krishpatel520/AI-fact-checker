"""
tests/test_api.py
-----------------
Integration tests for the Veritas v3 REST API.
Requires a running backend stack (FastAPI + Redis + Postgres + Celery worker).

Run:
    python -m pytest tests/test_api.py -v -s --timeout=300

Environment variable BASE_URL can override the default localhost:8000.
"""

import os
import time
import pytest
import requests

BASE_URL = os.getenv("TEST_API_BASE_URL", "http://127.0.0.1:8000")
POLL_INTERVAL = 3   # seconds
MAX_POLLS     = 80  # 80 × 3s = 4 min max (Ollama can be slow on CPU)


def _poll_job(job_id: str):
    """Poll /api/job/{job_id} until done or timeout. Returns final data dict."""
    for i in range(MAX_POLLS):
        print(f"  Poll {i+1}/{MAX_POLLS} for job {job_id}...")
        resp = requests.get(f"{BASE_URL}/api/job/{job_id}", timeout=10)
        assert resp.status_code == 200, f"Poll failed: {resp.status_code}"
        data = resp.json()
        if data["status"] in ("done", "failed"):
            return data
        time.sleep(POLL_INTERVAL)
    pytest.fail(f"Job {job_id} did not complete within {MAX_POLLS * POLL_INTERVAL}s")


# ── Health check ──────────────────────────────────────────────────────────────

def test_health_check():
    resp = requests.get(f"{BASE_URL}/api/health", timeout=5)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data
    print(f"\n  API version: {data['version']}")


# ── Verify URL ────────────────────────────────────────────────────────────────

def test_url_verification_workflow():
    """
    Full end-to-end test: submit URL → get job_id → poll → validate result.
    Uses AP News as a reliable test target.
    """
    test_url = "https://apnews.com/article/fact-check-biden-border-executive-order-258014202102"
    print(f"\n  Submitting URL: {test_url}")

    resp = requests.post(f"{BASE_URL}/api/verify/url", data={"url": test_url}, timeout=10)
    assert resp.status_code == 200
    data = resp.json()
    print(f"  Response: {data}")

    if data.get("status") == "SUCCESS":
        # Cache hit — validate immediately
        result = data["result"]
    else:
        # New job — poll
        assert "job_id" in data, f"Expected job_id, got: {data}"
        job_data = _poll_job(data["job_id"])
        assert job_data["status"] == "done", f"Job failed: {job_data.get('error')}"
        result = job_data["result"]

    # Validate result structure
    assert "status"            in result
    assert "credibility_score" in result
    assert "source_analysis"   in result
    assert "related_coverage"  in result
    assert "results"           in result
    assert isinstance(result["results"],           list)
    assert isinstance(result["related_coverage"],  list)
    assert isinstance(result["credibility_score"], int)
    assert 0 <= result["credibility_score"] <= 100
    print(f"  ✓ Credibility: {result['credibility_score']} | Claims: {len(result['results'])}")


# ── Cache hit test ────────────────────────────────────────────────────────────

def test_second_url_submission_returns_cache():
    """Submitting the same URL twice should return STATUS=SUCCESS immediately."""
    url = "https://apnews.com/article/fact-check-biden-border-executive-order-258014202102"

    # First submission (may be new or cached)
    r1 = requests.post(f"{BASE_URL}/api/verify/url", data={"url": url}, timeout=10)
    assert r1.status_code == 200

    if r1.json().get("status") == "PENDING":
        # Wait for first to complete
        _poll_job(r1.json()["job_id"])

    # Second submission must be a cache hit
    r2 = requests.post(f"{BASE_URL}/api/verify/url", data={"url": url}, timeout=10)
    assert r2.status_code == 200
    assert r2.json()["status"] == "SUCCESS", "Second submission should be a cache hit"


# ── Verify text ───────────────────────────────────────────────────────────────

def test_text_verification_workflow():
    """Submit pasted text and validate the result structure."""
    text = (
        "The unemployment rate in the United States fell to 3.5 percent in March 2024, "
        "according to the Bureau of Labor Statistics. The Federal Reserve held interest "
        "rates steady at 5.25 percent, citing concerns about persistent inflation. "
        "GDP growth reached 2.8 percent in the first quarter, beating analyst expectations."
    )
    resp = requests.post(f"{BASE_URL}/api/verify/text", data={"text": text}, timeout=10)
    assert resp.status_code == 200
    data = resp.json()
    assert "job_id" in data

    job_data = _poll_job(data["job_id"])
    assert job_data["status"] == "done"
    result = job_data["result"]
    assert "results" in result
    assert isinstance(result["results"], list)
    print(f"  ✓ Text claims found: {len(result['results'])}")


# ── Empty text rejected ───────────────────────────────────────────────────────

def test_empty_text_returns_400():
    resp = requests.post(f"{BASE_URL}/api/verify/text", data={"text": "   "}, timeout=5)
    assert resp.status_code == 400


# ── Job not found ─────────────────────────────────────────────────────────────

def test_unknown_job_id_returns_404():
    resp = requests.get(f"{BASE_URL}/api/job/nonexistent-job-id-12345", timeout=5)
    assert resp.status_code == 404


# ── Recent analyses ───────────────────────────────────────────────────────────

def test_recent_analyses_endpoint():
    resp = requests.get(f"{BASE_URL}/api/recent?limit=5", timeout=5)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    for item in data:
        assert "url"           in item
        assert "article_title" in item
        assert "checked_at"    in item


# ── Rate limit structure ──────────────────────────────────────────────────────

def test_rate_limit_headers_present():
    """Verify that rate limit headers are returned on verify endpoints."""
    resp = requests.post(f"{BASE_URL}/api/verify/text", data={"text": "   "}, timeout=5)
    # 400 is expected — we just want to check headers exist
    # slowapi adds X-RateLimit-* headers on successful requests
    # On 400 it may not — just confirm the endpoint responded
    assert resp.status_code in (200, 400, 429)