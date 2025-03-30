"""
API Service Module
Handles communication with the external humanization API
"""

import os
import time
import requests
import logging
import json
from dotenv import load_dotenv
from .users import get_user_rate_limit, increment_user_usage

# Load environment variables
load_dotenv()

# API configuration
API_BASE_URL = os.getenv('HUMANIZER_API_URL', 'https://web-production-3db6c.up.railway.app')
HUMANIZE_ENDPOINT = '/humanize_text'  # The specific endpoint for humanization

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HumanizerAPIError(Exception):
    """Custom exception for API errors"""
    pass

def humanize_text(text, user_id, account_type):
    """
    Send text to the humanizer API and return the response
    
    Args:
        text (str): Text to be humanized
        user_id (str): User ID for rate limiting and tracking
        account_type (str): Account type for rate limits
        
    Returns:
        dict: Humanized text response with metadata
        
    Raises:
        HumanizerAPIError: If the API request fails
    """
    # Check rate limits
    rate_limit = get_user_rate_limit(user_id, account_type)
    if rate_limit['remaining'] <= 0:
        raise HumanizerAPIError(f"Rate limit exceeded. Resets at {rate_limit['reset_time']}")
    
    # Construct the full API URL
    api_url = f"{API_BASE_URL}{HUMANIZE_ENDPOINT}"
    
    # Based on the error messages, the API expects a JSON with input_text field
    headers = {
        'Content-Type': 'application/json'
    }
    
    # Create the payload using the input_text field
    payload = {
        "input_text": text
    }
    
    # Log request information
    logger.info(f"Sending request to API: {api_url}")
    logger.info(f"Request payload: {json.dumps(payload)}")
    
    # Make the request with error handling
    try:
        start_time = time.time()
        
        # Make the POST request
        response = requests.post(
            api_url,
            json=payload,
            headers=headers,
            timeout=30  # 30 second timeout
        )
        
        # Log response details for debugging
        logger.info(f"Response status code: {response.status_code}")
        logger.info(f"Response headers: {dict(response.headers)}")
        logger.info(f"Response content (sample): {response.text[:200] if response.text else 'Empty'}")
        
        # Check if the request was successful
        if response.status_code != 200:
            error_message = f"API request failed with status code {response.status_code}"
            try:
                error_data = response.json()
                if 'detail' in error_data:
                    error_message += f": {json.dumps(error_data['detail'])}"
                elif 'error' in error_data:
                    error_message += f": {error_data['error']}"
            except:
                if response.text:
                    error_message += f": {response.text[:200]}"
            
            logger.error(error_message)
            raise HumanizerAPIError(error_message)
        
        # Try to parse the response as JSON
        try:
            result = response.json()
            logger.info(f"Parsed JSON response: {json.dumps(result)[:200]}")
        except json.JSONDecodeError:
            # If not JSON, treat the response as plain text
            result = {
                "humanized_text": response.text
            }
            logger.info("Response was not JSON, using plain text")
        
        # Get the humanized text from the response
        # Based on testing, find the appropriate key for the result
        if 'humanized_text' in result:
            humanized_text = result['humanized_text']
        elif 'output_text' in result:
            humanized_text = result['output_text']
        elif 'result' in result:
            humanized_text = result['result']
        elif 'output' in result:
            humanized_text = result['output']
        else:
            # Default to the full response text if no recognized key
            humanized_text = response.text
        
        response_time = time.time() - start_time
        
        # Log API request for monitoring
        logger.info(f"API request completed in {response_time:.2f}s")
        
        # Track usage
        increment_user_usage(user_id, len(text.split()))
        
        # Construct and return the result
        return {
            'original_text': text,
            'humanized_text': humanized_text,
            'metrics': {
                'response_time': response_time,
                'characters_processed': len(text)
            },
            'usage': {
                'remaining': rate_limit['remaining'] - 1
            }
        }
        
    except requests.exceptions.RequestException as e:
        logger.error(f"API connection error: {str(e)}")
        raise HumanizerAPIError(f"Failed to connect to humanizer API: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in API request: {str(e)}")
        raise HumanizerAPIError(f"Unexpected error: {str(e)}")

def get_api_status():
    """Check the status of the humanizer API"""
    try:
        # Try to access the humanize endpoint with a minimal request
        api_url = f"{API_BASE_URL}{HUMANIZE_ENDPOINT}"
        
        # Use the correct format with input_text field
        headers = {'Content-Type': 'application/json'}
        payload = {"input_text": "Test connection"}
        
        response = requests.post(
            api_url,
            json=payload,
            headers=headers,
            timeout=5
        )
        
        if response.status_code == 200:
            return {
                'status': 'online',
                'latency': response.elapsed.total_seconds(),
                'endpoint': HUMANIZE_ENDPOINT,
                'full_url': api_url
            }
        else:
            return {
                'status': 'degraded',
                'latency': response.elapsed.total_seconds(),
                'message': f"API returned status code {response.status_code}",
                'endpoint': HUMANIZE_ENDPOINT,
                'full_url': api_url,
                'response': response.text[:200]
            }
            
    except Exception as e:
        return {
            'status': 'offline',
            'message': f"Error checking API status: {str(e)}",
            'endpoint': HUMANIZE_ENDPOINT,
            'full_url': f"{API_BASE_URL}{HUMANIZE_ENDPOINT}"
        }
