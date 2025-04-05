# Andikar AI - Frontend

This repository contains the frontend web application for Andikar AI, a tool for humanizing AI-generated text.

## Google OAuth Setup

This application uses Google OAuth for authentication. Follow these steps to set it up:

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select an existing one)
3. Navigate to "APIs & Services" > "Credentials"
4. Click "Create Credentials" > "OAuth client ID"
5. Select "Web application" as the application type
6. Add a name for your OAuth client
7. Add the following Authorized JavaScript origins:
   - `http://localhost:5000` (for local development)
   - Your production domain (e.g., `https://andikar.ai`)
8. Add the following Authorized redirect URIs:
   - `http://localhost:5000/callback` (for local development)
   - `https://your-domain.com/callback` (for production)
9. Click "Create"
10. Note your Client ID and Client Secret

## Environment Variables

Create a `.env` file in the root directory and add the following environment variables:

```
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=your-secret-key
MONGODB_URI=your-mongodb-uri
DB_NAME=andikar_ai
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

## Installation and Setup

1. Clone this repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Run the application: `flask run`

## Rollback Instructions

If you need to roll back to the original authentication system:

1. Replace the content of `app.py` with the code in `backup/auth_backup.py`
2. Restore the original login.html template
3. Remove the Google OAuth related files and dependencies

## Features

- Google OAuth authentication
- Text humanization
- AI content detection
- User dashboard
- Usage statistics
