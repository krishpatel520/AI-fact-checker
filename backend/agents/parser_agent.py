"""
parser_agent.py
---------------
Celery agent that wraps the parser module.
Handles URL extraction, PDF, DOCX, and plain text inputs.
Returns a normalised dict: {text, title, publish_date, input_type}.
"""

from ..celery_app import celery
from ..parser import (
    extract_text_from_url,
    extract_text_from_pdf_bytes,
    extract_text_from_docx_bytes,
)


@celery.task(bind=True, queue="high", max_retries=2, default_retry_delay=10,
             name="agents.parser_agent")
def run_parser(self, input_ref: str, input_type: str, file_content: bytes = None,
               filename: str = "") -> dict:
    """
    Parse article content from a URL, uploaded file bytes, or raw text.

    Args:
        input_ref:    URL string, filename, or first 200 chars of pasted text.
        input_type:   "url" | "file" | "text"
        file_content: Raw bytes for file uploads (serialised as list[int] by Celery).
        filename:     Original filename for file uploads.

    Returns:
        dict with keys: text, title, publish_date, input_type
    """
    try:
        if input_type == "url":
            result = extract_text_from_url(input_ref)

        elif input_type == "file":
            # Celery serialises bytes as a list of ints — convert back
            raw: bytes = bytes(file_content) if isinstance(file_content, list) else file_content
            lower = filename.lower()
            if lower.endswith(".pdf"):
                result = extract_text_from_pdf_bytes(raw)
            elif lower.endswith((".docx", ".doc")):
                result = extract_text_from_docx_bytes(raw)
            else:
                result = {"text": raw.decode(errors="ignore"), "title": filename, "publish_date": ""}

        elif input_type == "text":
            # input_ref contains the raw pasted text
            first_sentence = input_ref.strip().split(".")[0][:120]
            result = {
                "text": input_ref,
                "title": first_sentence or "Pasted Text",
                "publish_date": "",
            }

        else:
            result = {"text": "", "title": "", "publish_date": ""}

        result["input_type"] = input_type
        return result

    except Exception as exc:
        raise self.retry(exc=exc)
