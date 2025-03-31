import os
import requests
import time
import logging
import re
from .db import update_user_usage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API configuration
API_URL = os.environ.get('API_URL', 'https://web-production-3db6c.up.railway.app/humanize_text')
API_KEY = os.environ.get('API_KEY', '')

# Configuration parameters
DEFAULT_TIMEOUT = int(os.environ.get('API_TIMEOUT', '60'))  # Increased timeout (default: 60 seconds)
RETRY_COUNT = int(os.environ.get('API_RETRY_COUNT', '2'))   # Number of retries

class HumanizerAPIError(Exception):
    """Custom exception for API errors."""
    pass

def count_words(text):
    """Count the number of words in the given text."""
    # Split text by whitespace and count non-empty strings
    words = re.findall(r'\b\w+\b', text)
    return len(words)

def humanize_text(text, username):
    """
    Humanize the given text using the external API.
    
    Args:
        text (str): The text to humanize
        username (str): The username of the user making the request
        
    Returns:
        dict: A dictionary containing the humanized text and metrics
        
    Raises:
        HumanizerAPIError: If there's an issue with the API request
    """
    # Count words in the input text
    word_count = count_words(text)
    
    # Log the request
    logger.info(f"Humanizing text for user {username} - {word_count} words")
    
    # Record metrics
    start_time = time.time()
    
    # Initialize retry counter
    retry_count = 0
    
    # If text is very long (more than 1000 words), use longer timeout
    timeout = DEFAULT_TIMEOUT
    if word_count > 1000:
        timeout = DEFAULT_TIMEOUT * 2
    
    while retry_count <= RETRY_COUNT:
        try:
            # Make the API request
            payload = {"input_text": text}
            headers = {}
            
            # Add API key if available
            if API_KEY:
                headers['Authorization'] = f'Bearer {API_KEY}'
            
            if retry_count > 0:
                logger.info(f"Retry attempt {retry_count} for user {username}")
            
            # Send the request
            response = requests.post(API_URL, json=payload, headers=headers, timeout=timeout)
            
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
                
                # If it's a server error (5xx), retry
                if response.status_code >= 500 and retry_count < RETRY_COUNT:
                    retry_count += 1
                    time.sleep(1)  # Wait before retry
                    continue
                
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
                        'response_time': response_time,
                        'retries': retry_count
                    }
                }
                
            except Exception as e:
                logger.error(f"Error parsing API response: {str(e)}")
                raise HumanizerAPIError(f"Error parsing API response: {str(e)}")
                
        except requests.RequestException as e:
            logger.error(f"Error making API request: {str(e)}")
            
            # Retry for network-related errors, but not if we've hit the limit
            if retry_count < RETRY_COUNT:
                retry_count += 1
                time.sleep(1)  # Wait before retry
                continue
            else:
                # If we've exhausted retries, try a local fallback
                if 'timeout' in str(e).lower():
                    # Create a simple fallback response for timeout errors
                    logger.info(f"Using fallback response for {username} after timeout")
                    response_time = time.time() - start_time
                    
                    # Simple fallback humanization (very basic)
                    fallback_text = text
                    # Add a note about using fallback
                    fallback_notice = "\n\n[Note: This text was processed using a fallback method due to API timeout. For better results, try again with shorter text or during non-peak hours.]"
                    
                    return {
                        'humanized_text': fallback_text + fallback_notice,
                        'metrics': {
                            'input_words': word_count,
                            'output_words': count_words(fallback_text),
                            'response_time': response_time,
                            'retries': retry_count,
                            'fallback': True
                        }
                    }
                
                raise HumanizerAPIError(f"Error making API request after {retry_count} retries: {str(e)}")

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
                'has_key': bool(API_KEY),
                'timeout': DEFAULT_TIMEOUT
            }
        else:
            return {
                'status': 'error',
                'message': f'API returned status code {response.status_code}',
                'url': API_URL,
                'has_key': bool(API_KEY),
                'timeout': DEFAULT_TIMEOUT
            }
            
    except requests.RequestException as e:
        return {
            'status': 'offline',
            'message': f'API connection error: {str(e)}',
            'url': API_URL,
            'has_key': bool(API_KEY),
            'timeout': DEFAULT_TIMEOUT
        }
