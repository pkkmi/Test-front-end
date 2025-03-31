import os
from werkzeug.security import generate_password_hash, check_password_hash
import logging
import traceback

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# User tiers and word limits
USER_TIERS = {
    'basic': {'max_words': 500, 'name': 'Basic'},
    'standard': {'max_words': 2500, 'name': 'Standard'},
    'premium': {'max_words': 12500, 'name': 'Premium'}
}

# In-memory fallback storage
memory_users = {
    'demo': {
        "username": "demo",
        "password": generate_password_hash("demo"),
        "email": "demo@example.com",
        "account_type": "basic",
        "usage": {
            "requests": 0,
            "total_words": 0,
            "last_request": None
        }
    }
}
memory_transactions = {}

# Database configuration
DB_URI = os.environ.get('MONGODB_URI', 'mongodb+srv://edgarmaina003:Andikar_25@oldtrafford.id96k.mongodb.net/?retryWrites=true&w=majority&appName=OldTrafford')
DB_NAME = os.environ.get('DB_NAME', 'andikar_ai')

# Try to initialize MongoDB client
try:
    from pymongo import MongoClient
    client = MongoClient(DB_URI, serverSelectionTimeoutMS=5000)  # 5 second timeout
    # Test the connection
    client.server_info()  # Will raise an exception if connection fails
    db = client[DB_NAME]
    users_collection = db['users']
    transactions_collection = db['transactions']
    logger.info(f"Successfully connected to MongoDB: {DB_NAME}")
    using_mongodb = True
except Exception as e:
    logger.error(f"MongoDB connection error: {str(e)}\n{traceback.format_exc()}")
    logger.warning("Falling back to in-memory storage")
    # Using in-memory storage as fallback
    users_collection = memory_users
    transactions_collection = memory_transactions
    using_mongodb = False

def init_db():
    """Initialize the database with collections and demo data."""
    try:
        if not using_mongodb:
            logger.warning("Using in-memory storage instead of MongoDB")
            # Check if demo user exists in memory
            if 'demo' not in memory_users:
                memory_users['demo'] = {
                    "username": "demo",
                    "password": generate_password_hash("demo"),
                    "email": "demo@example.com",
                    "account_type": "basic",
                    "usage": {
                        "requests": 0,
                        "total_words": 0,
                        "last_request": None
                    }
                }
            return
            
        # MongoDB implementation
        # Create unique index on username
        users_collection.create_index("username", unique=True)
        
        # Add demo user if it doesn't exist
        if users_collection.count_documents({"username": "demo"}) == 0:
            users_collection.insert_one({
                "username": "demo",
                "password": generate_password_hash("demo"),
                "email": "demo@example.com",
                "account_type": "basic",
                "usage": {
                    "requests": 0,
                    "total_words": 0,
                    "last_request": None
                }
            })
            logger.info("Added demo user to MongoDB database")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}\n{traceback.format_exc()}")
        logger.warning("Continuing with limited functionality")

def add_user(username, password, email, account_type="basic"):
    """Add a new user to the database."""
    try:
        if not using_mongodb:
            # In-memory implementation
            if username in memory_users:
                return False, "Username already exists"
            
            memory_users[username] = {
                "username": username,
                "password": generate_password_hash(password),
                "email": email,
                "account_type": account_type,
                "usage": {
                    "requests": 0,
                    "total_words": 0,
                    "last_request": None
                }
            }
            return True, "User created successfully"
        
        # MongoDB implementation
        # Check if user already exists
        if users_collection.find_one({"username": username}):
            return False, "Username already exists"
            
        user_data = {
            "username": username,
            "password": generate_password_hash(password),
            "email": email,
            "account_type": account_type,
            "usage": {
                "requests": 0,
                "total_words": 0,
                "last_request": None
            }
        }
        
        result = users_collection.insert_one(user_data)
        if result.inserted_id:
            return True, "User created successfully"
        return False, "Failed to create user"
    except Exception as e:
        logger.error(f"Error adding user: {str(e)}\n{traceback.format_exc()}")
        return False, str(e)

