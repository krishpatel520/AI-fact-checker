import os
from dotenv import load_dotenv
import fitz
from docx import Document
from newspaper import Article
import io
import requests
import urllib.parse

# Load variables from the .env file
load_dotenv()

def get_html_from_url(url: str) -> str:
    # --- Securely load the API key from the environment ---
    API_KEY = os.getenv("SCRAPINGBEE_API_KEY")
    if not API_KEY:
        print("❌ CRITICAL: ScrapingBee API key not found in .env file.")
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
        print(f"❌ Failed to get URL through ScrapingBee: {e}")
        return ""

def extract_text_from_pdf_bytes(bytes_data: bytes) -> str:
    text = ""
    with fitz.open(stream=bytes_data, filetype="pdf") as doc:
        for page in doc:
            text += page.get_text()
    return text

def extract_text_from_docx_bytes(bytes_data: bytes) -> str:
    f = io.BytesIO(bytes_data)
    doc = Document(f)
    return "\n".join([p.text for p in doc.paragraphs])

def extract_text_from_url(url: str) -> str:
    html_content = get_html_from_url(url)
    if not html_content:
        return ""

    article = Article(url)
    article.download(input_html=html_content)
    article.parse()

    if len(article.text) < 150:
        print(f"⚠️ Extracted text is too short. Page may have been a login/cookie wall for URL: {url}")
        return ""

    return article.text