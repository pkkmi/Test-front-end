from flask import Flask, render_template_string, request, redirect, url_for, session, flash, jsonify
import random
import string
import datetime
import re
import os
import requests
import logging
from functools import wraps

from config import APP_NAME, pricing_plans
from templates import html_templates
from debug_file import debug_users  # Import debug utility

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(32)))

# Import backend modules for API communication and database
from backend.api_service import humanize_text, get_api_status, HumanizerAPIError
from backend.db import get_user, create_user, authenticate_user, update_user_usage, update_user_plan, get_user_transactions, init_db, create_transaction

# Login decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function

# Routes
@app.route('/')
def index():
    return render_template_string(html_templates['index.html'])


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        logger.info(f"Login attempt for user: {username}")
        
        # Authenticate user using DB
        user = authenticate_user(username, password)
        
        if user:
            session['user_id'] = user['user_id']
            session['account_type'] = user['account_type']
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
            logger.warning(f"Failed login attempt for user: {username}")

    return render_template_string(html_templates['login.html'])


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        plan_type = request.form.get('plan_type', 'Free')
        email = request.form.get('email', f"{username}@example.com")
        
        logger.info(f"Registration attempt for user: {username}")
        
        # Create user in database
        user = create_user(username, password, email, plan_type)
        
        if user:
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Registration failed. Username may already exist.', 'error')

    return render_template_string(html_templates['register.html'], pricing_plans=pricing_plans)


@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session.get('user_id')
    
    # Get user data from database
    user_data = get_user(user_id)
    
    if not user_data:
        flash('User account not found. Please log in again.', 'error')
        return redirect(url_for('logout'))
    
    # Format user data for template
    user_info = {
        'username': user_id,
        'email': user_data.get('email', f"{user_id}@example.com"),
        'plan': user_data.get('plan', 'Free'),
        'joined_date': user_data.get('joined_date').strftime('%Y-%m-%d') if user_data.get('joined_date') else 'Unknown',
        'words_used': user_data.get('words_used', 0),
        'payment_status': user_data.get('payment_status', 'Pending')
    }
    
    return render_template_string(html_templates['dashboard.html'], 
                                 user=user_info,
                                 plan=pricing_plans[user_info['plan']])


@app.route('/humanize', methods=['GET', 'POST'])
@login_required
def humanize():
    message = ""
    humanized_text = ""
    original_text = ""
    api_response_time = None
    
    user_id = session.get('user_id')
    account_type = session.get('account_type', 'Free')
    
    # Get user data from database
    user_data = get_user(user_id)
    
    if not user_data:
        flash('User account not found. Please log in again.', 'error')
        return redirect(url_for('logout'))
    
    # Get word limit from plan
    plan_type = user_data.get('plan', 'Free')
    word_limit = pricing_plans[plan_type]['word_limit']
    words_used = user_data.get('words_used', 0)
    words_remaining = max(0, word_limit - words_used)
    
    if request.method == 'POST':
        original_text = request.form['original_text']
        
        # Check if user has enough words remaining
        if words_remaining > 0:
            try:
                # Call the external API to humanize text
                logger.info(f"Sending text to humanizer API for user: {user_id}")
                
                # Call API through our service
                result = humanize_text(original_text, user_id, account_type)
                
                # Extract humanized text
                humanized_text = result.get('humanized_text', '')
                api_response_time = result.get('metrics', {}).get('response_time', None)
                
                if not humanized_text:
                    raise HumanizerAPIError("API returned empty response")
                
                # Update words used in database
                input_word_count = len(original_text.split())
                update_user_usage(user_id, input_word_count)
                
                message = "Text successfully humanized!"
                logger.info(f"Text humanized successfully for user: {user_id}")
                
            except HumanizerAPIError as e:
                message = f"API Error: {str(e)}"
                logger.error(f"API error for user {user_id}: {str(e)}")
                flash(message, 'error')
                
            except Exception as e:
                message = f"Unexpected error: {str(e)}"
                logger.error(f"Unexpected error for user {user_id}: {str(e)}")
                flash(message, 'error')
        else:
            message = "You have reached your word limit. Please upgrade your plan for more words."
            flash(message, 'warning')

    return render_template_string(html_templates['humanize.html'],
                                 message=message,
                                 humanized_text=humanized_text,
                                 original_text=original_text,
                                 word_limit=word_limit,
                                 words_used=words_used,
                                 words_remaining=words_remaining,
                                 api_response_time=api_response_time)