def get_user(username):
    """Get a user by username."""
    try:
        if not using_mongodb:
            # In-memory implementation
            return memory_users.get(username)
        
        # MongoDB implementation
        user = users_collection.find_one({"username": username})
        return user
    except Exception as e:
        logger.error(f"Error getting user: {str(e)}\n{traceback.format_exc()}")
        # Fall back to memory if MongoDB fails
        return memory_users.get(username)

def verify_user(username, password):
    """Verify a user's credentials."""
    try:
        user = get_user(username)
        if not user:
            return False, "User not found"
        
        stored_password = user.get("password")
        if not stored_password:
            return False, "Invalid user data"
            
        if check_password_hash(stored_password, password):
            return True, user
        return False, "Invalid password"
    except Exception as e:
        logger.error(f"Error verifying user: {str(e)}\n{traceback.format_exc()}")
        return False, str(e)

def update_user_usage(username, words_processed):
    """Update a user's usage statistics."""
    try:
        if not using_mongodb:
            # In-memory implementation
            if username not in memory_users:
                return False, "User not found"
            
            user = memory_users[username]
            user["usage"]["requests"] = user["usage"].get("requests", 0) + 1
            user["usage"]["total_words"] = user["usage"].get("total_words", 0) + words_processed
            user["usage"]["last_request"] = "now"  # Simplified for in-memory
            return True, "Usage updated"
        
        # MongoDB implementation
        from datetime import datetime
        result = users_collection.update_one(
            {"username": username},
            {"$inc": {
                "usage.requests": 1,
                "usage.total_words": words_processed
            },
            "$set": {
                "usage.last_request": datetime.now()
            }}
        )
        
        if result.modified_count:
            return True, "Usage updated"
        return False, "Failed to update usage"
    except Exception as e:
        logger.error(f"Error updating user usage: {str(e)}\n{traceback.format_exc()}")
        # Fall back to memory if MongoDB fails
        if username in memory_users:
            memory_users[username]["usage"]["requests"] = memory_users[username]["usage"].get("requests", 0) + 1
            memory_users[username]["usage"]["total_words"] = memory_users[username]["usage"].get("total_words", 0) + words_processed
            memory_users[username]["usage"]["last_request"] = "now"
            return True, "Usage updated (fallback)"
        return False, str(e)

def update_user_tier(username, new_tier):
    """Update a user's account tier."""
    if new_tier not in USER_TIERS:
        return False, f"Invalid tier: {new_tier}"
        
    try:
        if not using_mongodb:
            # In-memory implementation
            if username not in memory_users:
                return False, "User not found"
            
            memory_users[username]["account_type"] = new_tier
            return True, f"User tier updated to {USER_TIERS[new_tier]['name']}"
        
        # MongoDB implementation
        result = users_collection.update_one(
            {"username": username},
            {"$set": {"account_type": new_tier}}
        )
        
        if result.modified_count:
            return True, f"User tier updated to {USER_TIERS[new_tier]['name']}"
        return False, "Failed to update user tier"
    except Exception as e:
        logger.error(f"Error updating user tier: {str(e)}\n{traceback.format_exc()}")
        # Fall back to memory if MongoDB fails
        if username in memory_users:
            memory_users[username]["account_type"] = new_tier
            return True, f"User tier updated to {USER_TIERS[new_tier]['name']} (fallback)"
        return False, str(e)

def get_word_limit(account_type):
    """Get the word limit for a given account type."""
    tier_info = USER_TIERS.get(account_type, USER_TIERS['basic'])
    return tier_info['max_words']
    
def get_tier_info(account_type):
    """Get the full tier information for a given account type."""
    return USER_TIERS.get(account_type, USER_TIERS['basic'])

def get_all_tiers():
    """Get information about all available tiers."""
    return USER_TIERS

def get_db_status():
    """Get the current database connection status."""
    if using_mongodb:
        try:
            # Test the connection
            client.server_info()
            return {
                "status": "connected",
                "type": "MongoDB",
                "database": DB_NAME,
                "collections": ["users", "transactions"]
            }
        except Exception as e:
            return {
                "status": "error",
                "type": "MongoDB",
                "error": str(e),
                "fallback": "in-memory"
            }
    else:
        return {
            "status": "using fallback",
            "type": "in-memory",
            "users": len(memory_users)
        }
