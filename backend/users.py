"""
User management module for Andikar AI.
This module handles user account operations and data.
"""

import time
import datetime
import logging
from models import users_db, transactions_db
from config import pricing_plans
from backend.api_service import register_user_to_backend_api

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_user_by_username(username):
    """
    Get user data by username
    
    Args:
        username (str): Username
        
    Returns:
        dict: User data or None if not found
    """
    if username in users_db:
        # Create a copy of user data for safety
        user_data = dict(users_db[username])
        # Don't return password in responses
        if 'password' in user_data:
            user_data.pop('password')
        return user_data
    return None

def get_user_account_info(username):
    """
    Get comprehensive user account information
    
    Args:
        username (str): Username
        
    Returns:
        dict: User account information
    """
    if username not in users_db:
        return None
        
    user_data = get_user_by_username(username)
    if not user_data:
        return None
    
    # Get user's transactions
    user_transactions = [t for t in transactions_db if t.get('user_id') == username]
    
    # Get plan details
    plan_info = pricing_plans.get(user_data['plan'], {})
    
    # Calculate usage percentage
    word_limit = plan_info.get('word_limit', 0)
    words_used = user_data.get('words_used', 0)
    usage_percentage = (words_used / word_limit * 100) if word_limit > 0 else 0
    
    # Calculate days remaining in subscription (placeholder for real implementation)
    days_remaining = 30  # Assuming monthly subscriptions
    
    account_info = {
        'username': username,
        'plan': user_data['plan'],
        'plan_details': plan_info,
        'joined_date': user_data.get('joined_date', ''),
        'payment_status': user_data.get('payment_status', 'Unknown'),
        'usage_stats': {
            'words_used': words_used,
            'word_limit': word_limit,
            'usage_percentage': round(usage_percentage, 1),
            'days_remaining': days_remaining
        },
        'last_transactions': user_transactions[:5],  # Last 5 transactions
        'api_keys_configured': bool(user_data.get('api_keys', {}).get('gpt_zero')) or bool(user_data.get('api_keys', {}).get('originality'))
    }
    
    return account_info

def update_user_plan(username, new_plan):
    """
    Update a user's subscription plan
    
    Args:
        username (str): Username
        new_plan (str): New subscription plan
        
    Returns:
        tuple: (success, message)
    """
    if username not in users_db:
        return False, "User not found"
        
    if new_plan not in pricing_plans:
        return False, "Invalid plan type"
        
    current_plan = users_db[username]['plan']
    
    if current_plan == new_plan:
        return False, "User is already on this plan"
    
    # Update plan and set payment status based on plan type
    users_db[username]['plan'] = new_plan
    
    # Free plan is automatically paid, others require payment
    if new_plan == 'Free':
        users_db[username]['payment_status'] = 'Paid'
        message = "Plan updated to Free tier."
    else:
        users_db[username]['payment_status'] = 'Pending'
        message = f"Plan updated to {new_plan}. Payment required to activate."
    
    # Sync with backend
    try:
        # Use generic email format if we don't have it stored
        email = f"{username}@example.com"  # Just a placeholder
        register_user_to_backend_api(
            username=username,
            email=email,
            plan_type=new_plan
        )
    except Exception as e:
        logger.error(f"Error syncing plan update with backend: {e}")
        # Continue anyway since we've updated locally
    
    return True, message

def update_user_usage(username, word_count):
    """
    Update a user's word usage counter
    
    Args:
        username (str): Username
        word_count (int): Number of words used
        
    Returns:
        bool: Success status
    """
    if username not in users_db:
        return False
    
    # Update word count
    current_usage = users_db[username].get('words_used', 0)
    users_db[username]['words_used'] = current_usage + word_count
    
    # Log for tracking
    logger.info(f"Updated usage for {username}: +{word_count} words, total: {users_db[username]['words_used']}")
    
    return True

