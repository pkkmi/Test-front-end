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
from models import users_db, transactions_db
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

# Import backend modules for API communication
from backend.api_service import humanize_text, get_api_status, HumanizerAPIError

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
        
        # Handle demo account directly
        if username == 'demo' and password == 'demo':
            session['user_id'] = 'demo'
            session['account_type'] = 'Basic'
            flash('Demo login successful!', 'success')
            return redirect(url_for('dashboard'))
            
        # Handle other users
        if username in users_db:
            stored_password = users_db[username].get('password')
            
            # Simple plain text password check (for demo purposes only)
            if stored_password == password:
                session['user_id'] = username
                session['account_type'] = users_db[username].get('plan', 'Free')
                flash('Login successful!', 'success')
                return redirect(url_for('dashboard'))
        
        # Failed login
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
        
        # Check if username already exists
        if username in users_db:
            flash('Username already exists. Please choose another.', 'error')
            return render_template_string(html_templates['register.html'], pricing_plans=pricing_plans)
        
        # Create new user
        users_db[username] = {
            'password': password,  # For a real app, use hashing
            'plan': plan_type,
            'joined_date': datetime.datetime.now().strftime('%Y-%m-%d'),
            'words_used': 0,
            'payment_status': 'Pending' if plan_type != 'Free' else 'N/A',
            'api_keys': {
                'gpt_zero': '',
                'originality': ''
            },
            'email': email
        }
        
        # Log created user
        logger.info(f"New user registered: {username}")
        debug_users()  # Print all users for debugging
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template_string(html_templates['register.html'], pricing_plans=pricing_plans)


@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session.get('user_id')
    
    # Check if user exists
    if user_id not in users_db:
        flash('User account not found. Please log in again.', 'error')
        return redirect(url_for('logout'))
    
    # Get user data
    user_data = users_db[user_id]
    
    # Format user data for template
    user_info = {
        'username': user_id,
        'email': user_data.get('email', f"{user_id}@example.com"),
        'plan': user_data.get('plan', 'Free'),
        'joined_date': user_data.get('joined_date', 'Unknown'),
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
    api_source = "External API"
    
    user_id = session.get('user_id')
    account_type = session.get('account_type', 'Free')
    
    # Check if user exists
    if user_id not in users_db:
        flash('User account not found. Please log in again.', 'error')
        return redirect(url_for('logout'))
    
    # Get user data
    user_data = users_db[user_id]
    plan_type = user_data.get('plan', 'Free')
    
    # Get word limit from plan
    word_limit = pricing_plans[plan_type]['word_limit']
    words_used = user_data.get('words_used', 0)
    words_remaining = max(0, word_limit - words_used)
    
    if request.method == 'POST':
        original_text = request.form['original_text']
        
        # Check if user has enough words remaining
        if words_remaining > 0:
            try:
                # Use the backend API service to humanize text
                logger.info(f"Sending text to humanizer API for user: {user_id}")
                start_time = datetime.datetime.now()
                
                # Call the API through our backend service
                result = humanize_text(original_text, user_id, account_type)
                
                # Extract the humanized text
                humanized_text = result.get('humanized_text', '')
                api_response_time = result.get('metrics', {}).get('response_time', None)
                
                if 'usage' in result:
                    words_remaining = result['usage'].get('remaining', words_remaining - 1)
                
                # Set the API source
                if api_response_time is None:
                    api_source = "Fallback (Local Processing)"
                
                # Update words used (this is also done in the API service)
                input_word_count = len(original_text.split())
                if 'words_used' not in users_db[user_id]:
                    users_db[user_id]['words_used'] = 0
                users_db[user_id]['words_used'] += input_word_count
                
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
                                 api_response_time=api_response_time,
                                 api_source=api_source)


@app.route('/detect', methods=['GET', 'POST'])
@login_required
def detect():
    result = None
    message = ""
    
    user_id = session.get('user_id')
    
    # Check if user exists
    if user_id not in users_db:
        flash('User account not found. Please log in again.', 'error')
        return redirect(url_for('logout'))
    
    # Get user data
    user_data = users_db[user_id]
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
    
    # Check if user exists
    if user_id not in users_db:
        flash('User account not found. Please log in again.', 'error')
        return redirect(url_for('logout'))
    
    # Get user data
    user_data = users_db[user_id]
    
    # Format user data for template
    user_info = {
        'username': user_id,
        'email': user_data.get('email', f"{user_id}@example.com"),
        'plan': user_data.get('plan', 'Free'),
        'joined_date': user_data.get('joined_date', 'Unknown'),
        'words_used': user_data.get('words_used', 0),
        'payment_status': user_data.get('payment_status', 'Pending')
    }
    
    # Get user transactions
    user_transactions = [t for t in transactions_db if t.get('user_id') == user_id]
    
    return render_template_string(html_templates['account.html'], 
                                 user=user_info,
                                 plan=pricing_plans[user_info['plan']],
                                 transactions=user_transactions)


