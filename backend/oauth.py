"""
Google OAuth Configuration and Helper Functions
"""

import os
import json
import logging
from flask import url_for, session, redirect, request
from datetime import datetime
from oauthlib.oauth2 import WebApplicationClient
import requests

# Configuration for Google OAuth
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "YOUR_GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "YOUR_GOOGLE_CLIENT_SECRET")
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OAuth client setup
client = WebApplicationClient(GOOGLE_CLIENT_ID)

def get_google_provider_cfg():
    """Get Google's OAuth 2.0 endpoint configurations"""
    try:
        return requests.get(GOOGLE_DISCOVERY_URL).json()
    except Exception as e:
        logger.error(f"Error fetching Google provider config: {str(e)}")
        return None

def get_google_auth_url(redirect_uri=None):
    """Generate a Google authentication URL"""
    try:
        # Find out what URL to hit for Google login
        google_provider_cfg = get_google_provider_cfg()
        if not google_provider_cfg:
            return None

        # Use library to construct the request for Google login
        # and provide the redirect location
        authorization_endpoint = google_provider_cfg["authorization_endpoint"]
        
        if not redirect_uri:
            redirect_uri = url_for('callback', _external=True)
            
        # Generate URL for request to Google's OAuth 2.0 server
        return client.prepare_request_uri(
            authorization_endpoint,
            redirect_uri=redirect_uri,
            scope=["openid", "email", "profile"],
        )
    except Exception as e:
        logger.error(f"Error generating Google auth URL: {str(e)}")
        return None

def get_google_tokens(code, redirect_uri=None):
    """Exchange authorization code for tokens"""
    try:
        # Find out what URL to hit to get tokens from the provider
        google_provider_cfg = get_google_provider_cfg()
        if not google_provider_cfg:
            return None

        token_endpoint = google_provider_cfg["token_endpoint"]
        
        if not redirect_uri:
            redirect_uri = url_for('callback', _external=True)
            
        # Prepare and send request to get tokens
        token_url, headers, body = client.prepare_token_request(
            token_endpoint,
            authorization_response=request.url,
            redirect_url=redirect_uri,
            code=code,
        )
        
        token_response = requests.post(
            token_url,
            headers=headers,
            data=body,
            auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
        )

        # Parse the tokens
        return client.parse_request_body_response(json.dumps(token_response.json()))
    except Exception as e:
        logger.error(f"Error getting Google tokens: {str(e)}")
        return None

def get_google_user_info(tokens):
    """Get user info from Google API"""
    try:
        # Find out what URL to hit to get the user's profile information
        google_provider_cfg = get_google_provider_cfg()
        if not google_provider_cfg:
            return None
            
        userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
        
        # Make a request to the userinfo endpoint
        uri, headers, body = client.add_token(userinfo_endpoint)
        userinfo_response = requests.get(uri, headers=headers, data=body)
        
        # Parse the user info
        if userinfo_response.json().get("email_verified"):
            # The user's email has been verified by Google
            # Extract user information
            return {
                "sub": userinfo_response.json()["sub"],  # Unique Google user ID
                "email": userinfo_response.json()["email"],
                "name": userinfo_response.json().get("name", ""),
                "picture": userinfo_response.json().get("picture", "")
            }
        else:
            # The user's email hasn't been verified by Google
            return None
    except Exception as e:
        logger.error(f"Error getting Google user info: {str(e)}")
        return None

def get_or_create_user(db, user_info):
    """Get or create a user based on Google user info"""
    try:
        users_collection = db['users']
        
        # Check if user already exists
        user = users_collection.find_one({"google_id": user_info["sub"]})
        
        if user:
            # User exists, return it
            return user
            
        # Check if email already exists
        email_user = users_collection.find_one({"email": user_info["email"]})
        if email_user:
            # Link Google ID to existing user
            result = users_collection.update_one(
                {"_id": email_user["_id"]},
                {"$set": {"google_id": user_info["sub"]}}
            )
            return users_collection.find_one({"_id": email_user["_id"]})
        
        # Create new user
        new_user = {
            "username": user_info["email"].split("@")[0],  # Use part before @ as username
            "email": user_info["email"],
            "google_id": user_info["sub"],
            "name": user_info["name"],
            "profile_picture": user_info["picture"],
            "created_at": datetime.now(),
            "usage": {
                "requests": 0,
                "total_words": 0,
                "monthly_words": 0,
                "last_request": None
            }
        }
        
        result = users_collection.insert_one(new_user)
        return users_collection.find_one({"_id": result.inserted_id})
    except Exception as e:
        logger.error(f"Error creating/getting user: {str(e)}")
        return None
