"""
parser.py
---------
Extracts article text, title, and publish date from URLs and file bytes.
Uses ScrapingBee (if available) for JS-rendered pages, with a fallback
to direct newspaper3k download.
"""

import io
import logging
import os
import urllib.parse

import fitz                      # PyMuPDF
import requests
from docx import Document
from dotenv import load_dotenv
from newspaper import Article

load_dotenv()

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_html_from_url(url: str) -> str:
    """
    Attempt to fetch rendered HTML via ScrapingBee.
    Returns empty string if the API key is missing or the request fails.
    """
    API_KEY = os.getenv("SCRAPINGBEE_API_KEY")
    if not API_KEY:
        logger.info("SCRAPINGBEE_API_KEY not set – using direct download.")
        return ""

    params = {
        "api_key": API_KEY,
        "url": url,
        "render_js": "true",
        "premium_proxy": "true",
        "wait_for": urllib.parse.quote("article"),
    }
    api_url = "https://app.scrapingbee.com/api/v1/?" + urllib.parse.urlencode(params)

    try:
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        logger.warning("ScrapingBee failed for %s: %s", url, e)
        return ""


def _parse_article(url: str, html: str | None = None) -> dict:
    """
    Run newspaper3k on a URL, optionally seeding with pre-fetched HTML.
    Returns {text, title, publish_date}.
    """
    try:
        article = Article(url)
        if html:
            article.download(input_html=html)
        else:
            article.download()
        article.parse()
        return {
            "text": article.text or "",
            "title": article.title or "",
            "publish_date": str(article.publish_date) if article.publish_date else "",
        }
    except Exception as e:
        logger.warning("newspaper3k parse error: %s", e)
        return {"text": "", "title": "", "publish_date": ""}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_text_from_url(url: str) -> dict:
    """
    Robust article extractor. Returns a dict:
      {text: str, title: str, publish_date: str}

    Strategy:
      1. Try ScrapingBee-rendered HTML + newspaper3k
      2. Fall back to direct newspaper3k download if (1) yields < 80 chars
    """
    result = {"text": "", "title": "", "publish_date": ""}

    # Attempt 1: ScrapingBee
    html = _get_html_from_url(url)
    if html:
        result = _parse_article(url, html=html)
        logger.info("ScrapingBee → %d chars for %s", len(result["text"]), url)

    # Attempt 2: Direct download fallback
    if not result["text"] or len(result["text"]) < 80:
        logger.info("Falling back to direct download for %s", url)
        result = _parse_article(url, html=None)
        logger.info("Direct download → %d chars for %s", len(result["text"]), url)

    if not result["text"].strip():
        logger.error("Could not extract text from %s", url)

    result["text"] = result["text"].strip()
    return result


def extract_text_from_pdf_bytes(bytes_data: bytes) -> dict:
    """Extract text from PDF file bytes."""
    text = ""
    try:
        with fitz.open(stream=bytes_data, filetype="pdf") as doc:
            for page in doc:
                text += page.get_text()
    except Exception as e:
        logger.warning("PDF extraction error: %s", e)
    return {"text": text.strip(), "title": "", "publish_date": ""}


def extract_text_from_docx_bytes(bytes_data: bytes) -> dict:
    """Extract text from DOCX file bytes."""
    try:
        f = io.BytesIO(bytes_data)
        doc = Document(f)
        text = "\n".join(p.text for p in doc.paragraphs)
    except Exception as e:
        logger.warning("DOCX extraction error: %s", e)
        text = ""
    return {"text": text.strip(), "title": "", "publish_date": ""}
