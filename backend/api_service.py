"""
API Service Module
Handles communication with the external humanization API
"""

import os
import time
import requests
import logging
import random  # For demo purposes only
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
        
        # Try to use the real API if configured
        if API_KEY:
            response = requests.post(
                f"{API_BASE_URL}/api/humanize",  # Adjust endpoint as needed
                json=payload,
                headers=headers,
                timeout=30  # 30 second timeout
            )
            
            # Handle error response codes
            if response.status_code != 200:
                logger.warning(f"API request failed with status {response.status_code}, using fallback")
                # Use fallback method below
                raise Exception("API request failed")
                
            result = response.json()
            humanized_text = result.get('humanized_text', '')
        else:
            # Fallback/demo method if API key not available
            # This simulates an API response for testing
            time.sleep(0.5)  # Simulate API latency
            
            # Simple text humanization simulation
            lines = text.split('\n')
            humanized_lines = []
            
            for line in lines:
                if not line.strip():
                    humanized_lines.append(line)
                    continue
                    
                words = line.split()
                # Mix in some sentence variations
                if len(words) > 3 and random.random() > 0.7:
                    # Add transition words
                    transitions = ["moreover", "however", "indeed", "specifically", "naturally"]
                    idx = random.randint(1, min(3, len(words)-1))
                    words.insert(idx, random.choice(transitions) + ",")
                
                # Occasionally combine sentences
                if '.' in line and random.random() > 0.8:
                    parts = line.split('.')
                    if len(parts) >= 2:
                        connectors = [" moreover, ", " additionally, ", " furthermore, ", " in addition, "]
                        for i in range(len(parts)-1):
                            if parts[i].strip() and parts[i+1].strip():
                                parts[i] = parts[i] + random.choice(connectors) + parts[i+1].lstrip()
                                parts[i+1] = ""
                    humanized_lines.append('.'.join([p for p in parts if p]))
                else:
                    humanized_lines.append(' '.join(words))
            
            humanized_text = '\n'.join(humanized_lines)
        
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
        # If API is not reachable, use fallback mode
        return {
            'status': 'fallback',
            'message': "Using local text processing (API not available)",
            'error': str(e)
        }
