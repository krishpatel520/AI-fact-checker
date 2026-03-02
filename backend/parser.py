"""
parser.py
---------
Extracts article text, title, and publish date from URLs and file bytes.
Uses ScrapingBee (if available) for JS-rendered pages, with a fallback
to direct newspaper3k download.
"""

import os
import io
import requests
import urllib.parse
from dotenv import load_dotenv
import fitz                      # PyMuPDF
from docx import Document
from newspaper import Article

load_dotenv()


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
        print("ℹ️  SCRAPINGBEE_API_KEY not set – using direct download.")
        return ""

    encoded_url = urllib.parse.quote(url)
    wait_for_selector = urllib.parse.quote("article")
    api_url = (
        f"https://app.scrapingbee.com/api/v1/?"
        f"api_key={API_KEY}"
        f"&url={encoded_url}"
        f"&render_js=true"
        f"&premium_proxy=true"
        f"&wait_for={wait_for_selector}"
    )

    try:
        response = requests.get(api_url, timeout=120)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"⚠️  ScrapingBee failed for {url}: {e}")
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
        print(f"⚠️  newspaper3k parse error: {e}")
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
        print(f"ℹ️  ScrapingBee → {len(result['text'])} chars for {url}")

    # Attempt 2: Direct download fallback
    if not result["text"] or len(result["text"]) < 80:
        print(f"🔁  Falling back to direct download for {url}")
        result = _parse_article(url, html=None)
        print(f"ℹ️  Direct download → {len(result['text'])} chars for {url}")

    if not result["text"].strip():
        print(f"❌  Could not extract text from {url}")

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
        print(f"⚠️  PDF extraction error: {e}")
    return {"text": text.strip(), "title": "", "publish_date": ""}


def extract_text_from_docx_bytes(bytes_data: bytes) -> dict:
    """Extract text from DOCX file bytes."""
    try:
        f = io.BytesIO(bytes_data)
        doc = Document(f)
        text = "\n".join(p.text for p in doc.paragraphs)
    except Exception as e:
        print(f"⚠️  DOCX extraction error: {e}")
        text = ""
    return {"text": text.strip(), "title": "", "publish_date": ""}
