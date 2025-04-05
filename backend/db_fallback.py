"""
Minimal emergency fallback for database operations - simplified version.
"""

import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.warning("Using EMERGENCY minimal in-memory database fallback")

# Simple in-memory storage with no MongoDB compatibility
_users = {
    'demo': {
        'username': 'demo',
        'email': 'demo@example.com',
        'created_at': datetime.now(),
        'usage': {
            'requests': 0,
            'total_words': 0,
            'monthly_words': 0,
            'last_request': None
        }
    }
}

# Mock client and db for compatibility
class MockClient:
    def __init__(self):
        self.connected = True
    
    def close(self):
        self.connected = False

client = MockClient()

# Simple class to mimic MongoDB db access
class MockDB:
    def command(self, cmd):
        return {'ok': 1.0}

db = MockDB()

def init_db():
    """Initialize the in-memory database."""
    # Already initialized
    return True

def add_user(username, email, password_hash):
    """Add a new user."""
    if username in _users:
        return False
    
    _users[username] = {
        'username': username,
        'email': email,
        'password_hash': password_hash,
        'created_at': datetime.now(),
        'usage': {
            'requests': 0,
            'total_words': 0,
            'monthly_words': 0,
            'last_request': None
        }
    }
    
    return True

def verify_user(username, password_hash):
    """Verify user credentials."""
    if username not in _users:
        return False
    
    return _users[username].get('password_hash') == password_hash

def get_user(username):
    """Get user information."""
    return _users.get(username)

def update_user_usage(username, word_count):
    """Update user usage statistics."""
    if username not in _users:
        return False
    
    user = _users[username]
    
    # Update usage statistics
    user['usage']['requests'] += 1
    user['usage']['total_words'] += word_count
    user['usage']['monthly_words'] += word_count
    user['usage']['last_request'] = datetime.now()
    
    return True

# For debug purposes, print loaded status
logger.warning("EMERGENCY db_fallback.py loaded successfully!")
