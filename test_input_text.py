"""
Test script specifically for the input_text field format
Based on the error messages, the API appears to expect a JSON body with an input_text field
"""
import requests
import logging
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# API URL
API_URL = "https://web-production-3db6c.up.railway.app/humanize_text"

def test_input_text_format():
    """Test with the input_text format that appears in the error messages"""
    test_text = "This is a test of the humanizer API. Please convert this AI text to human-like text."
    
    # Try with the specific field name indicated in the error
    payload = {"input_text": test_text}
    headers = {'Content-Type': 'application/json'}
    
    logger.info(f"Sending request to {API_URL}")
    logger.info(f"Payload: {json.dumps(payload)}")
    
    try:
        response = requests.post(API_URL, json=payload, headers=headers)
        
        logger.info(f"Status code: {response.status_code}")
        logger.info(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            logger.info("SUCCESS! Correct format found.")
            try:
                result = response.json()
                logger.info(f"Response JSON: {json.dumps(result, indent=2)}")
            except:
                logger.info(f"Response text: {response.text[:500]}")
            return True
        else:
            logger.error(f"Failed with status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error making request: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Testing with input_text format")
    success = test_input_text_format()
    
    if success:
        logger.info("The input_text format works! Update the API service to use this format.")
    else:
        logger.error("The input_text format failed. The API may require additional configuration.")
