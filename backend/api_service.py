"""
API Service Module
Handles communication with the external humanization API
"""

import os
import time
import requests
import logging
from dotenv import load_dotenv
from .users import get_user_rate_limit, increment_user_usage

# Load environment variables
load_dotenv()

# API configuration
API_BASE_URL = os.getenv('HUMANIZER_API_URL', 'https://api.humanizer.example.com')
API_KEY = os.getenv('HUMANIZER_API_KEY', '')

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
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json',
        'User-Agent': 'Andikar-Backend/1.0'
    }
    
    payload = {
        'text': text,
        'options': {
            'style': 'natural',
            'formality': 'neutral',
            'preserve_formatting': True
        }
    }
    
    # Make the request with error handling
    try:
        start_time = time.time()
        response = requests.post(
            f"{API_BASE_URL}/v1/humanize",
            json=payload,
            headers=headers,
            timeout=30  # 30 second timeout
        )
        response_time = time.time() - start_time
        
        # Log API request for monitoring
        logger.info(f"API request completed in {response_time:.2f}s, status: {response.status_code}")
        
        # Handle error response codes
        if response.status_code != 200:
            error_msg = f"API request failed with status {response.status_code}"
            try:
                error_detail = response.json().get('error', {}).get('message', 'Unknown error')
                error_msg = f"{error_msg}: {error_detail}"
            except:
                pass
            
            logger.error(error_msg)
            raise HumanizerAPIError(error_msg)
        
        # Parse response
        result = response.json()
        
        # Track usage
        increment_user_usage(user_id, 1)
        
        return {
            'original_text': text,
            'humanized_text': result.get('humanized_text', ''),
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
        response = requests.get(
            f"{API_BASE_URL}/status",
            headers={'User-Agent': 'Andikar-Backend/1.0'},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            return {
                'status': 'online',
                'latency': response.elapsed.total_seconds(),
                'api_version': data.get('version', 'unknown')
            }
        else:
            return {
                'status': 'degraded',
                'latency': response.elapsed.total_seconds(),
                'message': f"API returned status code {response.status_code}"
            }
            
    except Exception as e:
        return {
            'status': 'offline',
            'message': str(e)
        }
