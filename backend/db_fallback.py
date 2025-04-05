"""
Fallback implementation for database operations using in-memory storage.
This module is used when MongoDB connection fails.
"""

import logging
import time
from datetime import datetime
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory database (dict-based)
db = {
    'users': {},
    'usage_stats': {},
    'system_logs': []
}

# Mock client for compatibility
class MockClient:
    def __init__(self):
        self.connected = True
    
    def close(self):
        self.connected = False

client = MockClient()

logger.warning("Using in-memory database fallback")

def init_db():
    """Initialize the in-memory database."""
    # Add a demo user if it doesn't exist
    if 'demo' not in db['users']:
        db['users']['demo'] = {
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
    
    return True

def add_user(username, email, password_hash):
    """Add a new user to the in-memory database."""
    if username in db['users']:
        return False
    
    db['users'][username] = {
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
    """Verify user credentials against the in-memory database."""
    if username not in db['users']:
        return False
    
    user = db['users'][username]
    return user.get('password_hash') == password_hash

def get_user(username):
    """Get user information from the in-memory database."""
    return db['users'].get(username)

def update_user_usage(username, word_count):
    """Update user usage statistics in the in-memory database."""
    if username not in db['users']:
        return False
    
    user = db['users'][username]
    
    # Update usage statistics
    user['usage']['requests'] += 1
    user['usage']['total_words'] += word_count
    user['usage']['monthly_words'] += word_count
    user['usage']['last_request'] = datetime.now()
    
    return True

def get_usage_stats():
    """Get global usage statistics from the in-memory database."""
    total_users = len(db['users'])
    total_requests = sum(user['usage'].get('requests', 0) for user in db['users'].values())
    total_words = sum(user['usage'].get('total_words', 0) for user in db['users'].values())
    
    return {
        'total_users': total_users,
        'total_requests': total_requests,
        'total_words': total_words,
        'last_updated': datetime.now()
    }

def log_event(event_type, details):
    """Log an event to the in-memory database."""
    event = {
        'type': event_type,
        'details': details,
        'timestamp': datetime.now()
    }
    
    db['system_logs'].append(event)
    return True

def get_all_users():
    """Get all users from the in-memory database."""
    return list(db['users'].values())

def clean_old_data():
    """Simulate cleaning old data (no-op for in-memory database)."""
    # This is a no-op for the in-memory database
    return True

# Dictionary accessor class to mimic MongoDB collections
class Collection:
    def __init__(self, name):
        if name not in db:
            db[name] = {}
        self.name = name
    
    def find_one(self, query):
        """Find a single document matching the query."""
        # Simple implementation for finding by ID or other unique fields
        if '_id' in query:
            return db[self.name].get(query['_id'])
        
        # For other fields, scan through all items
        for item_id, item in db[self.name].items():
            matches = True
            for key, value in query.items():
                if key not in item or item[key] != value:
                    matches = False
                    break
            
            if matches:
                return item
        
        return None
    
    def insert_one(self, document):
        """Insert a document into the collection."""
        # Generate a simple ID if not provided
        if '_id' not in document:
            document['_id'] = str(time.time())
        
        # Store in the database
        db[self.name][document['_id']] = document
        
        # Return a result object with inserted_id
        class InsertResult:
            def __init__(self, inserted_id):
                self.inserted_id = inserted_id
        
        return InsertResult(document['_id'])
    
    def update_one(self, query, update):
        """Update a single document matching the query."""
        # Find the item to update
        item = self.find_one(query)
        if not item:
            return None
        
        # Apply the update
        if '$set' in update:
            for key, value in update['$set'].items():
                item[key] = value
        
        # Return a result object
        class UpdateResult:
            def __init__(self, matched_count, modified_count):
                self.matched_count = matched_count
                self.modified_count = modified_count
        
        return UpdateResult(1, 1)
    
    def count_documents(self, query):
        """Count documents matching the query."""
        count = 0
        for item in db[self.name].values():
            matches = True
            for key, value in query.items():
                if key not in item or item[key] != value:
                    matches = False
                    break
            
            if matches:
                count += 1
        
        return count

# MongoDB-like indexing (no-op for in-memory database)
def create_index(collection_name, keys, **kwargs):
    """Create an index (no-op for in-memory database)."""
    return True

# Dictionary accessor to mimic MongoDB db object
def __getitem__(name):
    return Collection(name)

# Add the __getitem__ method to the db object
db.__getitem__ = lambda name: Collection(name)

# Initialize the database when this module is imported
init_db()