def check_user_limit(username):
    """
    Check if a user has reached their word limit
    
    Args:
        username (str): Username
        
    Returns:
        tuple: (has_exceeded, remaining_words)
    """
    if username not in users_db:
        return True, 0
    
    user_data = users_db[username]
    plan = user_data.get('plan', 'Free')
    words_used = user_data.get('words_used', 0)
    word_limit = pricing_plans.get(plan, {}).get('word_limit', 0)
    
    if word_limit <= 0:  # No limit or invalid plan
        return False, 0
    
    remaining = max(0, word_limit - words_used)
    has_exceeded = words_used >= word_limit
    
    return has_exceeded, remaining

def register_new_user(username, password, email, plan_type=None, phone=None):
    """
    Register a new user
    
    Args:
        username (str): Username
        password (str): Password
        email (str): Email address
        plan_type (str, optional): Subscription plan
        phone (str, optional): Phone number
        
    Returns:
        tuple: (success, message)
    """
    if username in users_db:
        return False, "Username already exists"
    
    # Validate plan type
    plan_type = plan_type if plan_type in pricing_plans else 'Free'
    
    # Set payment status (Free tier is automatically Paid)
    payment_status = 'Paid' if plan_type == 'Free' else 'Pending'
    
    # Save user to in-memory database
    users_db[username] = {
        'password': password,
        'plan': plan_type,
        'joined_date': datetime.datetime.now().strftime('%Y-%m-%d'),
        'words_used': 0,
        'payment_status': payment_status,
        'api_keys': {
            'gpt_zero': '',
            'originality': ''
        }
    }
    
    # Register user to backend
    success, message, _ = register_user_to_backend_api(
        username=username,
        email=email,
        phone=phone,
        plan_type=plan_type
    )
    
    if not success:
        # If backend registration fails, we still keep the local registration
        # but return a warning message
        return True, f"Registration successful, but backend sync encountered an issue: {message}"
    
    return True, "Registration successful"

def process_payment(username, phone_number, amount=None):
    """
    Process a payment for a user
    
    Args:
        username (str): Username
        phone_number (str): Phone number for payment
        amount (float, optional): Payment amount (uses plan price if None)
        
    Returns:
        tuple: (success, message, transaction_id)
    """
    if username not in users_db:
        return False, "User not found", None
    
    # If amount not specified, use plan price
    if amount is None:
        plan = users_db[username]['plan']
        amount = pricing_plans.get(plan, {}).get('price', 0)
    
    # Generate transaction ID
    import random
    import string
    transaction_id = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))
    
    # Record the transaction
    transaction = {
        'transaction_id': transaction_id,
        'user_id': username,
        'phone_number': phone_number,
        'amount': amount,
        'date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'status': 'Completed'
    }
    
    transactions_db.append(transaction)
    
    # Update payment status
    users_db[username]['payment_status'] = 'Paid'
    
    # Sync with backend
    try:
        # Use generic email format if we don't have it stored
        email = f"{username}@example.com"  # Just a placeholder
        register_user_to_backend_api(
            username=username,
            email=email,
            phone=phone_number,
            plan_type=users_db[username]['plan']
        )
    except Exception as e:
        logger.error(f"Error syncing payment with backend: {e}")
        # Continue anyway since we've updated locally
    
    return True, f"Payment of KES {amount} successful", transaction_id

def update_api_keys(username, gpt_zero_key=None, originality_key=None):
    """
    Update API keys for a user
    
    Args:
        username (str): Username
        gpt_zero_key (str, optional): GPT Zero API key
        originality_key (str, optional): Originality.ai API key
        
    Returns:
        bool: Success status
    """
    if username not in users_db:
        return False
    
    # Only update keys that are provided
    if gpt_zero_key is not None:
        users_db[username]['api_keys']['gpt_zero'] = gpt_zero_key
    
    if originality_key is not None:
        users_db[username]['api_keys']['originality'] = originality_key
    
    return True
