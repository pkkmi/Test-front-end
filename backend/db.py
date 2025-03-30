"""
MongoDB Database Module
Handles connection and operations for the MongoDB database
"""

import os
import logging
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
from werkzeug.security import generate_password_hash, check_password_hash

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB connection string (from environment or hardcoded for testing)
MONGO_URI = os.getenv('MONGO_URI', 'mongodb+srv://edgarmaina003:Andikar_25@oldtrafford.id96k.mongodb.net/?retryWrites=true&w=majority&appName=OldTrafford')

# Initialize client as None, we'll connect lazily
client = None
db = None

def get_db_connection():
    """Get a connection to the MongoDB database"""
    global client, db
    
    if client is None:
        try:
            # Connect to MongoDB
            client = MongoClient(MONGO_URI)
            
            # Ping the server to confirm connection
            client.admin.command('ping')
            logger.info("Successfully connected to MongoDB")
            
            # Get the database
            db = client.andikar_db
            
            # Initialize collections if they don't exist
            if 'users' not in db.list_collection_names():
                db.create_collection('users')
                logger.info("Created 'users' collection")
                
            if 'transactions' not in db.list_collection_names():
                db.create_collection('transactions')
                logger.info("Created 'transactions' collection")
                
            return db
            
        except ConnectionFailure as e:
            logger.error(f"MongoDB connection failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected MongoDB error: {str(e)}")
            raise
    
    return db

# User functions
def get_user(username):
    """Get a user from the database"""
    try:
        db = get_db_connection()
        user = db.users.find_one({"username": username})
        return user
    except Exception as e:
        logger.error(f"Error getting user {username}: {str(e)}")
        return None

def create_user(username, password, email, plan_type='Free'):
    """Create a new user in the database"""
    try:
        db = get_db_connection()
        
        # Check if user already exists
        if db.users.find_one({"username": username}):
            logger.warning(f"User {username} already exists")
            return None
        
        # Create user document
        user = {
            "username": username,
            "password": generate_password_hash(password),
            "email": email,
            "plan": plan_type,
            "joined_date": datetime.datetime.now(),
            "words_used": 0,
            "payment_status": 'Pending' if plan_type != 'Free' else 'N/A',
            "api_keys": {}
        }
        
        # Insert user
        result = db.users.insert_one(user)
        
        if result.acknowledged:
            logger.info(f"Created user {username}")
            # Return user without password for security
            user.pop('password', None)
            return user
        else:
            logger.error(f"Failed to create user {username}")
            return None
    except Exception as e:
        logger.error(f"Error creating user {username}: {str(e)}")
        return None

def authenticate_user(username, password):
    """Authenticate a user with username and password"""
    try:
        db = get_db_connection()
        user = db.users.find_one({"username": username})
        
        if user:
            # Special case for demo account
            if username == 'demo' and password == 'demo':
                return {
                    'user_id': 'demo',
                    'username': 'demo',
                    'account_type': 'Basic'
                }
            
            # Check password hash
            if check_password_hash(user['password'], password):
                return {
                    'user_id': username,
                    'username': username,
                    'account_type': user.get('plan', 'Free')
                }
        
        return None
    except Exception as e:
        logger.error(f"Error authenticating user {username}: {str(e)}")
        return None

def update_user_usage(username, word_count):
    """Update a user's word usage count"""
    try:
        db = get_db_connection()
        result = db.users.update_one(
            {"username": username},
            {"$inc": {"words_used": word_count}}
        )
        
        if result.modified_count > 0:
            logger.info(f"Updated word count for user {username} by {word_count}")
            return True
        else:
            logger.warning(f"No update for user {username}")
            return False
    except Exception as e:
        logger.error(f"Error updating word count for user {username}: {str(e)}")
        return False

def update_user_plan(username, new_plan):
    """Update a user's plan"""
    try:
        db = get_db_connection()
        
        # Update plan and payment status
        payment_status = 'Pending' if new_plan != 'Free' else 'N/A'
        
        result = db.users.update_one(
            {"username": username},
            {"$set": {"plan": new_plan, "payment_status": payment_status}}
        )
        
        if result.modified_count > 0:
            logger.info(f"Updated plan for user {username} to {new_plan}")
            return True
        else:
            logger.warning(f"No update for user {username}")
            return False
    except Exception as e:
        logger.error(f"Error updating plan for user {username}: {str(e)}")
        return False

def update_api_keys(username, gpt_zero_key, originality_key):
    """Update a user's API keys"""
    try:
        db = get_db_connection()
        
        result = db.users.update_one(
            {"username": username},
            {"$set": {
                "api_keys.gpt_zero": gpt_zero_key,
                "api_keys.originality": originality_key
            }}
        )
        
        if result.modified_count > 0:
            logger.info(f"Updated API keys for user {username}")
            return True
        else:
            logger.warning(f"No update for user {username}")
            return False
    except Exception as e:
        logger.error(f"Error updating API keys for user {username}: {str(e)}")
        return False

# Transaction functions
def create_transaction(user_id, amount, phone_number):
    """Create a new transaction"""
    try:
        db = get_db_connection()
        
        # Create transaction ID
        import random
        import string
        transaction_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        
        # Create transaction document
        transaction = {
            "transaction_id": transaction_id,
            "user_id": user_id,
            "amount": amount,
            "phone_number": phone_number,
            "date": datetime.datetime.now(),
            "status": "Completed"
        }
        
        # Insert transaction
        result = db.transactions.insert_one(transaction)
        
        if result.acknowledged:
            # Update user payment status
            db.users.update_one(
                {"username": user_id},
                {"$set": {"payment_status": "Paid"}}
            )
            
            logger.info(f"Created transaction {transaction_id} for user {user_id}")
            return transaction
        else:
            logger.error(f"Failed to create transaction for user {user_id}")
            return None
    except Exception as e:
        logger.error(f"Error creating transaction for user {user_id}: {str(e)}")
        return None

def get_user_transactions(user_id):
    """Get all transactions for a user"""
    try:
        db = get_db_connection()
        transactions = list(db.transactions.find({"user_id": user_id}))
        
        # Convert ObjectId to string for each transaction
        for transaction in transactions:
            transaction['_id'] = str(transaction['_id'])
            
        return transactions
    except Exception as e:
        logger.error(f"Error getting transactions for user {user_id}: {str(e)}")
        return []

# Initialize database and add demo user if it doesn't exist
def init_db():
    """Initialize the database with demo data"""
    try:
        db = get_db_connection()
        
        # Check if demo user exists
        demo_user = db.users.find_one({"username": "demo"})
        
        if not demo_user:
            # Create demo user
            import datetime
            
            demo_user = {
                "username": "demo",
                "password": generate_password_hash("demo"),
                "email": "demo@example.com",
                "plan": "Basic",
                "joined_date": datetime.datetime.now(),
                "words_used": 125,
                "payment_status": "Paid",
                "api_keys": {
                    "gpt_zero": "",
                    "originality": ""
                }
            }
            
            db.users.insert_one(demo_user)
            logger.info("Created demo user")
            
            # Create demo transaction
            transaction = {
                "transaction_id": "TXND3M0123456",
                "user_id": "demo",
                "amount": 500,  # Set an appropriate amount based on your pricing plans
                "phone_number": "254712345678",
                "date": datetime.datetime.now(),
                "status": "Completed"
            }
            
            db.transactions.insert_one(transaction)
            logger.info("Created demo transaction")
            
        return True
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        return False
