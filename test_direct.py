"""
Direct API Test
Skip all the app logic and directly hit the API to test what format works.
"""
import requests
import logging
import json
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# The API URL 
API_URL = "https://web-production-3db6c.up.railway.app/humanize_text"

def test_direct_connection():
    """Test a direct connection to the API with various formats"""
    # Use a simple test sentence
    test_text = "AI-generated text often sounds robotic and formulaic. Please make it more human-like."
    
    # Try form data (x-www-form-urlencoded) - this is most common for web forms
    try:
        logger.info("\n--- Testing form data ---")
        payload = {'text': test_text}
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        
        response = requests.post(API_URL, data=payload, headers=headers)
        
        logger.info(f"Status code: {response.status_code}")
        logger.info(f"Response headers: {dict(response.headers)}")
        logger.info(f"Response: {response.text[:500]}")
        
        if response.status_code == 200:
            logger.info("SUCCESS! Form data format works.")
            return True
    except Exception as e:
        logger.error(f"Error testing form data: {str(e)}")
    
    # Try JSON format with different keys
    keys_to_try = ['text', 'content', 'input', 'message', 'query']
    
    for key in keys_to_try:
        try:
            logger.info(f"\n--- Testing JSON with '{key}' key ---")
            payload = {key: test_text}
            headers = {'Content-Type': 'application/json'}
            
            response = requests.post(API_URL, json=payload, headers=headers)
            
            logger.info(f"Status code: {response.status_code}")
            logger.info(f"Response headers: {dict(response.headers)}")
            logger.info(f"Response: {response.text[:500]}")
            
            if response.status_code == 200:
                logger.info(f"SUCCESS! JSON with '{key}' key works.")
                return True
        except Exception as e:
            logger.error(f"Error testing JSON with '{key}' key: {str(e)}")
    
    # Try plain text (raw body)
    try:
        logger.info("\n--- Testing plain text body ---")
        headers = {'Content-Type': 'text/plain'}
        
        response = requests.post(API_URL, data=test_text, headers=headers)
        
        logger.info(f"Status code: {response.status_code}")
        logger.info(f"Response headers: {dict(response.headers)}")
        logger.info(f"Response: {response.text[:500]}")
        
        if response.status_code == 200:
            logger.info("SUCCESS! Plain text format works.")
            return True
    except Exception as e:
        logger.error(f"Error testing plain text: {str(e)}")
    
    # Try URL parameters with GET request
    try:
        logger.info("\n--- Testing URL parameters (GET) ---")
        params = {'text': test_text}
        
        response = requests.get(API_URL, params=params)
        
        logger.info(f"Status code: {response.status_code}")
        logger.info(f"Response headers: {dict(response.headers)}")
        logger.info(f"Response: {response.text[:500]}")
        
        if response.status_code == 200:
            logger.info("SUCCESS! URL parameters (GET) works.")
            return True
    except Exception as e:
        logger.error(f"Error testing URL parameters (GET): {str(e)}")
    
    # Try URL parameters with POST request
    try:
        logger.info("\n--- Testing URL parameters (POST) ---")
        params = {'text': test_text}
        
        response = requests.post(API_URL, params=params)
        
        logger.info(f"Status code: {response.status_code}")
        logger.info(f"Response headers: {dict(response.headers)}")
        logger.info(f"Response: {response.text[:500]}")
        
        if response.status_code == 200:
            logger.info("SUCCESS! URL parameters (POST) works.")
            return True
    except Exception as e:
        logger.error(f"Error testing URL parameters (POST): {str(e)}")
    
    logger.error("All format tests failed. The API may be offline or using a different format.")
    return False

if __name__ == "__main__":
    logger.info(f"Testing direct connection to API: {API_URL}")
    
    # Get test text from command line if provided
    if len(sys.argv) > 1:
        test_text = sys.argv[1]
    else:
        test_text = "This is a test of the humanization API. The text should be transformed to appear more human-like."
    
    success = test_direct_connection()
    
    if success:
        logger.info("At least one format was successful.")
    else:
        logger.error("All formats failed. Check if the API is working or if it needs a different format.")
