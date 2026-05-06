"""
coverage_agent.py
-----------------
Celery agent that finds related news coverage across outlets for the
same story (Ground News-style panel). Uses Serper.dev news search.
Wraps news_aggregator.py.
"""

from ..celery_app import celery
from ..news_aggregator import find_related_coverage


@celery.task(queue="default", name="agents.coverage_agent")
def run_coverage(article_title: str, original_url: str, top_n: int = 10) -> list:
    """
    Search for related articles covering the same news story.

    Args:
        article_title: Headline used as the Serper search query.
        original_url:  URL of the source article (excluded from results).
        top_n:         Max number of related articles to return.

    Returns:
        List of dicts: title, url, domain, bias, political_leaning_score,
                       factual_reporting, country, logo_url, snippet, date
    """
    return find_related_coverage(article_title, original_url, top_n=top_n)
