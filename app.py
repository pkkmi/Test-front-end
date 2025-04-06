# Deployment helper - this will verify that code is being deployed properly
try:
    import deploy_helper
except Exception as e:
    print(f"Failed to import deploy_helper: {e}")

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import os
import logging
from datetime import datetime, timedelta
import json
import random
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Log startup message
logger.warning("APPLICATION STARTING - APP.PY UPDATED VERSION")

# Try importing backend modules with proper error handling
try:
    # Import API service first
    from backend.api_service import humanize_text, get_api_status, HumanizerAPIError, count_words
    logger.info("Successfully imported API service")
    
    # Try to import the MongoDB-based database module
    try:
        from backend.db import init_db, add_user, verify_user, get_user, update_user_usage
        from backend.db import client, db
        
        # Test MongoDB connection
        db.command('ping')
        logger.info("MongoDB connection successful")
        using_fallback_db = False
    except Exception as e:
        # If MongoDB connection fails, use the fallback implementation
        logger.warning(f"MongoDB connection failed: {str(e)}. Switching to fallback database.")
        logger.warning(traceback.format_exc())
        from backend.db_fallback import init_db, add_user, verify_user, get_user, update_user_usage
        from backend.db_fallback import client, db
        using_fallback_db = True
    
    from backend.oauth import get_google_auth_url, get_google_tokens, get_google_user_info, get_or_create_user
    
    # Import support bot module
    from support_bot import register_support_bot
except Exception as e:
    logger.error(f"Error importing modules: {str(e)}")
    logger.error(traceback.format_exc())
    raise

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'andikar-ai-development-key')
# Extend session lifetime
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# Print all environment variables for debugging (redacted for security)
env_vars = {k: (v[:5] + "..." + v[-5:] if len(v) > 15 else "***") for k, v in os.environ.items()}
logger.info(f"Environment variables (redacted): {env_vars}")

# Add environment variable info to session for debugging
app.config['GOOGLE_CLIENT_ID'] = os.environ.get("GOOGLE_CLIENT_ID", "934412857118-i13t5ma9afueo40tmohosprsjf4555f0.apps.googleusercontent.com")
app.config['GOOGLE_CLIENT_SECRET_SET'] = bool(os.environ.get("GOOGLE_CLIENT_SECRET"))
logger.info(f"Google Client ID: {app.config['GOOGLE_CLIENT_ID'][:5]}...{app.config['GOOGLE_CLIENT_ID'][-5:]}")
logger.info(f"Google Client Secret is set: {app.config['GOOGLE_CLIENT_SECRET_SET']}")

# Initialize database
init_db()

# Register support bot blueprint
register_support_bot(app)

# Check API status on startup
api_status = get_api_status()
logger.info(f"\nAPI Status: {api_status.get('status', 'unknown')}")
if api_status.get('status') != 'online':
    logger.warning(f"API is not fully operational: {api_status.get('message', 'Unknown error')}")

