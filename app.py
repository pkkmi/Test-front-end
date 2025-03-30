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

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(32)))

# Login decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function

# Initialize backend components
from backend.api_routes import init_app as init_api
from backend.auth import authenticate_user, register_user, token_required
from backend.users import get_user_info, update_user_account_type, check_feature_access
from backend.api_service import humanize_text, get_api_status

# Initialize API routes
init_api(app)

# Routes
@app.route('/')
def index():
    return render_template_string(html_templates['index.html'])


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Use new auth module to authenticate user
        user = authenticate_user(username, password)
        
        if user:
            session['user_id'] = user['user_id']
            session['account_type'] = user['account_type']
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials', 'error')

    return render_template_string(html_templates['login.html'])


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        plan_type = request.form['plan_type']
        
        # Get email and phone from the form
        email = request.form['email']
        phone = request.form.get('phone', None)  # Phone is optional

        # Register user using backend function
        user = register_user(username, password, email, plan_type)
        
        if user:
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Registration failed. Username may already exist.', 'error')

    return render_template_string(html_templates['register.html'], pricing_plans=pricing_plans)


@app.route('/dashboard')
@login_required
def dashboard():
    # Get detailed user account info using backend function
    user_data = get_user_info(session['user_id'])
    
    if not user_data:
        flash('User data not found', 'error')
        return redirect(url_for('logout'))
        
    return render_template_string(html_templates['dashboard.html'], user=user_data,
                                  plan=pricing_plans[user_data['account_type']])


@app.route('/humanize', methods=['GET', 'POST'])
@login_required
def humanize():
    message = ""
    humanized_text = ""
    original_text = ""
    
    # Get user data
    user_data = get_user_info(session['user_id'])
    if not user_data:
        flash('User data not found', 'error')
        return redirect(url_for('dashboard'))
    
    # Check if user has enough API calls remaining
    rate_limit = user_data.get('limits', {})
    rate_limit_reached = rate_limit.get('remaining', 0) <= 0

    if request.method == 'POST':
        original_text = request.form['original_text']
        
        # Only process if rate limit not reached
        if not rate_limit_reached:
            try:
                # Use backend API service to humanize text
                result = humanize_text(
                    original_text, 
                    session['user_id'], 
                    session.get('account_type', 'free')
                )
                
                humanized_text = result.get('humanized_text', '')
                message = "Text successfully humanized!"
                
            except Exception as e:
                message = f"Error: {str(e)}"
                flash(message, 'error')
        else:
            message = "You've reached your usage limit. Please upgrade your plan for more API calls."
            flash(message, 'warning')

    return render_template_string(html_templates['humanize.html'],
                                  message=message,
                                  humanized_text=humanized_text,
                                  original_text=original_text,
                                  rate_limit_reached=rate_limit_reached,
                                  word_limit=pricing_plans[user_data['account_type']]['word_limit'])


@app.route('/detect', methods=['GET', 'POST'])
@login_required
def detect():
    result = None
    message = ""
    
    # Get user data
    user_data = get_user_info(session['user_id'])
    if not user_data:
        flash('User data not found', 'error')
        return redirect(url_for('dashboard'))
    
    # Check if user has the required feature
    feature_access = check_feature_access(session['user_id'], 'ai_detection')
    
    if request.method == 'POST':
        text = request.form['text']

        # Check if user has access to the feature
        if feature_access:
            # This is just a placeholder until actual AI detection is implemented
            # In the real implementation, this would call an AI detection service
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
    # Get detailed user account info
    user_data = get_user_info(session['user_id'])
    
    if not user_data:
        flash('User data not found', 'error')
        return redirect(url_for('logout'))
    
    # Get user transactions (this would be from a database in a real app)
    user_transactions = [t for t in transactions_db if t.get('user_id') == session['user_id']]
    
    return render_template_string(html_templates['account.html'], 
                                 user=user_data, 
                                 plan=pricing_plans[user_data['account_type']],
                                 transactions=user_transactions)


@app.route('/api-integration', methods=['GET', 'POST'])
@login_required
def api_integration():
    # Check if user has API access feature
    api_access = check_feature_access(session['user_id'], 'api_access')
    
    if not api_access:
        flash('API access not available with your current plan', 'warning')
        return redirect(url_for('account'))
    
    # Handle API key updates (if implemented)
    if request.method == 'POST':
        # This would be handled by a backend function in a real implementation
        flash('API keys updated successfully!', 'success')
        return redirect(url_for('api_integration'))

    return render_template_string(html_templates['api_integration.html'],
                                 api_keys={'api_token': '********'})


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
    if request.method == 'POST':
        phone_number = request.form['phone_number']
        
        # Get plan price
        user_data = get_user_info(session['user_id'])
        plan = user_data['account_type']
        amount = pricing_plans[plan]['price']

        # Process payment (this would call a payment gateway in a real app)
        # For demo purposes, just simulate a successful payment
        transaction_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        
        # Add transaction to database
        transactions_db.append({
            'transaction_id': transaction_id,
            'user_id': session['user_id'],
            'phone_number': phone_number,
            'amount': amount,
            'date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'Completed'
        })
        
        flash('Payment processed successfully!', 'success')
        return redirect(url_for('account'))

    # Get user data
    user_data = get_user_info(session['user_id'])
    
    return render_template_string(html_templates['payment.html'],
                                 plan=pricing_plans[user_data['account_type']])


@app.route('/upgrade', methods=['GET', 'POST'])
@login_required
def upgrade():
    if request.method == 'POST':
        new_plan = request.form['new_plan']
        
        # Update user plan using backend function
        success = update_user_account_type(session['user_id'], new_plan)
        
        if success:
            flash(f'Plan upgraded to {new_plan} successfully!', 'success')
            
            # Redirect to payment if needed
            if new_plan != 'free':
                return redirect(url_for('payment'))
            return redirect(url_for('account'))
        else:
            flash('Failed to upgrade plan', 'error')
            return redirect(url_for('upgrade'))

    # Get user data
    user_data = get_user_info(session['user_id'])
    current_plan = user_data['account_type']
    
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


# Diagnostic endpoint for the API connection
@app.route('/api-test')
def api_test():
    """Diagnostic endpoint to check the humanizer API connection"""
    # Get status of the API
    api_status = get_api_status()
    
    return jsonify(api_status)


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
    # Add a sample user for quick testing (this is just for development)
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
    
    # Log API URLs
    humanizer_api_url = os.environ.get('HUMANIZER_API_URL', 'https://web-production-3db6c.up.railway.app')
    admin_api_url = os.environ.get("ADMIN_API_URL", "https://railway-test-api-production.up.railway.app")
    logger.info(f"\nHumanizer API URL: {humanizer_api_url}")
    logger.info(f"Admin API URL: {admin_api_url}")
    logger.info(f"API routes available at: http://localhost:{port}/api/v1/")
    
    app.run(host='0.0.0.0', port=port)
