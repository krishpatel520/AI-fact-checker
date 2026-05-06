"""
news_aggregator.py
------------------
Finds related news coverage for the same story across different outlets,
enabling the Ground News-style "N outlets covered this" panel.
Uses Serper.dev API (already in .env) to search for related articles,
then maps each result to its source bias data.
"""

import os
import json
import requests
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

# Load source bias data for enrichment
_BIAS_FILE = Path(__file__).parent / "source_bias.json"
with open(_BIAS_FILE, "r") as f:
    _BIAS_LOOKUP = {item["domain"]: item for item in json.load(f)["domains"]}


def _get_domain(url: str) -> str:
    """Extract clean domain from a URL."""
    try:
        domain = urlparse(url).netloc
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return ""


def _enrich_with_bias(domain: str) -> dict:
    """Look up bias/factuality data for a domain, with sensible defaults."""
    return _BIAS_LOOKUP.get(domain, {
        "domain": domain,
        "bias": "Not Rated",
        "political_leaning_score": None,
        "factual_reporting": "Not Rated",
        "country": None,
        "logo_url": f"https://www.google.com/s2/favicons?domain={domain}&sz=64",
        "description": None,
    })


def find_related_coverage(article_title: str, original_url: str, top_n: int = 10) -> list:
    """
    Search for related articles on the same story from different outlets.

    Args:
        article_title: The headline/title of the original article
        original_url:  The URL of the original article (to exclude from results)
        top_n:         Maximum number of related articles to return

    Returns:
        A list of dicts, each with:
          title, url, domain, bias, political_leaning_score,
          factual_reporting, country, logo_url, description
    """
    SERPER_API_KEY = os.getenv("SERPER_API_KEY")
    if not SERPER_API_KEY or not article_title:
        return []

    original_domain = _get_domain(original_url)

    # Use the article title as the query – Serper finds news about the same event
    payload = json.dumps({
        "q": article_title,
        "num": top_n * 2,   # over-fetch to compensate for filtering
        "type": "news",     # news search mode
    })
    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            "https://google.serper.dev/news",
            headers=headers,
            data=payload,
            timeout=12,
        )
        response.raise_for_status()
        raw_results = response.json().get("news", [])
    except requests.exceptions.RequestException as e:
        print(f"❌ Serper news search failed: {e}")
        return []

    seen_domains = {original_domain}
    coverage = []

    for item in raw_results:
        url = item.get("link", "")
        title = item.get("title", "")
        if not url or not title:
            continue

        domain = _get_domain(url)
        if not domain or domain in seen_domains:
            continue  # skip duplicates and the original source

        seen_domains.add(domain)
        bias_data = _enrich_with_bias(domain)

        coverage.append({
            "title": title,
            "url": url,
            "domain": domain,
            "snippet": item.get("snippet", ""),
            "date": item.get("date", ""),
            "bias": bias_data.get("bias", "Not Rated"),
            "political_leaning_score": bias_data.get("political_leaning_score"),
            "factual_reporting": bias_data.get("factual_reporting", "Not Rated"),
            "country": bias_data.get("country"),
            "logo_url": bias_data.get("logo_url", f"https://www.google.com/s2/favicons?domain={domain}&sz=64"),
            "description": bias_data.get("description"),
        })

        if len(coverage) >= top_n:
            break

    # Sort by political_leaning_score (left → right), None values last
    coverage.sort(
        key=lambda x: (x["political_leaning_score"] is None, x["political_leaning_score"] or 0)
    )

    print(f"📰 Found {len(coverage)} related coverage items for: {article_title[:60]}")
    return coverage
