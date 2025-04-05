# Andikar AI - Text Humanizer

Andikar AI is a web application that transforms AI-generated content into natural human text. 

## Features

- Text humanization: Convert AI-generated text into more natural, human-like writing
- AI detection: Analyze text to determine the likelihood it was written by AI
- User dashboard: Track usage and access personal account settings
- Google authentication: Securely log in with Google accounts

## Recent Updates

- **Authentication Flow**: Users must now log in to access the humanize feature
- **Navigation Priority**: Humanize page is now the primary landing page after login
- **Google OAuth**: Authentication system now uses Google accounts

## Environment Setup

1. Copy `.env.example` to `.env` in the root directory
2. Generate a secure random key for `SECRET_KEY`:
   ```bash
   python -c "import secrets; print(secrets.token_hex(24))"
   ```
3. Set up your MongoDB connection string in `MONGODB_URI`
4. Set up Google OAuth credentials (instructions below)

## Google OAuth Setup

### Create Google Cloud Project
1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Navigate to "APIs & Services" > "OAuth consent screen"
4. Configure the consent screen (External user type recommended)
5. Add scopes: `email`, `profile`, `openid`
6. Add test users if needed

### Configure OAuth Credentials
1. Go to "APIs & Services" > "Credentials"
2. Create OAuth 2.0 Client ID (Web application)
3. Add authorized JavaScript origins:
   - `http://localhost:5000` (for development)
   - Your production domain (e.g., `https://yourdomain.com`)
4. Add authorized redirect URIs:
   - `http://localhost:5000/callback` (for development)
   - Your production callback URL (e.g., `https://yourdomain.com/callback`)
5. Note your Client ID and Client Secret
6. Update your `.env` file with these credentials

## Running Locally

```bash
# Clone the repository
git clone https://github.com/pkkmi/Test-front-end.git
cd Test-front-end

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
# Copy .env.example to .env and update values

# Run the application
flask run
```

Visit `http://localhost:5000` in your web browser.

## Deployment

### Heroku Deployment
```bash
# Install Heroku CLI if not already installed
# Login to Heroku
heroku login

# Create a new Heroku app
heroku create andikar-ai

# Set environment variables
heroku config:set FLASK_APP=app.py
heroku config:set FLASK_ENV=production
heroku config:set SECRET_KEY=your_generated_secret_key
heroku config:set MONGODB_URI=your_mongodb_connection_string
heroku config:set DB_NAME=andikar_ai
heroku config:set GOOGLE_CLIENT_ID=your_google_client_id
heroku config:set GOOGLE_CLIENT_SECRET=your_google_client_secret

# Deploy to Heroku
git push heroku main

# Open the app
heroku open
```

### AWS Deployment
1. Set up an EC2 instance with Python installed
2. Clone the repository to the server
3. Set up a virtual environment and install dependencies
4. Configure environment variables
5. Set up Nginx as a reverse proxy
6. Use Gunicorn as a WSGI server
7. Configure systemd to manage the application process

## Troubleshooting

If you encounter any issues with the Google OAuth integration, check:
1. The client ID and secret are correctly set in your environment variables
2. The authorized redirect URIs match your application's callback URL
3. The OAuth consent screen is properly configured
4. Your Google Cloud project APIs are enabled

If needed, you can roll back to the previous authentication system by restoring from backup files.