@app.route('/detect', methods=['GET', 'POST'])
@login_required
def detect():
    result = None
    message = ""
    
    user_id = session.get('user_id')
    
    # Get user data from database
    user_data = get_user(user_id)
    
    if not user_data:
        flash('User account not found. Please log in again.', 'error')
        return redirect(url_for('logout'))
    
    # Get user plan
    plan_type = user_data.get('plan', 'Free')
    
    # Check if user has access to detection feature
    feature_access = plan_type != 'Free'
    
    if request.method == 'POST':
        text = request.form['text']

        # Check if user has access to the feature
        if feature_access:
            # Simulate AI detection (just for demo)
            result = {
                'ai_probability': random.uniform(0.1, 0.9),
                'human_probability': random.uniform(0.1, 0.9),
                'analysis': {
                    'incoherence': random.uniform(0, 1),
                    'repetition': random.uniform(0, 1),
                    'complexity': random.uniform(0, 1)
                }
            }
            
            # Normalize probabilities
            total = result['ai_probability'] + result['human_probability']
            result['ai_probability'] = result['ai_probability'] / total
            result['human_probability'] = result['human_probability'] / total
            
            message = "Content analyzed successfully."
        else:
            message = "This feature is not available with your current plan. Please upgrade to access AI detection."
            flash(message, 'warning')

    return render_template_string(html_templates['detect.html'],
                                 result=result,
                                 message=message,
                                 feature_access=feature_access)


@app.route('/account')
@login_required
def account():
    user_id = session.get('user_id')
    
    # Get user data from database
    user_data = get_user(user_id)
    
    if not user_data:
        flash('User account not found. Please log in again.', 'error')
        return redirect(url_for('logout'))
    
    # Format user data for template
    user_info = {
        'username': user_id,
        'email': user_data.get('email', f"{user_id}@example.com"),
        'plan': user_data.get('plan', 'Free'),
        'joined_date': user_data.get('joined_date').strftime('%Y-%m-%d') if user_data.get('joined_date') else 'Unknown',
        'words_used': user_data.get('words_used', 0),
        'payment_status': user_data.get('payment_status', 'Pending')
    }
    
    # Get user transactions
    transactions = get_user_transactions(user_id)
    
    # Format transactions for display
    formatted_transactions = []
    for t in transactions:
        formatted_transactions.append({
            'transaction_id': t.get('transaction_id', ''),
            'date': t.get('date').strftime('%Y-%m-%d %H:%M:%S') if t.get('date') else '',
            'amount': t.get('amount', 0),
            'status': t.get('status', 'Pending')
        })
    
    return render_template_string(html_templates['account.html'], 
                                 user=user_info,
                                 plan=pricing_plans[user_info['plan']],
                                 transactions=formatted_transactions)


@app.route('/api-integration', methods=['GET', 'POST'])
@login_required
def api_integration():
    user_id = session.get('user_id')
    
    # Get user data from database
    user_data = get_user(user_id)
    
    if not user_data:
        flash('User account not found. Please log in again.', 'error')
        return redirect(url_for('logout'))
    
    # Get user plan
    plan_type = user_data.get('plan', 'Free')
    
    # Check if user has API access
    api_access = plan_type in ['Premium', 'Enterprise']
    
    if not api_access:
        flash('API access not available with your current plan', 'warning')
        return redirect(url_for('account'))
    
    # Handle API key updates
    if request.method == 'POST':
        gpt_zero_key = request.form.get('gpt_zero_key', '')
        originality_key = request.form.get('originality_key', '')
        
        # Update API keys in database
        from backend.db import update_api_keys
        update_api_keys(user_id, gpt_zero_key, originality_key)
        
        flash('API keys updated successfully!', 'success')
        return redirect(url_for('api_integration'))

    return render_template_string(html_templates['api_integration.html'],
                                 api_keys=user_data.get('api_keys', {}))


@app.route('/faq')
def faq():
    return render_template_string(html_templates['faq.html'])


@app.route('/community')
def community():
    return render_template_string(html_templates['community.html'])


@app.route('/download')
def download():
    return render_template_string(html_templates['download.html'])


@app.route('/pricing')
def pricing():
    return render_template_string(html_templates['pricing.html'], pricing_plans=pricing_plans)


