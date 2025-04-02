from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import os
import logging
from datetime import datetime
import json
import random

# Import backend modules
from backend.api_service import humanize_text, get_api_status, HumanizerAPIError, count_words
from backend.db import init_db, add_user, verify_user, get_user, update_user_usage

# Import support bot module
from support_bot import register_support_bot

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
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email', '')
        
        # Basic validation
        if not username or not password:
            flash('Username and password are required', 'danger')
            return render_template('register.html')
        
        # Add user to database
        success, message = add_user(username, password, email)
        
        if success:
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash(f'Registration failed: {message}', 'danger')
            return render_template('register.html')
    
    # GET request - display registration form
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Basic validation
        if not username or not password:
            flash('Username and password are required', 'danger')
            return render_template('login.html')
        
        # Special case for demo account
        if username == 'demo' and password == 'demo':
            session['user_id'] = 'demo'
            flash('Logged in as demo user', 'success')
            return redirect(url_for('dashboard'))
        
        # Verify user credentials
        success, result = verify_user(username, password)
        
        if success:
            # Store user info in session
            session['user_id'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash(f'Login failed: {result}', 'danger')
            return render_template('login.html')
    
    # GET request - display login form
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Handle user logout."""
    # Clear session data
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
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

@app.route('/account')
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
    # Allow both logged-in users and guests to use the humanization from the home page
    # For tracking purposes, we'll still get the user_id if available
    user_id = session.get('user_id', 'guest')
    
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

@app.route('/api/detect-ai', methods=['POST'])
def api_detect_ai():
    """API endpoint to detect AI-generated content."""
    # Get the text from the request
    data = request.json
    text = data.get('text', '')
    
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
    time.sleep(1.5)
    
    # Return the AI detection score
    return jsonify({
        'ai_score': ai_score,
        'analyzed_at': datetime.now().isoformat()
    })

@app.route('/debug')
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
        
        # Return debug information
        return render_template('debug.html',
                              user_info=user_info,
                              session=session_data,
                              api_status=api_status)
    else:
        return "Debug endpoint not available in production", 404

if __name__ == '__main__':
    # Run the Flask app
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
