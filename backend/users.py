"""
Users Module
Handles user account information, rate limits, and usage tracking
"""

import os
import time
import datetime
from dotenv import load_dotenv

# Import the user database
from models import users_db

load_dotenv()

# Account type configurations
ACCOUNT_TYPES = {
    'free': {
        'daily_limit': 5,
        'monthly_limit': 100,
        'features': ['basic_humanization']
    },
    'basic': {
        'daily_limit': 25,
        'monthly_limit': 500,
        'features': ['basic_humanization', 'custom_style']
    },
    'premium': {
        'daily_limit': 100,
        'monthly_limit': 2000,
        'features': ['basic_humanization', 'custom_style', 'priority_processing']
    },
    'enterprise': {
        'daily_limit': 10000,
        'monthly_limit': 200000,
        'features': ['basic_humanization', 'custom_style', 'priority_processing', 'api_access']
    },
    'admin': {
        'daily_limit': float('inf'),
        'monthly_limit': float('inf'),
        'features': ['basic_humanization', 'custom_style', 'priority_processing', 'api_access', 'admin']
    }
}

def get_user_info(user_id):
    """Get user account information"""
    if user_id not in users_db:
        return None
    
    user_data = users_db[user_id]
    
    # Map between the existing structure and the new API
    account_type = user_data.get('plan', 'Free').lower()
    limits = ACCOUNT_TYPES.get(account_type, ACCOUNT_TYPES['free'])
    
    # Calculate usage data
    words_used = user_data.get('words_used', 0)
    daily_remaining = max(0, limits['daily_limit'] - words_used)
    monthly_remaining = max(0, limits['monthly_limit'] - words_used)
    
    return {
        'user_id': user_id,
        'username': user_id,
        'email': user_data.get('email', f'{user_id}@example.com'),
        'account_type': account_type,
        'joined_date': user_data.get('joined_date', datetime.datetime.now().strftime('%Y-%m-%d')),
        'payment_status': user_data.get('payment_status', 'Pending'),
        'limits': {
            'daily': limits['daily_limit'],
            'monthly': limits['monthly_limit'],
            'remaining': min(daily_remaining, monthly_remaining)
        },
        'usage': {
            'words_used': words_used
        },
        'features': limits['features']
    }

def get_user_rate_limit(user_id, account_type=None):
    """Get user rate limit information"""
    # Map to existing structure if the user exists
    if user_id in users_db:
        user_data = users_db[user_id]
        if not account_type:
            account_type = user_data.get('plan', 'Free').lower()
    else:
        if not account_type:
            account_type = 'free'  # Default to free tier
    
    # Get rate limits from account type
    limits = ACCOUNT_TYPES.get(account_type.lower(), ACCOUNT_TYPES['free'])
    
    # If user exists, check actual usage
    if user_id in users_db:
        words_used = users_db[user_id].get('words_used', 0)
        daily_remaining = max(0, limits['daily_limit'] - words_used)
        monthly_remaining = max(0, limits['monthly_limit'] - words_used)
        remaining = min(daily_remaining, monthly_remaining)
    else:
        remaining = limits['daily_limit']
    
    # Calculate reset times
    now = datetime.datetime.now()
    daily_reset = datetime.datetime(now.year, now.month, now.day) + datetime.timedelta(days=1)
    
    # Calculate month reset (first day of next month)
    if now.month == 12:
        monthly_reset = datetime.datetime(now.year + 1, 1, 1)
    else:
        monthly_reset = datetime.datetime(now.year, now.month + 1, 1)
    
    return {
        'limit': limits['daily_limit'],
        'remaining': remaining,
        'reset_time': daily_reset.strftime('%Y-%m-%d %H:%M:%S'),
        'monthly_limit': limits['monthly_limit'],
        'monthly_remaining': monthly_remaining if 'monthly_remaining' in locals() else limits['monthly_limit'],
        'monthly_reset_time': monthly_reset.strftime('%Y-%m-%d %H:%M:%S')
    }

def increment_user_usage(user_id, count=1):
    """Increment user usage counter"""
    if user_id not in users_db:
        return False
    
    if 'words_used' not in users_db[user_id]:
        users_db[user_id]['words_used'] = 0
        
    users_db[user_id]['words_used'] += count
    return True

def update_user_account_type(user_id, new_account_type):
    """Update user account type"""
    if user_id not in users_db or new_account_type.lower() not in ACCOUNT_TYPES:
        return False
    
    users_db[user_id]['plan'] = new_account_type.capitalize()
    
    # Update payment status
    if new_account_type.lower() != 'free':
        users_db[user_id]['payment_status'] = 'Pending'
    else:
        users_db[user_id]['payment_status'] = 'N/A'
    
    return True

def check_feature_access(user_id, feature):
    """Check if user has access to a specific feature"""
    if user_id not in users_db:
        return False
    
    # Map existing plan to account_type
    account_type = users_db[user_id].get('plan', 'Free').lower()
    features = ACCOUNT_TYPES.get(account_type, ACCOUNT_TYPES['free'])['features']
    
    return feature in features