@app.route('/payment', methods=['GET', 'POST'])
@login_required
def payment():
    user_id = session.get('user_id')
    
    # Get user data from database
    user_data = get_user(user_id)
    
    if not user_data:
        flash('User account not found. Please log in again.', 'error')
        return redirect(url_for('logout'))
    
    # Get user plan
    plan_type = user_data.get('plan', 'Free')
    
    if request.method == 'POST':
        phone_number = request.form['phone_number']
        
        # Get plan price
        amount = pricing_plans[plan_type]['price']

        # Create transaction in database
        transaction = create_transaction(user_id, amount, phone_number)
        
        if transaction:
            flash('Payment processed successfully!', 'success')
            return redirect(url_for('account'))
        else:
            flash('Payment processing failed. Please try again.', 'error')

    return render_template_string(html_templates['payment.html'],
                                 plan=pricing_plans[plan_type])


@app.route('/upgrade', methods=['GET', 'POST'])
@login_required
def upgrade():
    user_id = session.get('user_id')
    
    # Get user data from database
    user_data = get_user(user_id)
    
    if not user_data:
        flash('User account not found. Please log in again.', 'error')
        return redirect(url_for('logout'))
    
    # Get user plan
    current_plan = user_data.get('plan', 'Free')
    
    if request.method == 'POST':
        new_plan = request.form['new_plan']
        
        # Update user plan in database
        success = update_user_plan(user_id, new_plan)
        
        if success:
            flash(f'Plan upgraded to {new_plan} successfully!', 'success')
            
            # Redirect to payment if needed
            if new_plan != 'Free':
                return redirect(url_for('payment'))
            return redirect(url_for('account'))
        else:
            flash('Failed to upgrade plan', 'error')
            return redirect(url_for('upgrade'))

    # Get available plans
    available_plans = {k: v for k, v in pricing_plans.items() if k != current_plan}
    return render_template_string(html_templates['upgrade.html'], 
                                 current_plan=pricing_plans[current_plan],
                                 available_plans=available_plans)


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('account_type', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))


# API status endpoint
@app.route('/api-test')
def api_test():
    """Check the status of the humanizer API"""
    api_status = get_api_status()
    return jsonify(api_status)


# Diagnostic endpoint for debugging
@app.route('/debug')
def debug():
    """Diagnostic endpoint to check users and sessions"""
    # Get API status
    api_status = get_api_status()
    
    # Check the API URL
    humanizer_api_url = os.environ.get('HUMANIZER_API_URL', 'https://web-production-3db6c.up.railway.app')
    
    return jsonify({
        'session': dict(session),
        'api_status': api_status,
        'api_url': humanizer_api_url,
        'api_key_set': bool(os.environ.get('HUMANIZER_API_KEY', '')),
        'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })


# CSS styles
@app.route('/static/style.css')
def serve_css():
    with open('static/style.css', 'r') as file:
        css = file.read()
    return css, 200, {'Content-Type': 'text/css'}


# JavaScript
@app.route('/static/script.js')
def serve_js():
    with open('static/script.js', 'r') as file:
        js = file.read()
    return js, 200, {'Content-Type': 'text/javascript'}


if __name__ == '__main__':
    # Initialize the database
    init_db()
    
    port = int(os.environ.get('PORT', 5000))
    
    # Log startup information
    logger.info(f"Starting {APP_NAME} server on port {port}...")
    logger.info("Available plans:")
    for plan, details in pricing_plans.items():
        logger.info(f"  - {plan}: {details['word_limit']} words per round (KES {details['price']})")
    
    # Check API status at startup
    api_status = get_api_status()
    logger.info(f"\nAPI Status: {api_status.get('status', 'unknown')}")
    
    if api_status.get('status') != 'online':
        logger.error(f"API IS NOT AVAILABLE: {api_status.get('message', 'Unknown error')}")
        logger.error("Please check your API configuration. The application requires a working API.")
    else:
        logger.info("API connection successful!")
    
    # Log API URLs
    humanizer_api_url = os.environ.get('HUMANIZER_API_URL', 'https://web-production-3db6c.up.railway.app')
    logger.info(f"\nHumanizer API URL: {humanizer_api_url}")
    logger.info(f"Debug endpoint available at: http://localhost:{port}/debug")
    
    app.run(host='0.0.0.0', port=port)
