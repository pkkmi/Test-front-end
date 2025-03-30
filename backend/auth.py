"""
Authentication and authorization module for Andikar AI.
This module handles user authentication, session management, and permissions.
"""

import functools
import jwt
import os
import time
import datetime
from flask import request, jsonify, session
from models import users_db

# Secret key for JWT tokens
JWT_SECRET = os.environ.get('JWT_SECRET', os.environ.get('SECRET_KEY', 'andikar_secret_key'))
# Token validity time in seconds (default: 24 hours)
TOKEN_EXPIRY = int(os.environ.get('TOKEN_EXPIRY', 86400))

def generate_auth_token(username):
    """
    Generate a JWT token for API authentication
    
    Args:
        username (str): Username to encode in the token
        
    Returns:
        str: JWT token
    """
    payload = {
        'username': username,
        'exp': time.time() + TOKEN_EXPIRY,
        'iat': time.time()
    }
    
    # Add user plan to the token for permission checking
    if username in users_db:
        payload['plan'] = users_db[username]['plan']
        payload['payment_status'] = users_db[username]['payment_status']
    
    token = jwt.encode(payload, JWT_SECRET, algorithm='HS256')
    return token

def verify_auth_token(token):
    """
    Verify a JWT token's validity
    
    Args:
        token (str): JWT token
        
    Returns:
        dict: Token payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        
        # Check if token is expired
        if payload['exp'] < time.time():
            return None
            
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def get_current_user():
    """
    Get the currently authenticated user from session or API token
    
    Returns:
        dict: User data if authenticated, None otherwise
    """
    # First try from session (web interface)
    if 'user_id' in session:
        username = session['user_id']
        if username in users_db:
            return users_db[username]
    
    # Then try from API token (API requests)
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
        payload = verify_auth_token(token)
        
        if payload and 'username' in payload:
            username = payload['username']
            if username in users_db:
                return users_db[username]
    
    return None

def login_required_api(f):
    """
    Decorator for API endpoints that require authentication
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
            
        # Add user to request context for the view function
        request.user = user
        request.username = next((username for username, data in users_db.items() if data == user), None)
        
        return f(*args, **kwargs)
    return decorated_function

def plan_required(min_plan):
    """
    Decorator for API endpoints that require a specific subscription plan
    
    Args:
        min_plan (str): Minimum plan required ('Free', 'Basic', 'Premium')
    """
    def decorator(f):
        @functools.wraps(f)
        @login_required_api
        def decorated_function(*args, **kwargs):
            user = request.user
            plan_hierarchy = {
                'Free': 0,
                'Basic': 1,
                'Premium': 2
            }
            
            # Check if user plan meets the minimum requirement
            if plan_hierarchy.get(user['plan'], -1) < plan_hierarchy.get(min_plan, 0):
                return jsonify({'error': f'This endpoint requires {min_plan} plan or higher'}), 403
                
            # Check payment status for paid plans
            if user['plan'] != 'Free' and user['payment_status'] != 'Paid':
                return jsonify({'error': 'Payment required to access this feature'}), 402
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def validate_user_credentials(username, password):
    """
    Validate user credentials
    
    Args:
        username (str): Username
        password (str): Password
        
    Returns:
        bool: True if credentials are valid
    """
    if username in users_db and users_db[username]['password'] == password:
        return True
    return False
