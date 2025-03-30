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
API_BASE_URL = os.getenv('HUMANIZER_API_URL', 'https://web-production-3db6c.up.railway.app')
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
        'Content-Type': 'application/json',
        'User-Agent': 'Andikar-Backend/1.0'
    }
    
    # Add Authorization header if API key is available
    if API_KEY:
        headers['Authorization'] = f'Bearer {API_KEY}'
    
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
        
        # Try multiple endpoints in case the first one doesn't work
        endpoints = [
            '/api/humanize',
            '/humanize',
            '/v1/humanize'
        ]
        
        response = None
        error_messages = []
        
        for endpoint in endpoints:
            try:
                logger.info(f"Trying API endpoint: {endpoint}")
                response = requests.post(
                    f"{API_BASE_URL}{endpoint}",
                    json=payload,
                    headers=headers,
                    timeout=30  # 30 second timeout
                )
                
                if response.status_code == 200:
                    logger.info(f"Successful API response from endpoint: {endpoint}")
                    break
                else:
                    error_messages.append(f"Endpoint {endpoint} returned status {response.status_code}")
                    response = None
            except Exception as e:
                error_messages.append(f"Error with endpoint {endpoint}: {str(e)}")
                continue
        
        # If none of the endpoints worked
        if not response or response.status_code != 200:
            error_detail = " | ".join(error_messages)
            logger.error(f"All API endpoints failed: {error_detail}")
            raise HumanizerAPIError(f"API request failed: {error_detail}")
        
        # Parse response
        result = response.json()
        humanized_text = result.get('humanized_text', '')
        
        # If we don't receive humanized text, check for alternate response formats
        if not humanized_text and 'result' in result:
            humanized_text = result.get('result', '')
        
        if not humanized_text and 'data' in result:
            humanized_text = result.get('data', {}).get('text', '')
        
        if not humanized_text:
            logger.error(f"API response missing humanized text: {result}")
            raise HumanizerAPIError("API response did not contain humanized text")
        
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
        # Try multiple endpoints for status
        status_endpoints = [
            '/status',
            '/api/status',
            '/health'
        ]
        
        for endpoint in status_endpoints:
            try:
                response = requests.get(
                    f"{API_BASE_URL}{endpoint}",
                    headers={'User-Agent': 'Andikar-Backend/1.0'},
                    timeout=5
                )
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                    except:
                        data = {'status': 'healthy'}
                        
                    return {
                        'status': 'online',
                        'latency': response.elapsed.total_seconds(),
                        'api_version': data.get('version', 'unknown'),
                        'endpoint': endpoint
                    }
            except:
                continue
        
        # If we get here, all endpoints failed
        return {
            'status': 'offline',
            'message': "API is unreachable. Please check configuration.",
            'base_url': API_BASE_URL
        }
            
    except Exception as e:
        return {
            'status': 'error',
            'message': "Error checking API status",
            'error': str(e)
        }
