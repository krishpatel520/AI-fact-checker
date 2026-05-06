"""
claims_agent.py
---------------
Celery agent that extracts candidate factual claims from article text
using spaCy NLP (named-entity + root-verb heuristic).
"""

from ..celery_app import celery
from ..claims import extract_candidate_claims


@celery.task(queue="default", name="agents.claims_agent")
def run_claims(text: str, max_claims: int = 20) -> list:
    """
    Extract verifiable claim sentences from article text.

    Args:
        text:       Full article body.
        max_claims: Maximum number of claims to extract (default 20).
                    Capped lower than the original 50 to control LLM costs.

    Returns:
        List of claim strings.
    """
    if not text or not text.strip():
        return []
    return extract_candidate_claims(text, max_claims=max_claims)
