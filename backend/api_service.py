import os
import requests
import time
import logging
import re
from .db import get_tier_info, update_user_usage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API configuration
API_URL = os.environ.get('API_URL', 'https://web-production-3db6c.up.railway.app/humanize_text')
API_KEY = os.environ.get('API_KEY', '')

class HumanizerAPIError(Exception):
    """Custom exception for API errors."""
    pass

def count_words(text):
    """Count the number of words in the given text."""
    # Split text by whitespace and count non-empty strings
    words = re.findall(r'\b\w+\b', text)
    return len(words)

def humanize_text(text, username, account_type):
    """
    Humanize the given text using the external API.
    
    Args:
        text (str): The text to humanize
        username (str): The username of the user making the request
        account_type (str): The account type/tier of the user
        
    Returns:
        dict: A dictionary containing the humanized text and metrics
        
    Raises:
        HumanizerAPIError: If there's an issue with the API request
        ValueError: If the text exceeds the user's word limit
    """
    # Count words in the input text
    word_count = count_words(text)
    
    # Get the word limit for the user's tier
    tier_info = get_tier_info(account_type)
    max_words = tier_info['max_words']
    
    # Check if the text exceeds the word limit
    if word_count > max_words:
        raise ValueError(f"Text exceeds your {tier_info['name']} plan word limit of {max_words} words. Your text has {word_count} words.")
    
    # Log the request
    logger.info(f"Humanizing text for user {username} ({account_type} tier) - {word_count} words")
    
    # Record metrics
    start_time = time.time()
    
    try:
        # Make the API request
        payload = {"input_text": text}
        headers = {}
        
        # Add API key if available
        if API_KEY:
            headers['Authorization'] = f'Bearer {API_KEY}'
        
        # Send the request
        response = requests.post(API_URL, json=payload, headers=headers, timeout=30)
        
        # Calculate response time
        response_time = time.time() - start_time
        
        # Check for API errors
        if response.status_code != 200:
            error_msg = f"API request failed with status code {response.status_code}"
            try:
                error_detail = response.json()
                error_msg += f" - {error_detail}"
            except:
                pass
            logger.error(error_msg)
            raise HumanizerAPIError(error_msg)
        
        # Parse the response
        try:
            response_data = response.json()
            
            # Extract the humanized text from the response based on different possible formats
            humanized_text = None
            
            # Try different possible response formats
            if 'humanized_text' in response_data:
                humanized_text = response_data['humanized_text']
            elif 'output_text' in response_data:
                humanized_text = response_data['output_text']
            elif 'result' in response_data:
                humanized_text = response_data['result']
            elif 'text' in response_data:
                humanized_text = response_data['text']
            else:
                # If no recognized format, use the first string value found
                for key, value in response_data.items():
                    if isinstance(value, str) and len(value) > 10:  # Reasonable text size
                        humanized_text = value
                        break
            
            # If we still don't have humanized text, use the whole response as a fallback
            if not humanized_text:
                humanized_text = str(response_data)
            
            # Update user usage statistics
            update_user_usage(username, word_count)
            
            # Return the humanized text and metrics
            return {
                'humanized_text': humanized_text,
                'metrics': {
                    'input_words': word_count,
                    'output_words': count_words(humanized_text),
                    'response_time': response_time
                },
                'tier_info': {
                    'name': tier_info['name'],
                    'word_limit': max_words,
                    'remaining': max_words - word_count
                }
            }
            
        except Exception as e:
            logger.error(f"Error parsing API response: {str(e)}")
            raise HumanizerAPIError(f"Error parsing API response: {str(e)}")
            
    except requests.RequestException as e:
        logger.error(f"Error making API request: {str(e)}")
        raise HumanizerAPIError(f"Error making API request: {str(e)}")

def get_api_status():
    """Check if the API is online and responding."""
    try:
        # Use a small sample text to avoid unnecessary processing
        payload = {"input_text": "Hello world."}
        headers = {}
        
        # Add API key if available
        if API_KEY:
            headers['Authorization'] = f'Bearer {API_KEY}'
            
        # Send a test request
        response = requests.post(API_URL, json=payload, headers=headers, timeout=5)
        
        # Check if the API is responding properly
        if response.status_code == 200:
            return {
                'status': 'online',
                'message': 'API is operational',
                'url': API_URL,
                'has_key': bool(API_KEY)
            }
        else:
            return {
                'status': 'error',
                'message': f'API returned status code {response.status_code}',
                'url': API_URL,
                'has_key': bool(API_KEY)
            }
            
    except requests.RequestException as e:
        return {
            'status': 'offline',
            'message': f'API connection error: {str(e)}',
            'url': API_URL,
            'has_key': bool(API_KEY)
        }
