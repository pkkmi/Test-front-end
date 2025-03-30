"""
API Service module for Andikar AI.
This module handles communication with external APIs.
"""

import os
import time
import json
import logging
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError
from functools import lru_cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API URLs and configuration
HUMANIZER_API_URL = os.environ.get("HUMANIZER_API_URL", "https://web-production-3db6c.up.railway.app")
ADMIN_API_URL = os.environ.get("ADMIN_API_URL", "https://railway-test-api-production.up.railway.app")
AI_DETECTOR_API_URL = os.environ.get("AI_DETECTOR_API_URL", "https://ai-detector-api.example.com")

# API timeouts
DEFAULT_TIMEOUT = 15  # seconds
HUMANIZE_TIMEOUT = 30  # seconds (longer for text processing)
ADMIN_TIMEOUT = 10     # seconds

# API rate limiting
RATE_LIMIT_WINDOW = 60  # seconds
MAX_CALLS_PER_WINDOW = {
    'Free': 5,
    'Basic': 20,
    'Premium': 100
}

# Rate limit tracking
api_call_counters = {}

class ApiRateLimitExceeded(Exception):
    """Exception raised when API rate limit is exceeded"""
    pass

def check_rate_limit(username, plan):
    """
    Check if a user has exceeded their API rate limit
    
    Args:
        username (str): Username
        plan (str): User subscription plan
        
    Returns:
        bool: True if rate limit is not exceeded
        
    Raises:
        ApiRateLimitExceeded: If rate limit is exceeded
    """
    current_time = time.time()
    window_key = int(current_time / RATE_LIMIT_WINDOW)
    user_key = f"{username}_{window_key}"
    
    if user_key not in api_call_counters:
        api_call_counters[user_key] = 1
        # Clean up old entries (from previous windows)
        api_call_counters = {k: v for k, v in api_call_counters.items() if k.split('_')[1] == str(window_key)}
        return True
        
    if api_call_counters[user_key] >= MAX_CALLS_PER_WINDOW.get(plan, 5):
        remaining_time = RATE_LIMIT_WINDOW - (current_time % RATE_LIMIT_WINDOW)
        raise ApiRateLimitExceeded(f"Rate limit exceeded. Try again in {int(remaining_time)} seconds.")
        
    api_call_counters[user_key] += 1
    return True

def humanize_text_api(text, user_plan, retry_count=1):
    """
    Call the external humanizer API to transform text
    
    Args:
        text (str): The text to humanize
        user_plan (str): User subscription plan
        retry_count (int): Number of retries on failure
        
    Returns:
        tuple: (humanized_text, message, status_code)
    """
    if not text:
        return "", "No text provided", 400
    
    # Apply word limit based on plan
    word_limit = 8000 if user_plan == "Premium" else 1500 if user_plan == "Basic" else 500
    words = text.split()
    truncated = False
    
    if len(words) > word_limit:
        words = words[:word_limit]
        text = " ".join(words)
        truncated = True
    
    try:
        payload = {"input_text": text}
        response = requests.post(
            f"{HUMANIZER_API_URL}/humanize_text", 
            json=payload, 
            timeout=HUMANIZE_TIMEOUT,
            headers={"Content-Type": "application/json"}
        )
        
        # Log the response status for debugging
        logger.info(f"Humanizer API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                if "result" in result:
                    message = "Text successfully humanized!"
                    if truncated:
                        message = f"Text was truncated to {word_limit} words due to plan limit. {message}"
                    return result["result"], message, 200
                else:
                    logger.warning(f"Unexpected API response format: {result}")
                    return "", "Unexpected API response format", 500
            except json.JSONDecodeError:
                logger.error(f"Error parsing API response: {response.text[:200]}")
                return "", "Error parsing API response", 500
        elif response.status_code == 429:
            # Rate limited by API
            return "", "External API rate limit reached. Please try again later.", 429
        elif response.status_code >= 500:
            # Server error, retry if possible
            if retry_count > 0:
                time.sleep(1)  # Wait before retry
                return humanize_text_api(text, user_plan, retry_count - 1)
            else:
                return "", f"External API error: {response.status_code}", response.status_code
        else:
            return "", f"External API error: {response.status_code}", response.status_code
            
    except Timeout:
        logger.error("Timeout while calling humanizer API")
        return "", "Humanizer API timeout. The service might be under heavy load.", 504
    except ConnectionError:
        logger.error("Connection error while calling humanizer API")
        return "", "Could not connect to the Humanizer API. The service might be down.", 503
    except RequestException as e:
        logger.error(f"Error calling humanizer API: {e}")
        return "", f"Error calling Humanizer API: {str(e)}", 500
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return "", f"Unexpected error: {str(e)}", 500

def detect_ai_content_api(text, api_keys=None):
    """
    Call external AI detection API to analyze text
    
    Args:
        text (str): Text to analyze
        api_keys (dict): User's API keys
        
    Returns:
        tuple: (result_dict, message, status_code)
    """
    if not text:
        return None, "No text provided", 400
        
    # First try with real API if API keys are provided
    if api_keys and api_keys.get('gpt_zero'):
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_keys.get('gpt_zero')}"
            }
            payload = {"text": text}
            
            response = requests.post(
                f"{AI_DETECTOR_API_URL}/detect", 
                json=payload, 
                headers=headers,
                timeout=DEFAULT_TIMEOUT
            )
            
            if response.status_code == 200:
                return response.json(), "Analysis complete", 200
                
        except Exception as e:
            logger.warning(f"Error using external AI detector API: {e}")
            # Fall back to simulated detection
    
    # Use simulated detection as backup or if no API key
    try:
        # Import here to avoid circular imports
        from utils import detect_ai_content
        result = detect_ai_content(text)
        return result, "Analysis complete (simulated)", 200
    except Exception as e:
        logger.error(f"Error in simulated AI detection: {e}")
        return None, f"Error in AI detection: {str(e)}", 500

