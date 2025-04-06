"""
Enhanced fallback for database operations with MongoDB compatibility
"""

import logging
from datetime import datetime
import os
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.warning("Using enhanced in-memory database fallback with MongoDB compatibility")

# Simple in-memory storage
_collections = {
    'users': {
        'demo': {
            '_id': 'demo-id',
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
}

# MongoDB result objects
class InsertOneResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id
        self.acknowledged = True

class UpdateResult:
    def __init__(self, matched_count, modified_count):
        self.matched_count = matched_count
        self.modified_count = modified_count
        self.acknowledged = True

# Collection class to mimic MongoDB collections
class Collection:
    def __init__(self, name):
        self.name = name
        if name not in _collections:
            _collections[name] = {}
        self.data = _collections[name]
    
    def find_one(self, query):
        """Find a single document matching the query"""
        logger.info(f"Find one in {self.name}: {query}")
        
        # Handle simple id query
        if '_id' in query and query['_id'] in self.data:
            return self.data[query['_id']]
            
        # Handle Google ID query (for OAuth)
        if 'google_id' in query:
            for doc_id, doc in self.data.items():
                if doc.get('google_id') == query['google_id']:
                    return doc
        
        # Handle email query (for OAuth)
        if 'email' in query:
            for doc_id, doc in self.data.items():
                if doc.get('email') == query['email']:
                    return doc
                    
        # Handle username query
        if 'username' in query:
            username = query['username']
            if username in self.data:
                return self.data[username]
        
        return None
    
    def insert_one(self, document):
        """Insert a single document"""
        logger.info(f"Insert one in {self.name}: {document}")
        
        # Create ID if not provided
        if '_id' not in document:
            document['_id'] = str(uuid.uuid4())
            
        # For user documents, use username or email as key
        if self.name == 'users':
            doc_id = document.get('username') or document.get('email').split('@')[0]
            document['username'] = doc_id  # Ensure username is set
        else:
            doc_id = document['_id']
            
        self.data[doc_id] = document
        return InsertOneResult(document['_id'])
    
    def update_one(self, filter_query, update_query):
        """Update a single document"""
        logger.info(f"Update one in {self.name}: {filter_query} -> {update_query}")
        
        # Find the document to update
        doc_to_update = self.find_one(filter_query)
        if not doc_to_update:
            return UpdateResult(0, 0)
            
        # Get the document ID
        if self.name == 'users':
            doc_id = doc_to_update.get('username') or doc_to_update.get('email').split('@')[0]
        else:
            doc_id = doc_to_update['_id']
            
        # Handle $set operation
        if '$set' in update_query:
            for key, value in update_query['$set'].items():
                doc_to_update[key] = value
                
        # Handle $inc operation
        if '$inc' in update_query:
            for key, value in update_query['$inc'].items():
                # Handle nested paths like 'usage.requests'
                if '.' in key:
                    parts = key.split('.')
                    target = doc_to_update
                    for part in parts[:-1]:
                        if part not in target:
                            target[part] = {}
                        target = target[part]
                    target[parts[-1]] = target.get(parts[-1], 0) + value
                else:
                    doc_to_update[key] = doc_to_update.get(key, 0) + value
        
        # Replace the document in storage
        self.data[doc_id] = doc_to_update
        return UpdateResult(1, 1)
        
    def find(self, query=None, projection=None):
        """Find all documents matching the query"""
        logger.info(f"Find in {self.name}: {query}")
        results = []
        
        # Return all documents if no query
        if not query:
            return list(self.data.values())
            
        # Filter documents based on query
        for doc in self.data.values():
            match = True
            for key, value in query.items():
                if key not in doc or doc[key] != value:
                    match = False
                    break
            if match:
                results.append(doc)
                
        return results

# Mock client and db for compatibility
class MockClient:
    def __init__(self):
        self.connected = True
    
    def close(self):
        self.connected = False

client = MockClient()

# Mock DB to mimic MongoDB db access
class MockDB:
    def __init__(self):
        self.collections = {}
    
    def __getitem__(self, name):
        """Allow dict-like access to collections"""
        return Collection(name)
        
    def command(self, cmd):
        """Mock MongoDB commands"""
        if cmd == 'ping':
            return {'ok': 1.0}
        return {'ok': 0.0}

db = MockDB()

# Database operation functions
def init_db():
    """Initialize the in-memory database."""
    return True

def add_user(username, email, password_hash):
    """Add a new user."""
    collection = Collection('users')
    
    # Check if user exists
    if collection.find_one({'username': username}):
        return False
    
    # Insert new user
    collection.insert_one({
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
    })
    
    return True

def verify_user(username, password_hash):
    """Verify user credentials."""
    collection = Collection('users')
    user = collection.find_one({'username': username})
    
    if not user:
        return False
    
    return user.get('password_hash') == password_hash

def get_user(username):
    """Get user information."""
    collection = Collection('users')
    return collection.find_one({'username': username})

def update_user_usage(username, word_count):
    """Update user usage statistics."""
    collection = Collection('users')
    result = collection.update_one(
        {'username': username},
        {
            '$inc': {
                'usage.requests': 1,
                'usage.total_words': word_count,
                'usage.monthly_words': word_count
            },
            '$set': {
                'usage.last_request': datetime.now()
            }
        }
    )
    
    return result.modified_count > 0

# For debug purposes, print loaded status
logger.warning("Enhanced db_fallback.py loaded successfully with MongoDB compatibility!")
