import os
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
import logging
import ssl

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DB_URI = os.environ.get('MONGODB_URI', 'mongodb+srv://edgarmaina003:Andikar_25@oldtrafford.id96k.mongodb.net/?retryWrites=true&w=majority&appName=OldTrafford')
DB_NAME = os.environ.get('DB_NAME', 'andikar_ai')

# Initialize MongoDB client with additional connection parameters for better compatibility
try:
    # Configure with ssl options to handle OpenSSL compatibility issues
    client = MongoClient(
        DB_URI,
        ssl=True,
        ssl_cert_reqs=ssl.CERT_NONE,  # Less strict certificate validation
        connect=False,  # Defer connection until needed
        serverSelectionTimeoutMS=5000,  # Timeout if connection fails
        tlsAllowInvalidCertificates=True  # Allow less secure connections
    )
    db = client[DB_NAME]
    users_collection = db['users']
    transactions_collection = db['transactions']
    logger.info(f"Connected to MongoDB: {DB_NAME}")
except Exception as e:
    logger.error(f"Error connecting to MongoDB: {str(e)}")
    # Fallback to in-memory storage if MongoDB connection fails
    users_collection = {}
    transactions_collection = {}

def init_db():
    """Initialize the database with collections and demo data."""
    try:
        # Create indexes for users collection
        if isinstance(users_collection, dict):
            logger.warning("Using in-memory storage instead of MongoDB")
            return
            
        # Create unique index on username
        users_collection.create_index("username", unique=True)
        
        # Add demo user if it doesn't exist
        if users_collection.count_documents({"username": "demo"}) == 0:
            users_collection.insert_one({
                "username": "demo",
                "password": generate_password_hash("demo"),
                "email": "demo@example.com",
                "usage": {
                    "requests": 0,
                    "total_words": 0,
                    "last_request": None
                }
            })
            logger.info("Added demo user to database")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")

def add_user(username, password, email):
    """Add a new user to the database."""
    try:
        if isinstance(users_collection, dict):
            # In-memory fallback
            if username in users_collection:
                return False, "Username already exists"
            users_collection[username] = {
                "username": username,
                "password": generate_password_hash(password),
                "email": email,
                "usage": {
                    "requests": 0,
                    "total_words": 0,
                    "last_request": None
                }
            }
            return True, "User created successfully"
        
        # MongoDB implementation
        user_data = {
            "username": username,
            "password": generate_password_hash(password),
            "email": email,
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
        logger.error(f"Error adding user: {str(e)}")
        return False, str(e)

def get_user(username):
    """Get a user by username."""
    try:
        if isinstance(users_collection, dict):
            # In-memory fallback
            return users_collection.get(username)
        
        # MongoDB implementation
        user = users_collection.find_one({"username": username})
        return user
    except Exception as e:
        logger.error(f"Error getting user: {str(e)}")
        return None

def verify_user(username, password):
    """Verify a user's credentials."""
    try:
        user = get_user(username)
        if not user:
            return False, "User not found"
        
        if isinstance(users_collection, dict):
            # In-memory fallback
            if check_password_hash(user["password"], password):
                return True, user
            return False, "Invalid password"
        
        # MongoDB implementation
        if check_password_hash(user["password"], password):
            return True, user
        return False, "Invalid password"
    except Exception as e:
        logger.error(f"Error verifying user: {str(e)}")
        return False, str(e)

def update_user_usage(username, words_processed):
    """Update a user's usage statistics."""
    try:
        if isinstance(users_collection, dict):
            # In-memory fallback
            if username not in users_collection:
                return False, "User not found"
            
            user = users_collection[username]
            user["usage"]["requests"] += 1
            user["usage"]["total_words"] += words_processed
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
        logger.error(f"Error updating user usage: {str(e)}")
        return False, str(e)
