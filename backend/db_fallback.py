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

# MongoDB Mock Implementation
class InsertOneResult:
    """Simulates MongoDB InsertOneResult"""
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id

class UpdateResult:
    """Simulates MongoDB UpdateResult"""
    def __init__(self, matched_count, modified_count):
        self.matched_count = matched_count
        self.modified_count = modified_count

class Collection:
    """Simulates MongoDB Collection class"""
    def __init__(self, name, storage):
        self.name = name
        self.storage = storage
        if name not in self.storage:
            self.storage[name] = {}
    
    def find_one(self, query):
        """Find a single document matching the query."""
        if not query:
            # Return first document if no query
            docs = self.storage[self.name]
            return docs[list(docs.keys())[0]] if docs else None
            
        # Simple implementation for finding by ID or other unique fields
        if '_id' in query:
            return self.storage[self.name].get(query['_id'])
            
        # For other fields, scan through all items
        for item_id, item in self.storage[self.name].items():
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
        self.storage[self.name][document['_id']] = document
        
        # Return a result object with inserted_id
        return InsertOneResult(document['_id'])
    
    def update_one(self, query, update):
        """Update a single document matching the query."""
        # Find the item to update
        item = self.find_one(query)
        if not item:
            return UpdateResult(0, 0)
        
        # Apply the update
        if '$set' in update:
            for key, value in update['$set'].items():
                item[key] = value
        
        return UpdateResult(1, 1)
    
    def count_documents(self, query):
        """Count documents matching the query."""
        count = 0
        for item in self.storage[self.name].values():
            matches = True
            for key, value in query.items():
                if key not in item or item[key] != value:
                    matches = False
                    break
            
            if matches:
                count += 1
        
        return count
    
    def find(self, query=None, projection=None):
        """Find documents matching the query."""
        results = []
        query = query or {}
        
        for item in self.storage[self.name].values():
            matches = True
            for key, value in query.items():
                if key not in item or item[key] != value:
                    matches = False
                    break
            
            if matches:
                # Handle projection if provided
                if projection:
                    result = {}
                    for field in projection:
                        if field in item and projection[field]:
                            result[field] = item[field]
                    results.append(result)
                else:
                    results.append(item)
        
        return results
    
    def command(self, cmd):
        """Simulate MongoDB commands."""
        if cmd == 'ping':
            return {'ok': 1.0}
        return {'ok': 0.0}

class MockDatabase:
    """Simulates MongoDB Database class"""
    def __init__(self):
        self.storage = {}
        
    def __getitem__(self, name):
        """Access a collection by name."""
        return Collection(name, self.storage)
    
    def command(self, cmd):
        """Simulate MongoDB commands."""
        if cmd == 'ping':
            return {'ok': 1.0}
        return {'ok': 0.0}

class MockClient:
    """Simulates MongoDB Client class"""
    def __init__(self):
        self.connected = True
        self._db = MockDatabase()
    
    def close(self):
        self.connected = False
        
    def __getitem__(self, name):
        """Access a database by name."""
        return self._db

# Initialize client and db
client = MockClient()
db = client['andikar']

logger.warning("Using in-memory database fallback")

# Store user data
_users = {}

def init_db():
    """Initialize the in-memory database."""
    # Add a demo user if it doesn't exist
    if not db['users'].find_one({'username': 'demo'}):
        demo_user = {
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
        db['users'].insert_one(demo_user)
    
    return True

def add_user(username, email, password_hash):
    """Add a new user to the database."""
    if db['users'].find_one({'username': username}):
        return False
    
    user = {
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
    
    db['users'].insert_one(user)
    return True

def verify_user(username, password_hash):
    """Verify user credentials."""
    user = db['users'].find_one({'username': username})
    if not user:
        return False
    
    return user.get('password_hash') == password_hash

def get_user(username):
    """Get user information."""
    return db['users'].find_one({'username': username})

def update_user_usage(username, word_count):
    """Update user usage statistics."""
    user = db['users'].find_one({'username': username})
    if not user:
        return False
    
    # Get current usage stats
    usage = user.get('usage', {})
    requests = usage.get('requests', 0) + 1
    total_words = usage.get('total_words', 0) + word_count
    monthly_words = usage.get('monthly_words', 0) + word_count
    
    # Update usage
    db['users'].update_one(
        {'username': username},
        {'$set': {
            'usage.requests': requests,
            'usage.total_words': total_words,
            'usage.monthly_words': monthly_words,
            'usage.last_request': datetime.now()
        }}
    )
    
    return True

def get_usage_stats():
    """Get global usage statistics."""
    users = db['users'].find()
    total_users = len(users)
    total_requests = sum(user.get('usage', {}).get('requests', 0) for user in users)
    total_words = sum(user.get('usage', {}).get('total_words', 0) for user in users)
    
    return {
        'total_users': total_users,
        'total_requests': total_requests,
        'total_words': total_words,
        'last_updated': datetime.now()
    }

def log_event(event_type, details):
    """Log an event to the database."""
    event = {
        'type': event_type,
        'details': details,
        'timestamp': datetime.now()
    }
    
    db['system_logs'].insert_one(event)
    return True

def get_all_users():
    """Get all users."""
    return db['users'].find()

def clean_old_data():
    """Simulate cleaning old data."""
    # No-op for fallback DB
    return True

# Initialize the database when this module is imported
init_db()