@app.route('/api-integration', methods=['GET', 'POST'])
@login_required
def api_integration():
    user_id = session.get('user_id')
    
    # Check if user exists
    if user_id not in users_db:
        flash('User account not found. Please log in again.', 'error')
        return redirect(url_for('logout'))
    
    # Get user data
    user_data = users_db[user_id]
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
        
        # Update API keys
        if 'api_keys' not in users_db[user_id]:
            users_db[user_id]['api_keys'] = {}
        
        users_db[user_id]['api_keys']['gpt_zero'] = gpt_zero_key
        users_db[user_id]['api_keys']['originality'] = originality_key
        
        flash('API keys updated successfully!', 'success')
        return redirect(url_for('api_integration'))

    return render_template_string(html_templates['api_integration.html'],
                                 api_keys=users_db[user_id].get('api_keys', {}))


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
    
    # Check if user exists
    if user_id not in users_db:
        flash('User account not found. Please log in again.', 'error')
        return redirect(url_for('logout'))
    
    # Get user data
    user_data = users_db[user_id]
    plan_type = user_data.get('plan', 'Free')
    
    if request.method == 'POST':
        phone_number = request.form['phone_number']
        
        # Get plan price
        amount = pricing_plans[plan_type]['price']

        # Simulate successful payment
        transaction_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        
        # Add transaction to database
        transactions_db.append({
            'transaction_id': transaction_id,
            'user_id': user_id,
            'phone_number': phone_number,
            'amount': amount,
            'date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'Completed'
        })
        
        # Update payment status
        users_db[user_id]['payment_status'] = 'Paid'
        
        flash('Payment processed successfully!', 'success')
        return redirect(url_for('account'))

    return render_template_string(html_templates['payment.html'],
                                 plan=pricing_plans[plan_type])


@app.route('/upgrade', methods=['GET', 'POST'])
@login_required
def upgrade():
    user_id = session.get('user_id')
    
    # Check if user exists
    if user_id not in users_db:
        flash('User account not found. Please log in again.', 'error')
        return redirect(url_for('logout'))
    
    # Get user data
    user_data = users_db[user_id]
    current_plan = user_data.get('plan', 'Free')
    
    if request.method == 'POST':
        new_plan = request.form['new_plan']
        
        # Update user plan
        if new_plan in pricing_plans:
            users_db[user_id]['plan'] = new_plan
            
            # Update payment status
            if new_plan != 'Free':
                users_db[user_id]['payment_status'] = 'Pending'
            else:
                users_db[user_id]['payment_status'] = 'N/A'
            
            flash(f'Plan upgraded to {new_plan} successfully!', 'success')
            
            # Redirect to payment if needed
            if new_plan != 'Free':
                return redirect(url_for('payment'))
            return redirect(url_for('account'))
        else:
            flash('Invalid plan selected', 'error')
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
    debug_users()  # Call debug function to print all users
    
    # Get API status
    api_status = get_api_status()
    
    return jsonify({
        'active_users': len(users_db),
        'session': dict(session),
        'api_status': api_status,
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
    # Add a sample user for quick testing
    users_db['demo'] = {
        'password': 'demo',
        'plan': 'Basic',
        'joined_date': datetime.datetime.now().strftime('%Y-%m-%d'),
        'words_used': 125,
        'payment_status': 'Paid',
        'api_keys': {
            'gpt_zero': '',
            'originality': ''
        }
    }

    # Create a sample transaction
    transactions_db.append({
        'transaction_id': 'TXND3M0123456',
        'user_id': 'demo',
        'phone_number': '254712345678',
        'amount': pricing_plans['Basic']['price'],
        'date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'status': 'Completed'
    })

    port = int(os.environ.get('PORT', 5000))
    
    # Log startup information
    logger.info(f"Starting {APP_NAME} server on port {port}...")
    logger.info("Available plans:")
    for plan, details in pricing_plans.items():
        logger.info(f"  - {plan}: {details['word_limit']} words per round (KES {details['price']})")
    logger.info("\nDemo account:")
    logger.info("  Username: demo")
    logger.info("  Password: demo")
    
    # Print all users for debugging at startup
    debug_users()
    
    # Check API status at startup
    api_status = get_api_status()
    logger.info(f"\nAPI Status: {api_status.get('status', 'unknown')}")
    if api_status.get('status') != 'online':
        logger.warning(f"API is not fully operational: {api_status.get('message', 'Unknown error')}")
        logger.warning("Using fallback mode for text humanization")
    
    # Log API URLs
    humanizer_api_url = os.environ.get('HUMANIZER_API_URL', 'https://web-production-3db6c.up.railway.app')
    admin_api_url = os.environ.get("ADMIN_API_URL", "https://railway-test-api-production.up.railway.app")
    logger.info(f"\nHumanizer API URL: {humanizer_api_url}")
    logger.info(f"Admin API URL: {admin_api_url}")
    logger.info(f"Debug endpoint available at: http://localhost:{port}/debug")
    
    app.run(host='0.0.0.0', port=port)
