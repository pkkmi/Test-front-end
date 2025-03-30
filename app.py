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

# Import backend modules
from backend.api_routes import api_bp
from backend.auth import login_required_api
from backend.users import (
    register_new_user, 
    get_user_account_info, 
    process_payment, 
    update_user_plan,
    update_user_usage,
    update_api_keys
)
from backend.api_service import humanize_text_api, detect_ai_content_api

# Register API blueprint
app.register_blueprint(api_bp)

# Login decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
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

        # Check if user exists (using backend function)
        from backend.auth import validate_user_credentials
        if validate_user_credentials(username, password):
            session['user_id'] = username
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
        success, message = register_new_user(
            username=username,
            password=password,
            email=email,
            plan_type=plan_type,
            phone=phone
        )
        
        if success:
            flash(message, 'success' if 'successful' in message else 'warning')
            return redirect(url_for('login'))
        else:
            flash(message, 'error')

    return render_template_string(html_templates['register.html'], pricing_plans=pricing_plans)


@app.route('/dashboard')
@login_required
def dashboard():
    # Get detailed user account info using backend function
    user_data = get_user_account_info(session['user_id'])
    
    if not user_data:
        flash('User data not found', 'error')
        return redirect(url_for('logout'))
        
    return render_template_string(html_templates['dashboard.html'], user=user_data,
                                  plan=pricing_plans[user_data['plan']])


@app.route('/humanize', methods=['GET', 'POST'])
@login_required
def humanize():
    message = ""
    humanized_text = ""
    
    # Get user data
    user_data = get_user_account_info(session['user_id'])
    if not user_data:
        flash('User data not found', 'error')
        return redirect(url_for('dashboard'))
        
    payment_required = user_data['payment_status'] == 'Pending' and user_data['plan'] != 'Free'

    if request.method == 'POST':
        original_text = request.form['original_text']
        user_type = user_data['plan']

        # Only process if payment not required or on Free plan
        if not payment_required:
            # Use backend API service to humanize text
            humanized_text, message, status_code = humanize_text_api(original_text, user_type)
            
            if status_code == 200:
                # Update word usage
                update_user_usage(session['user_id'], len(original_text.split()))
            else:
                flash(f"Error: {message}", 'error')
        else:
            message = "Payment required to access this feature. Please upgrade your plan."

    return render_template_string(html_templates['humanize.html'],
                                  message=message,
                                  humanized_text=humanized_text,
                                  payment_required=payment_required,
                                  word_limit=pricing_plans[user_data['plan']]['word_limit'])


@app.route('/detect', methods=['GET', 'POST'])
@login_required
def detect():
    result = None
    message = ""
    
    # Get user data
    user_data = get_user_account_info(session['user_id'])
    if not user_data:
        flash('User data not found', 'error')
        return redirect(url_for('dashboard'))
        
    payment_required = user_data['payment_status'] == 'Pending' and user_data['plan'] != 'Free'

    if request.method == 'POST':
        text = request.form['text']

        # Check payment status for non-free users
        if not payment_required:
            # Use backend API service to detect AI content
            api_keys = users_db[session['user_id']].get('api_keys', {})
            result, message, status_code = detect_ai_content_api(text, api_keys)
            
            if status_code != 200:
                flash(f"Error: {message}", 'error')
        else:
            message = "Payment required to access this feature. Please upgrade your plan."

    return render_template_string(html_templates['detect.html'],
                                  result=result,
                                  message=message,
                                  payment_required=payment_required)


@app.route('/account')
@login_required
def account():
    # Get detailed user account info
    user_data = get_user_account_info(session['user_id'])
    
    if not user_data:
        flash('User data not found', 'error')
        return redirect(url_for('logout'))
        
    user_transactions = [t for t in transactions_db if t['user_id'] == session['user_id']]
    
    return render_template_string(html_templates['account.html'], 
                                  user=user_data, 
                                  plan=pricing_plans[user_data['plan']],
                                  transactions=user_transactions)


@app.route('/api-integration', methods=['GET', 'POST'])
@login_required
def api_integration():
    if request.method == 'POST':
        gpt_zero_key = request.form.get('gpt_zero_key', '')
        originality_key = request.form.get('originality_key', '')

        # Update API keys using backend function
        if update_api_keys(session['user_id'], gpt_zero_key, originality_key):
            flash('API keys updated successfully!', 'success')
        else:
            flash('Failed to update API keys', 'error')
            
        return redirect(url_for('api_integration'))

    return render_template_string(html_templates['api_integration.html'],
                                  api_keys=users_db[session['user_id']]['api_keys'])


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
@login_required
def pricing():
    return render_template_string(html_templates['pricing.html'], pricing_plans=pricing_plans)


@app.route('/payment', methods=['GET', 'POST'])
@login_required
def payment():
    if request.method == 'POST':
        phone_number = request.form['phone_number']
        
        # Get plan price
        plan = users_db[session['user_id']]['plan']
        amount = pricing_plans[plan]['price']

        # Process payment using backend function
        success, message, transaction_id = process_payment(
            username=session['user_id'],
            phone_number=phone_number,
            amount=amount
        )
        
        if success:
            flash(message, 'success')
            return redirect(url_for('account'))
        else:
            flash(message, 'error')

    # Get user data
    user_data = get_user_account_info(session['user_id'])
    
    return render_template_string(html_templates['payment.html'],
                                  plan=pricing_plans[user_data['plan']])


@app.route('/upgrade', methods=['GET', 'POST'])
@login_required
def upgrade():
    if request.method == 'POST':
        new_plan = request.form['new_plan']
        
        # Update user plan using backend function
        success, message = update_user_plan(session['user_id'], new_plan)
        
        if success:
            flash(message, 'success')
            
            # Redirect to payment if needed
            if 'payment required' in message.lower():
                return redirect(url_for('payment'))
            return redirect(url_for('account'))
        else:
            flash(message, 'error')
            return redirect(url_for('upgrade'))

    # Get user data
    user_data = get_user_account_info(session['user_id'])
    current_plan = user_data['plan']
    
    available_plans = {k: v for k, v in pricing_plans.items() if k != current_plan}
    return render_template_string(html_templates['upgrade.html'], 
                                  current_plan=pricing_plans[current_plan],
                                  available_plans=available_plans)


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))


# Diagnostic endpoint for the API connection
@app.route('/api-test')
def api_test():
    """Diagnostic endpoint to check the humanizer API connection"""
    from backend.api_service import get_api_status
    
    # Get status of all APIs
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
    
    # Log API URLs
    humanizer_api_url = os.environ.get('HUMANIZER_API_URL', 'https://web-production-3db6c.up.railway.app')
    admin_api_url = os.environ.get("ADMIN_API_URL", "https://railway-test-api-production.up.railway.app")
    logger.info(f"\nHumanizer API URL: {humanizer_api_url}")
    logger.info(f"Admin API URL: {admin_api_url}")
    logger.info(f"API routes available at: http://localhost:{port}/api/v1/")
    
    app.run(host='0.0.0.0', port=port)
