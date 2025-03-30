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
    
    # Prepare request
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Andikar-Backend/1.0'
    }
    
    # Construct the full API URL
    api_url = f"{API_BASE_URL}{HUMANIZE_ENDPOINT}"
    
    # Prepare the payload based on our API testing
    payload = {
        "text": text
    }
    
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
        logger.info(f"Response headers: {response.headers}")
        logger.info(f"Response content: {response.text[:500]}")  # Log first 500 chars
        
        # Check if the request was successful
        if response.status_code != 200:
            error_message = f"API request failed with status code {response.status_code}"
            try:
                error_data = response.json()
                if 'error' in error_data:
                    error_message += f": {error_data['error']}"
            except:
                if response.text:
                    error_message += f": {response.text[:200]}"
            
            logger.error(error_message)
            raise HumanizerAPIError(error_message)
        
        # Try to parse the response as JSON
        try:
            result = response.json()
        except json.JSONDecodeError:
            # If not JSON, treat the response as plain text
            result = {
                "humanized_text": response.text
            }
        
        # Get the humanized text from the response
        if 'humanized_text' in result:
            humanized_text = result['humanized_text']
        elif 'result' in result:
            humanized_text = result['result']
        elif 'text' in result:
            humanized_text = result['text']
        elif isinstance(result, str):
            humanized_text = result
        else:
            humanized_text = response.text
        
        response_time = time.time() - start_time
        
        # Log API request for monitoring
        logger.info(f"API request completed in {response_time:.2f}s")
        
        # Track usage
        increment_user_usage(user_id, len(text.split()))
        
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
        
        # Make a minimal request
        payload = {
            "text": "Test connection."
        }
        
        response = requests.post(
            api_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
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
                'full_url': api_url
            }
            
    except Exception as e:
        return {
            'status': 'offline',
            'message': f"Error checking API status: {str(e)}",
            'endpoint': HUMANIZE_ENDPOINT,
            'full_url': f"{API_BASE_URL}{HUMANIZE_ENDPOINT}"
        }
