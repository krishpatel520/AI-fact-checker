import requests
import time
import pytest

# The base URL for your locally running API
BASE_URL = "http://127.0.0.1:8000"

def test_url_verification_workflow():
    """
    Tests the full end-to-end process for verifying a URL.
    1. Submits a URL and gets a task ID.
    2. Polls the result endpoint until the task is complete.
    3. Validates the structure of the final successful result.
    """
    # A reliable, simple news article for testing
    test_url = "https://apnews.com/article/fact-check-biden-border-executive-order-258014202102"

    # --- Step 1: Start the analysis task ---
    print(f"\nSubmitting URL for analysis: {test_url}")
    start_response = requests.post(
        f"{BASE_URL}/api/verify/url",
        data={"url": test_url}
    )
    
    # Check that the initial request was accepted
    assert start_response.status_code == 200
    start_data = start_response.json()
    assert start_data["status"] == "PENDING"
    assert "task_id" in start_data
    task_id = start_data["task_id"]
    print(f"Received task ID: {task_id}")

    # --- Step 2: Poll for the result ---
    result_data = None
    # --- CHANGE THIS LINE ---
    # Increase the polling range from 20 to 50 to allow a longer timeout
    for i in range(50): # Poll up to 50 times (e.g., 2.5 minutes)
        print(f"Polling attempt {i+1}...")
        result_response = requests.get(f"{BASE_URL}/api/result/{task_id}")
        assert result_response.status_code == 200
        result_data = result_response.json()
        
        if result_data["status"] == "SUCCESS" or result_data["status"] == "FAILURE":
            print("Task finished!")
            break
        
        time.sleep(3) # Wait 3 seconds between polls
    
    # --- Step 3: Validate the final result ---
    assert result_data is not None, "Polling timed out without a final result."
    assert result_data["status"] == "SUCCESS", f"Task failed with error: {result_data.get('error')}"
    
    # Check the structure of the successful result
    final_result = result_data["result"]
    assert "status" in final_result
    assert "source_analysis" in final_result
    assert "results" in final_result
    assert isinstance(final_result["results"], list)
    
    print("Test successful! The API returned a valid result structure.")