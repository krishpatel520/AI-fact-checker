import os
from pathlib import Path
from dotenv import load_dotenv
import requests
import json

# Load variables from the .env file
load_dotenv()

_TRUSTED_SOURCES_FILE = Path(__file__).parent / "trusted_sources.json"

def retrieve_from_trusted_sources(query: str, top_n: int = 3):
    """
    Search for the query across trusted sources using the Serper.dev Google Search API.
    """
    # --- Securely load the API key from the environment ---
    SERPER_API_KEY = os.getenv("SERPER_API_KEY")
    if not SERPER_API_KEY:
        print("❌ CRITICAL: Serper API key not found in .env file.")
        return []

    try:
        with open(_TRUSTED_SOURCES_FILE) as f:
            trusted_domains = json.load(f)['domains']
    except FileNotFoundError:
        print("❌ trusted_sources.json not found. Returning no evidence.")
        return []

    site_query = " OR ".join([f"site:{domain}" for domain in trusted_domains])
    full_query = f"{query} ({site_query})"

    url = "https://google.serper.dev/search"
    payload = json.dumps({"q": full_query, "num": top_n})
    headers = {
        'X-API-KEY': SERPER_API_KEY,
        'Content-Type': 'application/json'
    }

    results = []
    try:
        response = requests.post(url, headers=headers, data=payload, timeout=10)
        response.raise_for_status()
        search_results = response.json().get("organic", [])

        for item in search_results:
            results.append({
                "title": item.get("title", "No Title"),
                "content": item.get("snippet", ""),
                "url": item.get("link", "")
            })
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching evidence from Serper: {e}")

    return results[:top_n]