"""
Fallback authentication system for when MongoDB is unavailable.
This provides a simple in-memory user authentication system.
"""

import os
import json
import logging
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

# In-memory user database
users = {
    'demo': {
        'username': 'demo',
        'password': generate_password_hash('demo'),
        'email': 'demo@example.com',
        'account_type': 'basic',
        'created_at': datetime.now().isoformat(),
        'usage': {
            'requests': 0,
            'total_words': 0,
            'last_request': None
        }
    }
}

# Path for persisting users to disk
USERS_FILE = os.path.join(os.path.dirname(__file__), 'users.json')

def _save_users():
    """Save users to disk."""
    try:
        # Convert users to serializable format
        serializable_users = {}
        for username, user in users.items():
            # Copy the user object
            serialized_user = dict(user)
            # Remove non-serializable fields
            serialized_user.pop('password', None)
            serialized_user['password_hash'] = user.get('password', '')
            serializable_users[username] = serialized_user
            
        # Save to file
        with open(USERS_FILE, 'w') as f:
            json.dump(serializable_users, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to save users to disk: {str(e)}")
        return False

def _load_users():
    """Load users from disk."""
    try:
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'r') as f:
                serialized_users = json.load(f)
                
            # Convert back to usable format
            for username, user in serialized_users.items():
                if username not in users:  # Don't overwrite existing users
                    # Copy the serialized user
                    deserialized_user = dict(user)
                    # Fix the password field
                    deserialized_user['password'] = user.get('password_hash', '')
                    deserialized_user.pop('password_hash', None)
                    users[username] = deserialized_user
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to load users from disk: {str(e)}")
        return False

def init_auth():
    """Initialize the authentication system."""
    # Try to load users from disk
    _load_users()
    
    # Ensure demo user exists
    if 'demo' not in users:
        users['demo'] = {
            'username': 'demo',
            'password': generate_password_hash('demo'),
            'email': 'demo@example.com',
            'account_type': 'basic',
            'created_at': datetime.now().isoformat(),
            'usage': {
                'requests': 0,
                'total_words': 0,
                'last_request': None
            }
        }
        _save_users()
    
    logger.info(f"Fallback auth initialized with {len(users)} users")
    return True

def register_user(username, password, email, account_type='basic'):
    """Register a new user."""
    if username in users:
        return False, "Username already exists"
        
    users[username] = {
        'username': username,
        'password': generate_password_hash(password),
        'email': email,
        'account_type': account_type,
        'created_at': datetime.now().isoformat(),
        'usage': {
            'requests': 0,
            'total_words': 0,
            'last_request': None
        }
    }
    
    # Save to disk
    _save_users()
    
    return True, "User registered successfully"

def authenticate_user(username, password):
    """Authenticate a user."""
    if username not in users:
        return False, "User not found"
        
    user = users[username]
    if check_password_hash(user['password'], password):
        return True, user
    
    return False, "Invalid password"

def get_user(username):
    """Get a user by username."""
    return users.get(username)

def update_usage(username, words_processed):
    """Update a user's usage stats."""
    if username not in users:
        return False, "User not found"
        
    user = users[username]
    user['usage']['requests'] += 1
    user['usage']['total_words'] += words_processed
    user['usage']['last_request'] = datetime.now().isoformat()
    
    # Save to disk
    _save_users()
    
    return True, "Usage updated"

def update_tier(username, new_tier):
    """Update a user's tier."""
    if username not in users:
        return False, "User not found"
        
    user = users[username]
    user['account_type'] = new_tier
    
    # Save to disk
    _save_users()
    
    return True, f"Tier updated to {new_tier}"

def get_all_users():
    """Get all users."""
    return users
