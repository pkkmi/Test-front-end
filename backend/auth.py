"""
Authentication Module
Handles user authentication, JWT token generation/validation,
and user session management
"""

import os
import jwt
import datetime
from functools import wraps
from flask import request, jsonify, current_app, g, session
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# Import the user database
from models import users_db

load_dotenv()

# JWT configuration
JWT_SECRET = os.getenv('JWT_SECRET', 'dev-secret-key')
JWT_EXPIRATION = int(os.getenv('JWT_EXPIRATION', 3600))  # 1 hour by default

# User session store (replace with database in production)
active_sessions = {}

def generate_token(user_id, account_type):
    """Generate a JWT token for the authenticated user"""
    payload = {
        'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=JWT_EXPIRATION),
        'iat': datetime.datetime.utcnow(),
        'sub': user_id,
        'account_type': account_type
    }
    return jwt.encode(
        payload,
        JWT_SECRET,
        algorithm='HS256'
    )

def decode_token(token):
    """Decode and validate a JWT token"""
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=['HS256']
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None  # Token has expired
    except jwt.InvalidTokenError:
        return None  # Invalid token

def token_required(f):
    """Decorator to protect routes with JWT authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        
        if auth_header:
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({'message': 'Authentication token is missing'}), 401
            
        payload = decode_token(token)
        if not payload:
            return jsonify({'message': 'Invalid or expired token'}), 401
        
        # Store user info in g for access in the route function
        g.user_id = payload['sub']
        g.account_type = payload['account_type']
        
        return f(*args, **kwargs)
    
    return decorated

def login_required_api(f):
    """Decorator for Flask route that requires login"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'message': 'Login required'}), 401
        return f(*args, **kwargs)
    return decorated

def register_user(username, password, email, account_type='free'):
    """Register a new user"""
    # Check if username already exists
    if username in users_db:
        return None  # Username already exists
    
    # Hash the password
    hashed_password = generate_password_hash(password)
    
    # Create user entry
    users_db[username] = {
        'password': hashed_password,  # Store the hashed password
        'email': email,
        'plan': account_type.capitalize(),  # Capitalize for consistency
        'joined_date': datetime.datetime.now().strftime('%Y-%m-%d'),
        'words_used': 0,
        'payment_status': 'Pending' if account_type.lower() != 'free' else 'N/A',
        'api_keys': {
            'gpt_zero': '',
            'originality': ''
        }
    }
    
    # Return user info
    return {
        'user_id': username,
        'username': username,
        'email': email,
        'account_type': account_type
    }

def authenticate_user(username, password):
    """Authenticate a user with username and password"""
    # Check if we have a demo user (from app.py)
    if username == "demo" and password == "demo" and "demo" in users_db:
        return {
            'user_id': 'demo',
            'username': 'demo',
            'account_type': 'Basic'
        }
    
    # Check if username exists
    if username not in users_db:
        return None
    
    # Get stored user data
    user_data = users_db[username]
    
    # Check if password is stored as hash
    if user_data['password'].startswith('pbkdf2:sha256:') or user_data['password'].startswith('scrypt:'):
        # Verify hashed password
        if check_password_hash(user_data['password'], password):
            return {
                'user_id': username,
                'username': username,
                'account_type': user_data['plan']
            }
    else:
        # Plain text password (only for development!)
        if user_data['password'] == password:
            return {
                'user_id': username,
                'username': username,
                'account_type': user_data['plan']
            }
    
    # Admin fallback for testing
    if username == "admin" and password == "admin":
        return {
            'user_id': 'admin_user',
            'username': 'admin',
            'account_type': 'admin'
        }
        
    return None

def logout_user(user_id):
    """Logout a user (invalidate their session)"""
    if user_id in active_sessions:
        del active_sessions[user_id]
    return True
