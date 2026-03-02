"""
source_analyzer.py
------------------
Analyzes a URL to determine its source domain and retrieves bias,
factuality, and political leaning data from the local source_bias.json.
"""

import json
from pathlib import Path
from urllib.parse import urlparse

# Load the bias data using the file's own directory so it works
# regardless of the current working directory.
_BIAS_FILE = Path(__file__).parent / "source_bias.json"
with open(_BIAS_FILE, "r") as f:
    _source_data = json.load(f)["domains"]

# Build an efficient lookup dictionary keyed by domain
BIAS_LOOKUP: dict = {item["domain"]: item for item in _source_data}


def get_source_analysis(url: str) -> dict:
    """
    Analyzes a URL to find its domain and retrieve bias and reliability data.

    Returns a dict with keys:
      domain, bias, political_leaning_score, factual_reporting,
      country, logo_url, description
    """
    try:
        domain = urlparse(url).netloc
        # Remove 'www.' prefix to match lookup table
        if domain.startswith("www."):
            domain = domain[4:]

        return BIAS_LOOKUP.get(domain, {
            "domain": domain,
            "bias": "Not Rated",
            "political_leaning_score": None,
            "factual_reporting": "Not Rated",
            "country": None,
            "logo_url": f"https://www.google.com/s2/favicons?domain={domain}&sz=64",
            "description": None,
        })
    except Exception:
        return {
            "domain": "Invalid URL",
            "bias": "Not Rated",
            "political_leaning_score": None,
            "factual_reporting": "Not Rated",
            "country": None,
            "logo_url": None,
            "description": None,
        }