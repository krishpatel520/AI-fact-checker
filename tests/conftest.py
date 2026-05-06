"""
conftest.py
-----------
Shared pytest fixtures and configuration for all Veritas tests.
"""

import sys
import os
import pytest

# Ensure project root is always on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_article_text():
    return (
        "The unemployment rate in the United States fell to 3.5 percent in March 2024, "
        "according to the Bureau of Labor Statistics. The Federal Reserve held interest "
        "rates steady at 5.25 percent, citing concerns about persistent inflation. "
        "GDP growth reached 2.8 percent in the first quarter, beating analyst expectations. "
        "President Biden signed a new executive order on border security last Tuesday."
    )


@pytest.fixture
def sample_claims():
    return [
        "The unemployment rate fell to 3.5 percent.",
        "The Federal Reserve held interest rates steady at 5.25 percent.",
        "GDP growth reached 2.8 percent in the first quarter.",
    ]


@pytest.fixture
def sample_source_info():
    return {
        "domain": "apnews.com",
        "bias": "Center",
        "political_leaning_score": 0.0,
        "factual_reporting": "Very High",
        "country": "US",
        "logo_url": "https://www.google.com/s2/favicons?domain=apnews.com&sz=64",
        "description": "Non-profit news agency.",
    }


@pytest.fixture
def sample_verifier_result():
    return {
        "claim": "The unemployment rate fell to 3.5 percent.",
        "verdict": "supported",
        "evidence": [
            {
                "title": "BLS Report",
                "url": "https://bls.gov/news",
                "verdict": "supported",
                "confidence": 0.91,
                "reason": "Bureau confirms 3.5% unemployment.",
                "method": "llm",
            }
        ],
    }
