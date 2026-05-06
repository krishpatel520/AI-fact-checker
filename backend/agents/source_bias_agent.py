"""
source_bias_agent.py
--------------------
Celery agent that resolves political bias, factual reporting rating,
and credibility metadata for a given URL's domain.
Wraps source_analyzer.py — purely local lookup, no network calls.
"""

from ..celery_app import celery
from ..source_analyzer import get_source_analysis


@celery.task(queue="high", name="agents.source_bias_agent")
def run_source_bias(url: str) -> dict:
    """
    Look up media bias and credibility data for the given URL.

    Args:
        url: Article URL (domain is extracted internally).

    Returns:
        dict with keys: domain, bias, political_leaning_score,
                        factual_reporting, country, logo_url, description
    """
    return get_source_analysis(url)
