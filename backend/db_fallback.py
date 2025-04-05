"""
Fallback database implementation using a simple dictionary-based storage
Used when MongoDB connection fails due to compatibility issues
"""

import os
import logging
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory storage
users = {
    "demo": {
        "username": "demo",
        "password": generate_password_hash("demo"),
        "email": "demo@example.com",
        "usage": {
            "requests": 0,
            "total_words": 0,
            "last_request": None
        }
    }
}

transactions = {}

# Simulate collections
users_collection = users
transactions_collection = transactions

# Initialize mock database connection
db = {"users": users, "transactions": transactions}
client = {"andikar_ai": db}

def init_db():
    """Initialize the in-memory database."""
    logger.warning("Using in-memory database fallback")
    # Demo user is already defined in the users dictionary
    return True

def add_user(username, password, email):
    """Add a new user to the in-memory database."""
    try:
        if username in users:
            return False, "Username already exists"
        
        users[username] = {
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
    except Exception as e:
        logger.error(f"Error adding user: {str(e)}")
        return False, str(e)

def get_user(username):
    """Get a user by username from the in-memory database."""
    return users.get(username)

def verify_user(username, password):
    """Verify a user's credentials against the in-memory database."""
    try:
        user = get_user(username)
        if not user:
            return False, "User not found"
        
        if check_password_hash(user["password"], password):
            return True, user
        return False, "Invalid password"
    except Exception as e:
        logger.error(f"Error verifying user: {str(e)}")
        return False, str(e)

def update_user_usage(username, words_processed):
    """Update a user's usage statistics in the in-memory database."""
    try:
        if username not in users:
            return False, "User not found"
        
        user = users[username]
        user["usage"]["requests"] += 1
        user["usage"]["total_words"] += words_processed
        user["usage"]["last_request"] = datetime.now()
        return True, "Usage updated"
    except Exception as e:
        logger.error(f"Error updating user usage: {str(e)}")
        return False, str(e)

def get_or_create_user(db, user_info):
    """Get or create a user based on Google OAuth information."""
    try:
        # Check if user already exists by Google ID
        google_id = user_info.get("sub")
        for username, user in users.items():
            if user.get("google_id") == google_id:
                return user
        
        # Check if email already exists
        email = user_info.get("email")
        for username, user in users.items():
            if user.get("email") == email:
                # Update existing user with Google ID
                user["google_id"] = google_id
                return user
        
        # Create new user
        username = email.split("@")[0]  # Use part before @ as username
        # Ensure username is unique
        if username in users:
            username = f"{username}_{len(users)}"
            
        new_user = {
            "username": username,
            "email": email,
            "google_id": google_id,
            "name": user_info.get("name", ""),
            "profile_picture": user_info.get("picture", ""),
            "created_at": datetime.now(),
            "usage": {
                "requests": 0,
                "total_words": 0,
                "monthly_words": 0,
                "last_request": None
            }
        }
        
        users[username] = new_user
        return new_user
    except Exception as e:
        logger.error(f"Error creating/getting user: {str(e)}")
        return None
