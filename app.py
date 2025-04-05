from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import os
import logging
from datetime import datetime
import json
import random

# Try importing backend modules with proper error handling
try:
    # Import backend modules
    from backend.api_service import humanize_text, get_api_status, HumanizerAPIError, count_words
    
    # Try to import the MongoDB-based database module
    try:
        from backend.db import init_db, add_user, verify_user, get_user, update_user_usage
        from backend.db import client, db
        
        # Test MongoDB connection
        db.command('ping')
        logger = logging.getLogger(__name__)
        logger.info("MongoDB connection successful")
        using_fallback_db = False
    except Exception as e:
        # If MongoDB connection fails, use the fallback implementation
        logging.warning(f"MongoDB connection failed: {str(e)}. Switching to fallback database.")
        from backend.db_fallback import init_db, add_user, verify_user, get_user, update_user_usage
        from backend.db_fallback import client, db
        using_fallback_db = True
    
    from backend.oauth import get_google_auth_url, get_google_tokens, get_google_user_info, get_or_create_user
    
    # Import support bot module
    from support_bot import register_support_bot
except Exception as e:
    logging.error(f"Error importing modules: {str(e)}")
    raise

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'andikar-ai-development-key')

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
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handle user registration."""
    # Redirect to Google OAuth login
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login - redirect to Google OAuth."""
    # Generate Google OAuth URL
    google_auth_url = get_google_auth_url(url_for('callback', _external=True))
    
    if not google_auth_url:
        flash('Error configuring Google login. Please try again later.', 'danger')
        return redirect(url_for('index'))
    
    # Redirect to Google's OAuth page
    return render_template('login.html', google_auth_url=google_auth_url)

@app.route('/callback', methods=['GET', 'POST'])
def callback():
    """Handle the OAuth callback from Google."""
    # Get authorization code from request
    code = request.args.get('code')
    
    if not code:
        flash('Authentication failed. Please try again.', 'danger')
        return redirect(url_for('login'))
    
    # Exchange code for tokens
    tokens = get_google_tokens(code, url_for('callback', _external=True))
    
    if not tokens:
        flash('Failed to authenticate with Google. Please try again.', 'danger')
        return redirect(url_for('login'))
    
    # Get user info from Google
    user_info = get_google_user_info(tokens)
    
    if not user_info:
        flash('Failed to retrieve your information from Google. Please ensure your email is verified.', 'danger')
        return redirect(url_for('login'))
    
    # Get or create user in our database
    user = get_or_create_user(db, user_info)
    
    if not user:
        flash('Failed to create or find your user account. Please try again.', 'danger')
        return redirect(url_for('login'))
    
    # Set session variables
    session['user_id'] = user['username']
    session['user_email'] = user['email']
    session['user_picture'] = user.get('profile_picture', '')
    
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
    # Only available in development mode
    if os.environ.get('FLASK_ENV') != 'production':
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
        
        # Return debug information
        return render_template('debug.html',
                              user_info=user_info,
                              session=session_data,
                              api_status=api_status,
                              db_status=db_status)
    else:
        return "Debug endpoint not available in production", 404

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring."""
    status = {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "db_connection": "fallback" if using_fallback_db else "mongodb",
        "api_status": get_api_status().get('status', 'unknown')
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
    
    # For regular page requests, redirect to home with a message
    flash(f'Invalid request method: {request.method}', 'danger')
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Run the Flask app
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
