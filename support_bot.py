from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from datetime import datetime
import json
import os

# Create a Blueprint for the support bot
support_bp = Blueprint('support', __name__, template_folder='templates')

# List of FAQs for the support system
FAQS = [
    {
        "id": 1,
        "question": "How does the humanization service work?",
        "answer": "The Andikar AI humanization service converts machine-like text into natural, human-sounding content. Simply paste your text and click 'Humanize'."
    },
    {
        "id": 2,
        "question": "What's the maximum text length I can process?",
        "answer": "You can process text of any length, but larger texts may take longer to process."
    },
    {
        "id": 3,
        "question": "I'm getting an error when I try to humanize text",
        "answer": "First, check your internet connection. Then make sure your text doesn't contain any special characters that might cause issues. If problems persist, try logging out and back in."
    },
    {
        "id": 4,
        "question": "How do I create an account?",
        "answer": "Click the 'Register' button on the homepage, fill in your details, and follow the instructions to create your account."
    },
    {
        "id": 5,
        "question": "I forgot my password",
        "answer": "Click the 'Forgot Password' link on the login page and follow the instructions to reset your password."
    }
]

# Support page route
@support_bp.route('/support')
def support_page():
    """Render the support page"""
    # Check if user is logged in
    username = session.get('user_id')
    is_logged_in = username is not None
    
    return render_template('support.html', 
                          faqs=FAQS, 
                          is_logged_in=is_logged_in, 
                          username=username)

# FAQ API endpoint
@support_bp.route('/api/support/faqs')
def get_faqs():
    """Return all FAQs as JSON"""
    return jsonify(FAQS)

# Support bot message endpoint
@support_bp.route('/api/support/message', methods=['POST'])
def process_message():
    """Process a support message and return a response"""
    if not request.json or 'message' not in request.json:
        return jsonify({"error": "No message provided"}), 400
    
    user_message = request.json['message'].lower()
    
    # Prepare the response
    response = {
        "message": "I'm sorry, I don't have a specific answer for that. Please check our FAQs or contact our support team at support@andikar.ai.",
        "suggestions": []
    }
    
    # Keyword matching
    if any(word in user_message for word in ['hello', 'hi', 'hey', 'greetings']):
        response["message"] = "Hello! How can I help you today with Andikar AI?"
        response["suggestions"] = ["How does humanization work?", "I'm having an error", "Account issues"]
    
    elif any(word in user_message for word in ['humanize', 'humanization', 'how', 'work']):
        response["message"] = "The Andikar AI humanization service converts machine-like text into more natural, human-sounding content. Simply paste your text into the text box on the humanize page and click the 'Humanize' button."
        response["suggestions"] = ["Maximum text length?", "I'm getting an error", "How good is the quality?"]
    
    elif any(word in user_message for word in ['error', 'issue', 'problem', 'not working']):
        response["message"] = "I'm sorry to hear you're experiencing an error. Please try refreshing the page. If the issue persists, check your internet connection. For specific errors, please describe the problem in more detail or contact our support team."
        response["suggestions"] = ["I can't login", "Humanization failed", "Text formatting issue"]
    
    elif any(word in user_message for word in ['account', 'login', 'register', 'password']):
        response["message"] = "For account-related issues: Make sure your login credentials are correct. If you forgot your password, use the 'Forgot Password' link on the login page. For registration issues, ensure all required fields are filled correctly."
        response["suggestions"] = ["I forgot my password", "Can't create account", "Login failed"]
        
    return jsonify(response)

# Support contact form submission
@support_bp.route('/api/support/contact', methods=['POST'])
def submit_contact():
    """Process a support contact form submission"""
    if not request.json:
        return jsonify({"error": "No data provided"}), 400
    
    # Get form data
    data = request.json
    name = data.get('name', 'Anonymous')
    email = data.get('email', 'No email provided')
    message = data.get('message', 'No message provided')
    
    # In a real application, you would save this to a database
    # and/or send an email notification
    
    # For demonstration, we'll just return a success message
    return jsonify({
        "success": True,
        "message": "Thank you for contacting us. We'll respond to your inquiry soon."
    })

# Function to register the blueprint with the Flask app
def register_support_bot(app):
    """Register the support bot blueprint with the Flask app"""
    app.register_blueprint(support_bp)
    print("Support bot routes registered")