@app.route('/')
def index():
    """Render the homepage with text processing capabilities."""
    # For the simplified home page that can handle both logged-in and guest users
    # If user is logged in, redirect to humanize page
    if 'user_id' in session:
        return redirect(url_for('humanize'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handle user registration."""
    # Redirect to Google OAuth login
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login - redirect to Google OAuth."""
    # Add OAuth config info to session for debugging
    session['google_client_id'] = app.config['GOOGLE_CLIENT_ID']
    session['google_client_secret'] = app.config['GOOGLE_CLIENT_SECRET_SET']
    session.permanent = True  # Make session persistent
    
    # Generate Google OAuth URL
    google_auth_url = get_google_auth_url(url_for('callback', _external=True))
    
    if not google_auth_url:
        flash('Error configuring Google login. Please try again later.', 'danger')
        logger.error("Failed to generate Google auth URL")
        return redirect(url_for('index'))
    
    logger.info(f"Generated Google auth URL: {google_auth_url[:50]}...")
    
    # Redirect to Google's OAuth page
    return render_template('login.html', google_auth_url=google_auth_url)

@app.route('/callback')
def callback():
    """Handle the OAuth callback from Google."""
    # Log all request details for debugging
    logger.info(f"Callback received - Full URL: {request.url}")
    logger.info(f"Request args: {request.args}")
    
    # Get authorization code from request
    code = request.args.get('code')
    error = request.args.get('error')
    
    logger.info(f"Callback received - code exists: {bool(code)}, error: {error}")
    
    if error:
        flash(f'Authentication error: {error}. Please try again.', 'danger')
        logger.error(f"OAuth error returned: {error}")
        return redirect(url_for('login'))
    
    if not code:
        flash('Authentication failed. Please try again.', 'danger')
        logger.error("No authorization code in callback")
        return redirect(url_for('login'))
    
    # Exchange code for tokens
    logger.info(f"Exchanging code for tokens...")
    tokens = get_google_tokens(code, url_for('callback', _external=True))
    
    if not tokens:
        flash('Failed to authenticate with Google. Please try again.', 'danger')
        logger.error("Failed to get tokens from Google OAuth")
        return redirect(url_for('login'))
    
    # Get user info from Google
    logger.info(f"Getting user info from Google...")
    user_info = get_google_user_info(tokens)
    
    if not user_info:
        flash('Failed to retrieve your information from Google. Please ensure your email is verified.', 'danger')
        logger.error("Failed to get user info from Google")
        return redirect(url_for('login'))
    
    # Get or create user in our database
    logger.info(f"Getting or creating user in database...")
    user = get_or_create_user(db, user_info)
    
    if not user:
        flash('Failed to create or find your user account. Please try again.', 'danger')
        logger.error("Failed to get or create user in database")
        return redirect(url_for('login'))
    
    # Set session variables
    session['user_id'] = user['username']
    session['user_email'] = user['email']
    session['user_picture'] = user.get('profile_picture', '')
    session.permanent = True  # Make session persistent
    
    logger.info(f"User logged in successfully: {user['username']}")
    
    # Success message
    flash(f'Welcome, {user["username"]}!', 'success')
    
    # Redirect to humanize page
    return redirect(url_for('humanize'))

@app.route('/demo-login', methods=['GET', 'POST'])
def demo_login():
    """Handle demo account login."""
    # Set session for demo user
    session['user_id'] = 'demo'
    session['user_email'] = 'demo@example.com'
    session['user_picture'] = ''
    session.permanent = True  # Make session persistent
    
    flash('Logged in as demo user', 'success')
    return redirect(url_for('humanize'))

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    """Handle user logout."""
    # Clear session data
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard', methods=['GET'])
def dashboard():
    """Render the user dashboard."""
    # Check if user is logged in
    if 'user_id' not in session:
        flash('Please log in to access the dashboard', 'warning')
        return redirect(url_for('login'))
    
    # Get user info
    user_id = session['user_id']
    user = get_user(user_id)
    
    # Render dashboard template with user info
    return render_template('dashboard.html', 
                          user=user, 
                          api_status=get_api_status())

@app.route('/account', methods=['GET'])
def account():
    """Render the user account page."""
    # Check if user is logged in
    if 'user_id' not in session:
        flash('Please log in to access your account', 'warning')
        return redirect(url_for('login'))
    
    # Get user info
    user_id = session['user_id']
    user = get_user(user_id)
    
    # Render account template with user info
    return render_template('account.html', user=user)

@app.route('/humanize', methods=['GET', 'POST'])
def humanize():
    """Handle text humanization requests."""
    # Check if user is logged in
    if 'user_id' not in session:
        flash('Please log in to access the humanize feature', 'warning')
        return redirect(url_for('login'))
    
    # Get user_id for tracking purposes
    user_id = session.get('user_id')
    
    if request.method == 'POST':
        # Get original text from form
        original_text = request.form.get('original_text', '')
        
        if not original_text:
            flash('Please enter text to humanize', 'warning')
            # If request comes from home page, redirect back to home
            if request.referrer and 'humanize' not in request.referrer:
                return redirect(url_for('index'))
            return render_template('humanize.html')
        
        # Count words in the input text
        word_count = count_words(original_text)
        
        try:
            # Call the API through our backend service
            result = humanize_text(original_text, user_id)
            humanized_text = result.get('humanized_text', '')
            
            # Prepare success message
            message = "Text humanized successfully!"
            message_type = "success"
            
            # Get metrics
            metrics = result.get('metrics', {})
            api_response_time = metrics.get('response_time', None)
            api_source = "External API"
            
            # Render the template with results
            return render_template('humanize.html',
                                  original_text=original_text,
                                  humanized_text=humanized_text,
                                  metrics=metrics,
                                  message=message,
                                  message_type=message_type,
                                  api_source=api_source,
                                  api_response_time=api_response_time,
                                  word_count=word_count)
                                  
        except HumanizerAPIError as e:
            # API error
            message = f"API Error: {str(e)}"
            flash(message, 'danger')
            # If request comes from home page, redirect back to home
            if request.referrer and 'humanize' not in request.referrer:
                return redirect(url_for('index'))
            return render_template('humanize.html', 
                                  original_text=original_text,
                                  message=message,
                                  message_type="danger",
                                  word_count=word_count)
        except Exception as e:
            # Unexpected error
            message = f"Unexpected error: {str(e)}"
            flash(message, 'danger')
            # If request comes from home page, redirect back to home
            if request.referrer and 'humanize' not in request.referrer:
                return redirect(url_for('index'))
            return render_template('humanize.html', 
                                  original_text=original_text,
                                  message=message,
                                  message_type="danger",
                                  word_count=word_count)
    
    # GET request - display humanize form
    return render_template('humanize.html')

@app.route('/api/word-count', methods=['POST'])
def api_word_count():
    """API endpoint to count words in text."""
    # Get the text from the request
    data = request.json
    text = data.get('text', '')
    
    # Count words
    word_count = count_words(text)
    
    # Return word count
    return jsonify({
        'word_count': word_count
    })

@app.route('/api/detect-ai', methods=['GET', 'POST'])
def api_detect_ai():
    """API endpoint to detect AI-generated content."""
    # Handle both GET and POST requests
    if request.method == 'POST':
        # For POST requests, get text from request body
        data = request.json or {}
        text = data.get('text', '')
    else:
        # For GET requests, get text from query parameter
        text = request.args.get('text', '')
    
    if not text:
        return jsonify({
            'error': 'No text provided'
        }), 400
    
    # In a real implementation, you would call an AI detection service
    # For this demo, we'll simulate a detection algorithm
    
    # Simple simulation of AI detection (random score with some factors)
    word_count = count_words(text)
    
    # Base score - for demo purposes
    if word_count < 50:
        # Short texts get more random scores
        base_score = random.randint(15, 85)
    else:
        # Longer texts tend to lean more toward "AI-written" for this demo
        base_score = random.randint(40, 95)
    
    # Add some variance based on text characteristics
    # More complex logic would be implemented in a real detector
    
    # Final AI score
    ai_score = min(max(base_score, 0), 100)
    
    # Round to integer
    ai_score = round(ai_score)
    
    # Add a small delay to simulate processing
    import time
    time.sleep(0.5)  # Reduced delay to improve responsiveness
    
    # Return the AI detection score
    return jsonify({
        'ai_score': ai_score,
        'analyzed_at': datetime.now().isoformat()
    })

@app.route('/debug', methods=['GET'])
def debug():
    """Debug endpoint to show application state."""
    # Allow access in all environments for troubleshooting during development
    # Get all registered users
    users = []
    
    # Current user info
    user_info = None
    if 'user_id' in session:
        user_id = session['user_id']
        user = get_user(user_id)
        if user:
            user_info = {
                'username': user.get('username', user_id),
                'email': user.get('email', 'unknown'),
                'usage': user.get('usage', {})
            }
    
    # API status
    api_status = get_api_status()
    
    # Session data
    session_data = dict(session)
    
    # Database status
    db_status = "Using fallback in-memory database" if using_fallback_db else "Using MongoDB"
    
    # Environment info
    env_info = {
        "RAILWAY_STATIC_URL": os.environ.get("RAILWAY_STATIC_URL", "Not set"),
        "PORT": os.environ.get("PORT", "Not set"),
        "NIXPACKS_PYTHON_VERSION": os.environ.get("NIXPACKS_PYTHON_VERSION", "Not set"),
        "GOOGLE_CLIENT_SECRET_SET": bool(os.environ.get("GOOGLE_CLIENT_SECRET")),
        "DEPLOYMENT_ID": os.environ.get("RAILWAY_DEPLOYMENT_ID", "Not set")[:8] + "...",
        "GIT_COMMIT": os.environ.get("RAILWAY_GIT_COMMIT_SHA", "Not set")[:8] + "..."
    }
    
    # File status
    file_status = {}
    for path in ["/app/app.py", "/app/backend/db_fallback.py", "/app/backend/oauth.py"]:
        if os.path.exists(path):
            size = os.path.getsize(path)
            mtime = datetime.fromtimestamp(os.path.getmtime(path))
            file_status[path] = f"Exists: {size} bytes, modified: {mtime}"
        else:
            file_status[path] = "DOES NOT EXIST"
    
    # Return debug information
    return render_template('debug.html',
                          user_info=user_info,
                          session=session_data,
                          api_status=api_status,
                          db_status=db_status,
                          env_info=env_info,
                          file_status=file_status)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring."""
    status = {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "db_connection": "fallback" if using_fallback_db else "mongodb",
        "api_status": get_api_status().get('status', 'unknown'),
        "oauth_configured": bool(os.environ.get("GOOGLE_CLIENT_SECRET")),
        "environment": os.environ.get("RAILWAY_ENVIRONMENT", "unknown"),
        "deployment_id": os.environ.get("RAILWAY_DEPLOYMENT_ID", "unknown")[:8] + "...",
        "git_commit": os.environ.get("RAILWAY_GIT_COMMIT_SHA", "unknown")[:8] + "..."
    }
    return jsonify(status)

@app.errorhandler(405)
def method_not_allowed(e):
    """Handle Method Not Allowed errors gracefully."""
    app.logger.error(f"Method Not Allowed error: {request.method} {request.path}")
    
    # Check if the request is for an API endpoint
    if request.path.startswith('/api/'):
        return jsonify({
            'error': 'Method not allowed',
            'message': f'The method {request.method} is not allowed for this endpoint',
            'allowed_methods': e.valid_methods
        }), 405
    
    # For regular page requests, show a custom error page
    return render_template('errors/405.html', 
                          allowed_methods=e.valid_methods), 405

# Register error handlers for common HTTP errors
@app.errorhandler(400)
def bad_request(e):
    """Handle Bad Request errors."""
    app.logger.error(f"Bad Request error: {request.method} {request.path}")
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Bad Request', 'message': str(e)}), 400
    flash('Invalid request. Please try again.', 'danger')
    return redirect(url_for('index'))

@app.errorhandler(404)
def page_not_found(e):
    """Handle Page Not Found errors."""
    app.logger.error(f"Page Not Found: {request.method} {request.path}")
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Not Found', 'message': 'The requested resource was not found'}), 404
    
    # For logged-in users, redirect to humanize without flash message
    if 'user_id' in session:
        return redirect(url_for('humanize'))
    
    # For regular users, show error message
    flash('The page you requested was not found.', 'warning')
    return redirect(url_for('index'))

@app.errorhandler(500)
def internal_server_error(e):
    """Handle Internal Server Error."""
    app.logger.error(f"Internal Server Error: {request.method} {request.path}")
    app.logger.exception("Exception details")
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Internal Server Error', 'message': 'An unexpected error occurred'}), 500
    flash('An unexpected error occurred. Please try again later.', 'danger')
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Run the Flask app
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
