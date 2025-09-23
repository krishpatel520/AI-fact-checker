import json
from urllib.parse import urlparse

# Load the bias data once when the module is imported
with open('backend/source_bias.json', 'r') as f:
    source_data = json.load(f)['domains']

# Create a more efficient lookup dictionary
BIAS_LOOKUP = {item['domain']: item for item in source_data}

def get_source_analysis(url: str):
    """
    Analyzes a URL to find its domain and retrieve bias and reliability data.
    """
    try:
        domain = urlparse(url).netloc
        # Remove 'www.' if it exists to match the lookup table
        if domain.startswith('www.'):
            domain = domain[4:]
        
        # Return the data from our lookup or a default value
        return BIAS_LOOKUP.get(domain, {
            "domain": domain,
            "bias": "Not Rated",
            "factual_reporting": "Not Rated"
        })
    except Exception:
        return {
            "domain": "Invalid URL",
            "bias": "Not Rated",
            "factual_reporting": "Not Rated"
        }