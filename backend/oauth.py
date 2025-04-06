"""
Google OAuth Configuration and Helper Functions
"""

import os
import json
import logging
import secrets
import time
from flask import url_for, session, redirect, request
from datetime import datetime
from oauthlib.oauth2 import WebApplicationClient
import requests

# Configuration for Google OAuth
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "934412857118-i13t5ma9afueo40tmohosprsjf4555f0.apps.googleusercontent.com")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

# Explicitly set the callback URL for Railway deployment
RAILWAY_PRODUCTION_URL = "https://web-production-c1f4.up.railway.app/callback"

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OAuth client setup
client = WebApplicationClient(GOOGLE_CLIENT_ID)

def get_google_provider_cfg():
    """Get Google's OAuth 2.0 endpoint configurations with retry logic"""
    max_retries = 3
    retry_delay = 1  # seconds
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Fetching Google provider config (attempt {attempt+1}/{max_retries})")
            response = requests.get(GOOGLE_DISCOVERY_URL, timeout=10)
            
            if response.status_code == 200:
                logger.info("Successfully fetched Google provider config")
                return response.json()
            else:
                logger.error(f"Failed to get Google provider config: {response.status_code}")
                logger.error(f"Response: {response.text[:200]}")
        except Exception as e:
            logger.error(f"Error fetching Google provider config: {str(e)}")
        
        # Only delay if we're going to retry
        if attempt < max_retries - 1:
            time.sleep(retry_delay)
            retry_delay *= 2  # Exponential backoff
    
    logger.error("All attempts to fetch Google provider config failed")
    return None

def get_google_auth_url(redirect_uri=None):
    """Generate a Google authentication URL"""
    try:
        # Find out what URL to hit for Google login
        google_provider_cfg = get_google_provider_cfg()
        if not google_provider_cfg:
            logger.error("Failed to get Google provider configuration")
            return None

        # Use library to construct the request for Google login
        # and provide the redirect location
        authorization_endpoint = google_provider_cfg["authorization_endpoint"]
        
        # Always use the Railway production URL when deployed
        # This ensures it matches exactly what's in Google Cloud Console
        redirect_uri = RAILWAY_PRODUCTION_URL
        
        # Generate a random state parameter for CSRF protection
        state = secrets.token_urlsafe(16)
        session["oauth_state"] = state
        
        logger.info(f"OAuth redirect URI: {redirect_uri}")
        logger.info(f"OAuth state: {state}")
            
        # Generate URL for request to Google's OAuth 2.0 server
        auth_url = client.prepare_request_uri(
            authorization_endpoint,
            redirect_uri=redirect_uri,
            scope=["openid", "email", "profile"],
            state=state,
            prompt="select_account"  # Force Google to ask user to select account
        )
        
        logger.info(f"Generated auth URL: {auth_url[:50]}...")
        return auth_url
    except Exception as e:
        logger.error(f"Error generating Google auth URL: {str(e)}", exc_info=True)
        return None

