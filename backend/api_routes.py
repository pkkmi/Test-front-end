"""
API routes module for Andikar AI.
This module defines RESTful API endpoints for the application.
"""

from flask import Blueprint, request, jsonify, session, current_app
import logging
from models import users_db
from backend.auth import login_required_api, plan_required, validate_user_credentials, generate_auth_token
from backend.api_service import humanize_text_api, detect_ai_content_api, get_api_status, ApiRateLimitExceeded, check_rate_limit
from backend.users import (
    get_user_by_username, 
    get_user_account_info,
    update_user_plan,
    update_user_usage,
    check_user_limit,
    register_new_user,
    process_payment,
    update_api_keys
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Blueprint for API routes
api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

# API Routes
@api_bp.route('/health', methods=['GET'])
def health_check():
    """API health check endpoint"""
    return jsonify({
        "status": "ok",
        "message": "Andikar AI API is running"
    })

@api_bp.route('/status', methods=['GET'])
def api_status():
    """Get the status of all external APIs"""
    status = get_api_status()
    return jsonify(status)

@api_bp.route('/auth/login', methods=['POST'])
def login():
    """Login endpoint that returns an API token"""
    data = request.get_json()
    
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({"error": "Username and password are required"}), 400
    
    username = data['username']
    password = data['password']
    
    if validate_user_credentials(username, password):
        # Generate token
        token = generate_auth_token(username)
        
        # Also set session if user is logging in via web
        session['user_id'] = username
        
        return jsonify({
            "message": "Login successful",
            "token": token,
            "user": get_user_by_username(username)
        })
    
    return jsonify({"error": "Invalid credentials"}), 401

@api_bp.route('/auth/logout', methods=['POST'])
@login_required_api
def logout():
    """Logout endpoint"""
    # Clear session
    session.pop('user_id', None)
    
    return jsonify({"message": "Logout successful"})

@api_bp.route('/auth/register', methods=['POST'])
def register():
    """Register a new user"""
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    # Extract required fields
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    
    if not username or not password or not email:
        return jsonify({"error": "Username, password, and email are required"}), 400
    
    # Extract optional fields
    plan_type = data.get('plan_type')
    phone = data.get('phone')
    
    # Register user
    success, message = register_new_user(
        username=username,
        password=password,
        email=email,
        plan_type=plan_type,
        phone=phone
    )
    
    if success:
        # Generate token for immediate login
        token = generate_auth_token(username)
        
        return jsonify({
            "message": message,
            "token": token,
            "user": get_user_by_username(username)
        }), 201
    
    return jsonify({"error": message}), 400

@api_bp.route('/user/profile', methods=['GET'])
@login_required_api
def get_profile():
    """Get user profile information"""
    username = request.username
    
    user_info = get_user_account_info(username)
    
    if not user_info:
        return jsonify({"error": "User not found"}), 404
    
    return jsonify(user_info)

@api_bp.route('/user/update-plan', methods=['POST'])
@login_required_api
def update_plan():
    """Update user subscription plan"""
    username = request.username
    data = request.get_json()
    
    if not data or 'plan' not in data:
        return jsonify({"error": "New plan is required"}), 400
    
    new_plan = data['plan']
    
    success, message = update_user_plan(username, new_plan)
    
    if success:
        return jsonify({"message": message, "plan": new_plan})
    
    return jsonify({"error": message}), 400

@api_bp.route('/user/payment', methods=['POST'])
@login_required_api
def make_payment():
    """Process a payment"""
    username = request.username
    data = request.get_json()
    
    if not data or 'phone_number' not in data:
        return jsonify({"error": "Phone number is required"}), 400
    
    phone_number = data['phone_number']
    amount = data.get('amount')  # Optional, will use plan price if not specified
    
    success, message, transaction_id = process_payment(username, phone_number, amount)
    
    if success:
        return jsonify({
            "message": message,
            "transaction_id": transaction_id,
            "payment_status": "Paid"
        })
    
    return jsonify({"error": message}), 400

@api_bp.route('/user/update-api-keys', methods=['POST'])
@login_required_api
def api_keys():
    """Update user API keys"""
    username = request.username
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    gpt_zero_key = data.get('gpt_zero_key')
    originality_key = data.get('originality_key')
    
    if update_api_keys(username, gpt_zero_key, originality_key):
        return jsonify({"message": "API keys updated successfully"})
    
    return jsonify({"error": "Failed to update API keys"}), 400

@api_bp.route('/humanize', methods=['POST'])
@login_required_api
@plan_required('Free')  # At least Free plan required
def humanize_text():
    """Humanize AI-generated text"""
    username = request.username
    user = request.user
    data = request.get_json()
    
    if not data or 'text' not in data:
        return jsonify({"error": "Text to humanize is required"}), 400
    
    text = data['text']
    
    # Check payment status for paid plans
    if user['plan'] != 'Free' and user['payment_status'] != 'Paid':
        return jsonify({
            "error": "Payment required to access this feature",
            "payment_required": True
        }), 402
    
    # Check word limit
    has_exceeded, remaining = check_user_limit(username)
    if has_exceeded:
        return jsonify({
            "error": "Word limit exceeded for your plan",
            "remaining_words": 0,
            "upgrade_required": True
        }), 403
    
    # Check rate limit
    try:
        check_rate_limit(username, user['plan'])
    except ApiRateLimitExceeded as e:
        return jsonify({"error": str(e), "rate_limited": True}), 429
    
    # Process the text
    humanized_text, message, status_code = humanize_text_api(text, user['plan'])
    
    if status_code != 200:
        return jsonify({"error": message}), status_code
    
    # Update word usage
    word_count = len(text.split())
    update_user_usage(username, word_count)
    
    return jsonify({
        "original_text": text,
        "humanized_text": humanized_text,
        "message": message,
        "words_processed": word_count,
        "remaining_words": max(0, remaining - word_count)
    })

@api_bp.route('/detect', methods=['POST'])
@login_required_api
@plan_required('Basic')  # At least Basic plan required
def detect_ai():
    """Detect if text is AI-generated"""
    username = request.username
    user = request.user
    data = request.get_json()
    
    if not data or 'text' not in data:
        return jsonify({"error": "Text to analyze is required"}), 400
    
    text = data['text']
    
    # Check payment status
    if user['payment_status'] != 'Paid':
        return jsonify({
            "error": "Payment required to access this feature",
            "payment_required": True
        }), 402
    
    # Check rate limit
    try:
        check_rate_limit(username, user['plan'])
    except ApiRateLimitExceeded as e:
        return jsonify({"error": str(e), "rate_limited": True}), 429
    
    # Get API keys if available
    api_keys = user.get('api_keys', {})
    
    # Process the text
    result, message, status_code = detect_ai_content_api(text, api_keys)
    
    if status_code != 200:
        return jsonify({"error": message}), status_code
    
    return jsonify({
        "result": result,
        "message": message
    })

# Error handlers
@api_bp.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@api_bp.errorhandler(500)
def server_error(error):
    logger.error(f"Server error: {error}")
    return jsonify({"error": "Internal server error"}), 500
