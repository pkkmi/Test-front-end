"""
Users Module
Handles user account information, rate limits, and usage tracking
"""

import os
import time
import datetime
from dotenv import load_dotenv

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

# Mock user database (replace with actual database in production)
# In a real application, this would be stored in a database
user_db = {
    # Example user entry
    'admin_user': {
        'username': 'admin',
        'email': 'admin@example.com',
        'account_type': 'admin',
        'usage': {
            'daily': 0,
            'monthly': 0,
            'last_reset_day': datetime.datetime.now().day,
            'last_reset_month': datetime.datetime.now().month
        }
    }
}

def get_user_info(user_id):
    """Get user account information"""
    if user_id not in user_db:
        return None
    
    user = user_db[user_id]
    check_usage_reset(user_id)  # Check if usage counters need to be reset
    
    account_type = user['account_type']
    limits = ACCOUNT_TYPES.get(account_type, ACCOUNT_TYPES['free'])
    
    return {
        'user_id': user_id,
        'username': user['username'],
        'email': user['email'],
        'account_type': account_type,
        'limits': {
            'daily': limits['daily_limit'],
            'monthly': limits['monthly_limit']
        },
        'usage': {
            'daily': user['usage']['daily'],
            'monthly': user['usage']['monthly']
        },
        'features': limits['features']
    }

def get_user_rate_limit(user_id, account_type=None):
    """Get user rate limit information"""
    # If user doesn't exist, create a temporary entry
    if user_id not in user_db:
        if not account_type:
            account_type = 'free'  # Default to free tier
        
        user_db[user_id] = {
            'username': user_id,
            'email': f'{user_id}@example.com',
            'account_type': account_type,
            'usage': {
                'daily': 0,
                'monthly': 0,
                'last_reset_day': datetime.datetime.now().day,
                'last_reset_month': datetime.datetime.now().month
            }
        }
    
    user = user_db[user_id]
    check_usage_reset(user_id)  # Reset counters if needed
    
    # Get rate limits from account type
    limits = ACCOUNT_TYPES.get(user['account_type'], ACCOUNT_TYPES['free'])
    
    # Calculate remaining limits
    daily_remaining = max(0, limits['daily_limit'] - user['usage']['daily'])
    monthly_remaining = max(0, limits['monthly_limit'] - user['usage']['monthly'])
    remaining = min(daily_remaining, monthly_remaining)
    
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
        'monthly_remaining': monthly_remaining,
        'monthly_reset_time': monthly_reset.strftime('%Y-%m-%d %H:%M:%S')
    }

def increment_user_usage(user_id, count=1):
    """Increment user usage counter"""
    if user_id not in user_db:
        return False
    
    check_usage_reset(user_id)  # Reset counters if needed
    
    user_db[user_id]['usage']['daily'] += count
    user_db[user_id]['usage']['monthly'] += count
    
    return True

def check_usage_reset(user_id):
    """Check if usage counters need to be reset"""
    if user_id not in user_db:
        return
    
    user = user_db[user_id]
    now = datetime.datetime.now()
    
    # Reset daily counter if day changed
    if user['usage']['last_reset_day'] != now.day:
        user['usage']['daily'] = 0
        user['usage']['last_reset_day'] = now.day
    
    # Reset monthly counter if month changed
    if user['usage']['last_reset_month'] != now.month:
        user['usage']['monthly'] = 0
        user['usage']['last_reset_month'] = now.month

def update_user_account_type(user_id, new_account_type):
    """Update user account type"""
    if user_id not in user_db or new_account_type not in ACCOUNT_TYPES:
        return False
    
    user_db[user_id]['account_type'] = new_account_type
    return True

def check_feature_access(user_id, feature):
    """Check if user has access to a specific feature"""
    if user_id not in user_db:
        return False
    
    user = user_db[user_id]
    account_type = user['account_type']
    features = ACCOUNT_TYPES.get(account_type, ACCOUNT_TYPES['free'])['features']
    
    return feature in features
