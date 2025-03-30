"""
Authentication Module
Handles user authentication, JWT token generation/validation,
and user session management
"""

import os
import jwt
import datetime
from functools import wraps
from flask import request, jsonify, current_app, g
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

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

def register_user(username, password, email, account_type='free'):
    """Register a new user (interface to be implemented with your user database)"""
    # This is a placeholder. In a real implementation, you would:
    # 1. Check if username or email already exists
    # 2. Hash the password
    # 3. Store in database
    # 4. Return user ID or error
    
    hashed_password = generate_password_hash(password)
    
    # Example implementation with dummy values
    user_id = f"user_{username}"
    
    # Store in your database here
    
    return {
        'user_id': user_id,
        'username': username,
        'email': email,
        'account_type': account_type
    }

def authenticate_user(username, password):
    """Authenticate a user with username and password"""
    # This is a placeholder. In a real implementation, you would:
    # 1. Look up the user in your database
    # 2. Verify the password hash
    # 3. Return user info or None
    
    # Dummy implementation - replace with database lookup
    # In a real app, fetch the user from database by username
    # and verify password with check_password_hash()
    
    # Example check (replace with actual DB lookup)
    if username == "admin" and password == "admin":  # This is just for testing!
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
