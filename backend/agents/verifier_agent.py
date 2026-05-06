"""
verifier_agent.py
-----------------
Celery agent that verifies a single claim against evidence retrieved
from trusted sources.

Verification strategy (two-tier):
  1. Primary  — Ollama LLM (llama3.2:3b) via local REST API.
               Performs true semantic NLI with a structured JSON prompt.
  2. Fallback — Keyword-overlap heuristic from verifier.py.
               Used when Ollama is unreachable or times out.

One Celery task is created per claim, enabling full horizontal parallelism.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import requests as _requests

from ..celery_app import celery
from ..retriever import retrieve_from_trusted_sources
from ..verifier import nli_scores  # heuristic fallback

logger = logging.getLogger(__name__)

OLLAMA_HOST    = os.getenv("OLLAMA_HOST",    "http://localhost:11434")
OLLAMA_MODEL   = os.getenv("OLLAMA_MODEL",   "llama3.2:3b")   # default: 3B fits on CPU-only (≈2.2 GiB RAM)
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "60"))  # CPU inference is slower — 60s default
# Context window: our prompts are ≤500 tokens; 2048 halves KV-cache RAM vs the default 4096
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "2048"))

_NLI_SYSTEM = (
    "You are a rigorous fact-checking assistant. "
    "Given a CLAIM and a piece of EVIDENCE, classify the relationship. "
    "Reply with valid JSON only — no prose, no markdown."
)

_NLI_TEMPLATE = (
    "CLAIM: {claim}\n\n"
    "EVIDENCE: {evidence}\n\n"
    'Respond with exactly: {{"verdict": "supported"|"refuted"|"not_enough_info", '
    '"confidence": <0.0-1.0>, "reason": "<one sentence>"}}'
)


# ---------------------------------------------------------------------------
# LLM NLI helper
# ---------------------------------------------------------------------------

def _llm_nli(claim: str, evidence: str) -> dict[str, Any] | None:
    """
    Call Ollama for semantic NLI scoring.
    Returns parsed dict or None on any failure (triggers heuristic fallback).
    """
    prompt = _NLI_TEMPLATE.format(
        claim=claim[:400],       # keep prompt compact for 2048-ctx budget
        evidence=evidence[:800], # ~200 tokens — well within budget
    )
    payload = {
        "model": OLLAMA_MODEL,
        "system": _NLI_SYSTEM,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.0,       # deterministic for fact-checking
            "num_ctx": OLLAMA_NUM_CTX, # cap context to save RAM on CPU-only hosts
        },
    }
    try:
        resp = _requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json=payload,
            timeout=OLLAMA_TIMEOUT,
        )
        resp.raise_for_status()
        raw = resp.json().get("response", "{}")
        parsed = json.loads(raw)

        # Validate required fields
        if "verdict" not in parsed or parsed["verdict"] not in (
            "supported", "refuted", "not_enough_info"
        ):
            logger.warning("Ollama returned unexpected verdict field: %s", parsed)
            return None

        parsed["confidence"] = float(parsed.get("confidence", 0.5))
        parsed["reason"] = str(parsed.get("reason", ""))
        return parsed

    except Exception as exc:
        logger.warning("Ollama NLI failed (%s). Using heuristic fallback.", exc)
        return None


def _heuristic_nli(claim: str, evidence: str) -> dict[str, Any]:
    """Keyword-overlap heuristic fallback (from verifier.py)."""
    scores = nli_scores(evidence, claim)
    if scores["entailment"] >= 0.55:
        verdict, confidence = "supported", scores["entailment"]
    elif scores["contradiction"] >= 0.55:
        verdict, confidence = "refuted", scores["contradiction"]
    else:
        verdict, confidence = "not_enough_info", scores["neutral"]

    return {
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "reason": "Heuristic keyword-overlap NLI (Ollama unavailable).",
        "method": "heuristic",
    }


# ---------------------------------------------------------------------------
# Celery task
# ---------------------------------------------------------------------------

@celery.task(queue="default", name="agents.verifier_agent", max_retries=1)
def run_verifier(claim: str) -> dict:
    """
    Verify a single claim. Returns a verdict dict ready for the aggregator.

    Returns:
        {
            "claim": str,
            "verdict": "supported"|"refuted"|"not_enough_info",
            "evidence": [
                {
                    "title": str,
                    "url": str,
                    "verdict": str,
                    "confidence": float,
                    "reason": str,
                    "method": "llm"|"heuristic",
                }
            ]
        }
    """
    evidences = retrieve_from_trusted_sources(claim, top_n=3)
    evidence_results = []
    verdict_weights = {"supported": 0.0, "refuted": 0.0, "not_enough_info": 0.0}

    for ev in evidences:
        snippet = (ev.get("content") or "")[:1200]

        # Primary: Ollama LLM
        result = _llm_nli(claim, snippet)
        method = "llm"

        if result is None:
            # Fallback: heuristic
            result = _heuristic_nli(claim, snippet)
            method = "heuristic"

        verdict_weights[result["verdict"]] += result["confidence"]
        evidence_results.append({
            "title": ev.get("title", ""),
            "url": ev.get("url", ""),
            "verdict": result["verdict"],
            "confidence": result["confidence"],
            "reason": result.get("reason", ""),
            "method": method,
        })

    # Aggregate: confidence-weighted majority
    if not evidence_results:
        final_verdict = "not_enough_info"
    elif verdict_weights["refuted"] > verdict_weights["supported"] and verdict_weights["refuted"] > 0.4:
        final_verdict = "refuted"
    elif verdict_weights["supported"] > verdict_weights["refuted"] and verdict_weights["supported"] > 0.4:
        final_verdict = "supported"
    else:
        final_verdict = "not_enough_info"

    return {
        "claim": claim,
        "verdict": final_verdict,
        "evidence": evidence_results,
    }