def get_google_tokens(code, redirect_uri=None):
    """Exchange authorization code for tokens with retry logic"""
    max_retries = 3
    retry_delay = 1  # seconds
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Exchanging code for tokens (attempt {attempt+1}/{max_retries})")
            
            # Find out what URL to hit to get tokens from the provider
            google_provider_cfg = get_google_provider_cfg()
            if not google_provider_cfg:
                logger.error("Failed to get Google provider config")
                continue

            token_endpoint = google_provider_cfg["token_endpoint"]
            
            # Always use the Railway production URL for tokens
            redirect_uri = RAILWAY_PRODUCTION_URL
                    
            logger.info(f"Token exchange using redirect URI: {redirect_uri}")
            logger.info(f"Request URL: {request.url}")
            
            # Verify state parameter to prevent CSRF
            received_state = request.args.get('state', '')
            stored_state = session.get("oauth_state", '')
            logger.info(f"Received state: {received_state}")
            logger.info(f"Stored state: {stored_state}")
            
            # Check if client secret is set
            if not GOOGLE_CLIENT_SECRET:
                logger.error("GOOGLE_CLIENT_SECRET environment variable is not set")
                logger.info(f"Current env variables: {list(os.environ.keys())}")
                logger.info(f"GOOGLE_CLIENT_ID is set: {bool(GOOGLE_CLIENT_ID)}")
                continue
                
            # Prepare token request
            # Use the full URL for the authorization_response
            full_url = request.url
            if not full_url.startswith('https://'):
                # Railway uses HTTPS, make sure we're using it for the token exchange
                full_url = full_url.replace('http://', 'https://')
                
            logger.info(f"Using full URL for token exchange: {full_url}")
                
            # Prepare and send request to get tokens
            token_url, headers, body = client.prepare_token_request(
                token_endpoint,
                authorization_response=full_url,
                redirect_url=redirect_uri,
                code=code,
            )
            
            logger.info(f"Sending token request to: {token_url}")
            logger.info(f"With headers: {headers}")
            logger.info(f"Body length: {len(body) if body else 0}")
            
            # Log client credentials (redacted)
            client_id_log = GOOGLE_CLIENT_ID[:5] + "..." + GOOGLE_CLIENT_ID[-5:] if GOOGLE_CLIENT_ID else "Not set"
            client_secret_log = GOOGLE_CLIENT_SECRET[:2] + "..." + GOOGLE_CLIENT_SECRET[-2:] if GOOGLE_CLIENT_SECRET else "Not set"
            logger.info(f"Using client ID: {client_id_log}")
            logger.info(f"Using client secret: {client_secret_log}")
            
            # Make the token request with timeout and better error handling
            token_response = requests.post(
                token_url,
                headers=headers,
                data=body,
                auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
                timeout=10
            )

            # Check if token request was successful
            if token_response.status_code != 200:
                logger.error(f"Token request failed with status {token_response.status_code}")
                logger.error(f"Response body: {token_response.text}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                continue

            # Parse the tokens
            tokens = client.parse_request_body_response(json.dumps(token_response.json()))
            logger.info(f"Token exchange successful: {list(tokens.keys())}")
            return tokens
            
        except Exception as e:
            logger.error(f"Error getting Google tokens (attempt {attempt+1}/{max_retries}): {str(e)}", exc_info=True)
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
    
    logger.error("All attempts to get Google tokens failed")
    return None

def get_google_user_info(tokens):
    """Get user info from Google API with retry logic"""
    max_retries = 3
    retry_delay = 1  # seconds
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Getting user info from Google (attempt {attempt+1}/{max_retries})")
            
            # Find out what URL to hit to get the user's profile information
            google_provider_cfg = get_google_provider_cfg()
            if not google_provider_cfg:
                logger.error("Failed to get Google provider config")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                continue
                
            userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
            
            # Make a request to the userinfo endpoint
            uri, headers, body = client.add_token(userinfo_endpoint)
            userinfo_response = requests.get(uri, headers=headers, data=body, timeout=10)
            
            # Check if user info request was successful
            if userinfo_response.status_code != 200:
                logger.error(f"User info request failed with status {userinfo_response.status_code}")
                logger.error(f"Response body: {userinfo_response.text}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                continue
                
            # Parse the user info
            userinfo = userinfo_response.json()
            
            # Log user info (redacted)
            logger.info(f"Received user info: {list(userinfo.keys())}")
            if 'email' in userinfo:
                email_parts = userinfo['email'].split('@')
                if len(email_parts) == 2:
                    redacted_email = f"{email_parts[0][:3]}...@{email_parts[1]}"
                    logger.info(f"User email: {redacted_email}")
            
            if userinfo.get("email_verified"):
                # The user's email has been verified by Google
                # Extract user information
                user_data = {
                    "sub": userinfo["sub"],  # Unique Google user ID
                    "email": userinfo["email"],
                    "name": userinfo.get("name", ""),
                    "picture": userinfo.get("picture", "")
                }
                logger.info(f"User info retrieved successfully for: {userinfo.get('email')}")
                return user_data
            else:
                # The user's email hasn't been verified by Google
                logger.error("User email not verified by Google")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                continue
                
        except Exception as e:
            logger.error(f"Error getting Google user info (attempt {attempt+1}/{max_retries}): {str(e)}", exc_info=True)
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2
    
    logger.error("All attempts to get Google user info failed")
    return None

def get_or_create_user(db, user_info):
    """Get or create a user based on Google user info with retry logic"""
    max_retries = 3
    retry_delay = 1  # seconds
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Getting or creating user (attempt {attempt+1}/{max_retries})")
            
            if not user_info:
                logger.error("No user info provided")
                return None
                
            if not isinstance(db, object):
                logger.error(f"Invalid database object: {type(db)}")
                return None
                
            if not hasattr(db, '__getitem__'):
                logger.error(f"Database object doesn't support __getitem__: {type(db)}")
                return None
            
            users_collection = db['users']
            logger.info(f"Accessing users collection: {users_collection}")
            
            # Log user info for debugging
            google_id = user_info.get("sub")
            email = user_info.get("email")
            logger.info(f"Looking up user with Google ID: {google_id}")
            logger.info(f"User email: {email}")
            
            # Check if user already exists by Google ID
            user = users_collection.find_one({"google_id": google_id})
            
            if user:
                # User exists, return it
                logger.info(f"Existing user found by Google ID: {user.get('username')}")
                return user
                
            # Check if email already exists
            logger.info(f"No user found by Google ID, checking by email: {email}")
            email_user = users_collection.find_one({"email": email})
            
            if email_user:
                # Link Google ID to existing user
                logger.info(f"Linking Google ID to existing user: {email_user.get('username')}")
                result = users_collection.update_one(
                    {"_id": email_user["_id"]},
                    {"$set": {"google_id": google_id}}
                )
                return users_collection.find_one({"_id": email_user["_id"]})
            
            # Create new user
            logger.info(f"Creating new user with email: {email}")
            username = email.split("@")[0]  # Use part before @ as username
            
            new_user = {
                "username": username,
                "email": email,
                "google_id": google_id,
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
            
            logger.info(f"Inserting new user: {username}")
            result = users_collection.insert_one(new_user)
            
            # Verify the user was created
            created_user = users_collection.find_one({"username": username})
            if not created_user:
                logger.error(f"Failed to find newly created user: {username}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                    
            logger.info(f"User created successfully: {username}")
            return created_user
            
        except Exception as e:
            logger.error(f"Error creating/getting user (attempt {attempt+1}/{max_retries}): {str(e)}", exc_info=True)
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2
    
    logger.error("All attempts to get or create user failed")
    return None
