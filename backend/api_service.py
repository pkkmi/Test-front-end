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
    
    # Track successful format
    success_format = None
    
    # Try different request formats
    formats_to_try = [
        # Format 1: application/x-www-form-urlencoded (form data)
        {
            'method': 'post',
            'headers': {'Content-Type': 'application/x-www-form-urlencoded'},
            'data': {'text': text},
            'description': 'Form data'
        },
        # Format 2: JSON with 'text' key
        {
            'method': 'post',
            'headers': {'Content-Type': 'application/json'},
            'json': {'text': text},
            'description': 'JSON with text key'
        },
        # Format 3: JSON with 'input' key
        {
            'method': 'post',
            'headers': {'Content-Type': 'application/json'},
            'json': {'input': text},
            'description': 'JSON with input key'
        },
        # Format 4: JSON with 'content' key
        {
            'method': 'post',
            'headers': {'Content-Type': 'application/json'},
            'json': {'content': text},
            'description': 'JSON with content key'
        },
        # Format 5: JSON with 'message' key
        {
            'method': 'post',
            'headers': {'Content-Type': 'application/json'},
            'json': {'message': text},
            'description': 'JSON with message key'
        },
        # Format 6: Plain text
        {
            'method': 'post',
            'headers': {'Content-Type': 'text/plain'},
            'data': text,
            'description': 'Plain text'
        },
        # Format 7: Query parameters
        {
            'method': 'post',
            'params': {'text': text},
            'description': 'Query parameters'
        }
    ]
    
    # Log request information
    logger.info(f"Sending request to API: {api_url}")
    logger.info(f"Text length: {len(text)} characters")
    
    # Track errors for all formats
    errors = []
    
    # Make the request with error handling
    try:
        start_time = time.time()
        
        # Try each format until one works
        response = None
        
        for fmt in formats_to_try:
            try:
                logger.info(f"Trying format: {fmt['description']}")
                
                # Setup request arguments
                request_args = {k: v for k, v in fmt.items() if k not in ['method', 'description']}
                request_args['timeout'] = 30  # 30 second timeout
                
                # Make the request
                if fmt['method'] == 'post':
                    response = requests.post(api_url, **request_args)
                else:
                    response = requests.get(api_url, **request_args)
                
                # Log response details for debugging
                logger.info(f"Response status code: {response.status_code}")
                logger.info(f"Response headers: {dict(response.headers)}")
                logger.info(f"Response content (sample): {response.text[:200] if response.text else 'Empty'}")
                
                # If successful, stop trying
                if response.status_code == 200:
                    success_format = fmt['description']
                    logger.info(f"Successful format: {success_format}")
                    break
                else:
                    errors.append(f"{fmt['description']}: {response.status_code} - {response.text[:100]}")
                    
            except Exception as e:
                errors.append(f"{fmt['description']}: {str(e)}")
                continue
        
        # If all formats failed
        if not response or response.status_code != 200:
            error_message = f"All API request formats failed. Errors: {'; '.join(errors)}"
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
        # Check all possible keys where the result might be
        possible_keys = ['humanized_text', 'result', 'text', 'output', 'response', 'content']
        
        humanized_text = None
        for key in possible_keys:
            if key in result:
                humanized_text = result[key]
                logger.info(f"Found result in key: {key}")
                break
        
        if not humanized_text and isinstance(result, str):
            humanized_text = result
        
        if not humanized_text:
            # Just use the full response text if we couldn't parse it
            humanized_text = response.text
            logger.info("Using full response text as result")
        
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
                'characters_processed': len(text),
                'success_format': success_format
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
        
        # Try different formats
        formats_to_try = [
            # Form data
            {'data': {'text': 'Test'}, 'headers': {'Content-Type': 'application/x-www-form-urlencoded'}},
            # JSON
            {'json': {'text': 'Test'}, 'headers': {'Content-Type': 'application/json'}},
            # Plain text
            {'data': 'Test', 'headers': {'Content-Type': 'text/plain'}},
            # Query parameters
            {'params': {'text': 'Test'}}
        ]
        
        for fmt in formats_to_try:
            try:
                response = requests.post(
                    api_url,
                    timeout=5,
                    **fmt
                )
                
                if response.status_code == 200:
                    return {
                        'status': 'online',
                        'latency': response.elapsed.total_seconds(),
                        'endpoint': HUMANIZE_ENDPOINT,
                        'format': str(fmt),
                        'full_url': api_url
                    }
                elif response.status_code != 422:  # Ignore 422 (invalid format)
                    return {
                        'status': 'degraded',
                        'latency': response.elapsed.total_seconds(),
                        'message': f"API returned status code {response.status_code}",
                        'endpoint': HUMANIZE_ENDPOINT,
                        'format': str(fmt),
                        'full_url': api_url
                    }
            except:
                continue
        
        # If we get here, all formats failed
        return {
            'status': 'offline',
            'message': "Unable to connect with any request format",
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
