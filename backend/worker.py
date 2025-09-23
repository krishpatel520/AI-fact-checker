import json
from .celery_app import celery

# --- IMPORT EVERYTHING needed for the pipeline ---
from .parser import (
    extract_text_from_url,
    extract_text_from_pdf_bytes,
    extract_text_from_docx_bytes
)
from .claims import extract_candidate_claims
from .retriever import retrieve_from_trusted_sources
from .verifier import aggregate_verdict_from_evidence
from .source_analyzer import get_source_analysis


@celery.task
def analyze_url_task(url: str):
    """
    The background task that performs the full analysis pipeline for a URL.
    """
    print(f"🔬 Starting URL analysis for: {url}")
    
    source_info = get_source_analysis(url)
    text = extract_text_from_url(url)
    claims = extract_candidate_claims(text)
    results = []
    
    for claim in claims:
        evidences = retrieve_from_trusted_sources(claim, top_n=3)
        verdict, evidence_results = aggregate_verdict_from_evidence(claim, evidences)
        results.append({'claim': claim, 'verdict': verdict, 'evidence': evidence_results})
    
    doc_status = 'clean_document' if all(r['verdict'] != 'refuted' for r in results) else 'inaccuracies_found'
    
    final_analysis = {
        'status': doc_status, 
        'source_analysis': source_info, 
        'results': results
    }
    
    print(f"✅ URL analysis complete for: {url}")
    return json.dumps(final_analysis)


# --- NEW TASK FOR FILE ANALYSIS ---
@celery.task
def analyze_file_task(content: bytes, filename: str):
    """
    The background task that performs the full analysis pipeline for a file.
    """
    print(f"🔬 Starting File analysis for: {filename}")

    # Step 1: Parse text from file content based on filename extension
    text = ""
    if filename.lower().endswith(".pdf"):
        text = extract_text_from_pdf_bytes(content)
    elif filename.lower().endswith((".docx", ".doc")):
        text = extract_text_from_docx_bytes(content)
    else:
        # Fallback for plain text files (.txt, .md, etc.)
        text = content.decode(errors='ignore')

    # Step 2: Run the rest of the analysis pipeline (same as for URLs)
    claims = extract_candidate_claims(text)
    results = []
    for claim in claims:
        evidences = retrieve_from_trusted_sources(claim, top_n=3)
        verdict, evidence_results = aggregate_verdict_from_evidence(claim, evidences)
        results.append({'claim': claim, 'verdict': verdict, 'evidence': evidence_results})

    doc_status = 'clean_document' if all(r['verdict'] != 'refuted' for r in results) else 'inaccuracies_found'
    
    # We don't have source analysis for a file, so we create a default object
    final_analysis = {
        'status': doc_status,
        'source_analysis': {'domain': f"File: {filename}", 'bias': 'N/A', 'factual_reporting': 'N/A'},
        'results': results
    }

    print(f"✅ File analysis complete for: {filename}")
    return json.dumps(final_analysis)