"""
API Routes Module
Defines REST API endpoints for the backend
"""

from flask import Blueprint, request, jsonify, g
from flask_restful import Api, Resource
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import time
import logging
from functools import wraps

from .auth import token_required, authenticate_user, generate_token, register_user, logout_user
from .users import get_user_info, get_user_rate_limit, check_feature_access
from .api_service import humanize_text, get_api_status, HumanizerAPIError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Blueprint
api_bp = Blueprint('api', __name__)

# Initialize rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Initialize API
api = Api(api_bp)

# Request timing middleware
@api_bp.before_request
def start_timer():
    g.start_time = time.time()

@api_bp.after_request
def log_request(response):
    if hasattr(g, 'start_time'):
        total_time = time.time() - g.start_time
        logger.info(f"Request processed in {total_time:.2f}s: {request.method} {request.path} -> {response.status_code}")
    return response

# Helper function to require specific features
def require_feature(feature_name):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'user_id'):
                return jsonify({'message': 'Authentication required'}), 401
                
            if not check_feature_access(g.user_id, feature_name):
                return jsonify({'message': f'Access to {feature_name} not available with your account type'}), 403
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# API Resources
class AuthResource(Resource):
    def post(self):
        """Handle user login"""
        data = request.get_json()
        
        if not data:
            return {'message': 'No input data provided'}, 400
            
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return {'message': 'Username and password are required'}, 400
            
        user = authenticate_user(username, password)
        
        if not user:
            return {'message': 'Invalid username or password'}, 401
            
        token = generate_token(user['user_id'], user['account_type'])
        
        return {
            'message': 'Login successful',
            'token': token,
            'user': {
                'user_id': user['user_id'],
                'username': user['username'],
                'account_type': user['account_type']
            }
        }, 200

class RegisterResource(Resource):
    def post(self):
        """Handle user registration"""
        data = request.get_json()
        
        if not data:
            return {'message': 'No input data provided'}, 400
            
        username = data.get('username')
        password = data.get('password')
        email = data.get('email')
        
        if not username or not password or not email:
            return {'message': 'Username, password, and email are required'}, 400
            
        user = register_user(username, password, email)
        
        return {
            'message': 'User registered successfully',
            'user': {
                'user_id': user['user_id'],
                'username': user['username'],
                'email': user['email'],
                'account_type': user['account_type']
            }
        }, 201

class LogoutResource(Resource):
    @token_required
    def post(self):
        """Handle user logout"""
        user_id = g.user_id
        logout_user(user_id)
        
        return {
            'message': 'Logout successful'
        }, 200

class UserResource(Resource):
    @token_required
    def get(self):
        """Get user account information"""
        user_id = g.user_id
        user_info = get_user_info(user_id)
        
        if not user_info:
            return {'message': 'User not found'}, 404
            
        return user_info, 200

class HumanizeResource(Resource):
    @token_required
    @limiter.limit("10 per minute")
    def post(self):
        """Humanize text through the API"""
        data = request.get_json()
        
        if not data:
            return {'message': 'No input data provided'}, 400
            
        text = data.get('text')
        
        if not text:
            return {'message': 'Text is required'}, 400
            
        user_id = g.user_id
        account_type = g.account_type
        
        try:
            result = humanize_text(text, user_id, account_type)
            return result, 200
        except HumanizerAPIError as e:
            return {'message': str(e)}, 429
        except Exception as e:
            logger.error(f"Error in humanize endpoint: {str(e)}")
            return {'message': 'An error occurred while processing your request'}, 500

class StatusResource(Resource):
    def get(self):
        """Get API status"""
        api_status = get_api_status()
        return api_status, 200

# Register resources
api.add_resource(AuthResource, '/auth/login')
api.add_resource(RegisterResource, '/auth/register')
api.add_resource(LogoutResource, '/auth/logout')
api.add_resource(UserResource, '/user')
api.add_resource(HumanizeResource, '/humanize')
api.add_resource(StatusResource, '/status')

# Initialize Blueprint
def init_app(app):
    """Initialize the API with the Flask app"""
    limiter.init_app(app)
    app.register_blueprint(api_bp, url_prefix='/api/v1')