@lru_cache(maxsize=100)
def get_api_status():
    """
    Check the status of all external APIs
    
    Returns:
        dict: Status of each API
    """
    result = {
        "humanizer_api": {"status": "unknown", "latency": None},
        "admin_api": {"status": "unknown", "latency": None},
        "ai_detector_api": {"status": "unknown", "latency": None}
    }
    
    # Check humanizer API
    try:
        start_time = time.time()
        response = requests.get(f"{HUMANIZER_API_URL}/", timeout=5)
        latency = time.time() - start_time
        
        result["humanizer_api"] = {
            "status": "online" if response.status_code == 200 else "error",
            "latency": round(latency * 1000, 2),  # in milliseconds
            "status_code": response.status_code
        }
    except Exception as e:
        result["humanizer_api"]["status"] = "offline"
        result["humanizer_api"]["error"] = str(e)
    
    # Check admin API
    try:
        start_time = time.time()
        response = requests.get(f"{ADMIN_API_URL}/", timeout=5)
        latency = time.time() - start_time
        
        result["admin_api"] = {
            "status": "online" if response.status_code == 200 else "error",
            "latency": round(latency * 1000, 2),
            "status_code": response.status_code
        }
    except Exception as e:
        result["admin_api"]["status"] = "offline"
        result["admin_api"]["error"] = str(e)
    
    # Update cache timestamp
    result["timestamp"] = time.time()
    result["cache_expires"] = time.time() + 300  # 5 minutes
    
    return result

def register_user_to_backend_api(username, email, phone=None, plan_type=None):
    """
    Register a user to the backend admin API
    
    Args:
        username (str): Username
        email (str): Email address
        phone (str, optional): Phone number
        plan_type (str, optional): Subscription plan
        
    Returns:
        tuple: (success, message, status_code)
    """
    if not username or not email:
        return False, "Username and email are required", 400
        
    try:
        registration_data = {
            "name": username,
            "email": email,
            "phone": phone if phone else None,
            "details": {
                "plan_type": plan_type if plan_type else "Free",
                "signup_date": time.strftime('%Y-%m-%d'),
                "source": "web"
            }
        }
        
        logger.info(f"Registering user to backend: {username}")
        
        response = requests.post(
            f"{ADMIN_API_URL}/api/register",
            json=registration_data,
            timeout=ADMIN_TIMEOUT,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 201:
            return True, "Registration successful", 201
        elif response.status_code == 400:
            try:
                error_msg = response.json().get('message', 'Invalid data or email already registered')
                return False, error_msg, 400
            except:
                return False, "Registration failed: Invalid data", 400
        else:
            return False, f"Registration failed: Server error ({response.status_code})", response.status_code
            
    except Exception as e:
        logger.error(f"Error registering user to backend: {e}")
        return False, f"Registration error: {str(e)}", 500
