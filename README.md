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

Create a `.env` file in the root directory by copying the `.env.example` file and adding your secrets:

```
cp .env.example .env
```

Then edit the `.env` file with your actual values:

```
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=your-secret-key
MONGODB_URI=your-mongodb-uri
DB_NAME=andikar_ai
GOOGLE_CLIENT_ID=934412857118-i13t5ma9afueo40tmohosprsjf4555f0.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

## Installation and Setup

1. Clone this repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Create your `.env` file as described above
6. Run the application: `flask run`

## Deployment

### Heroku Deployment

1. Install the Heroku CLI: [Instructions](https://devcenter.heroku.com/articles/heroku-cli)
2. Login to Heroku: `heroku login`
3. Create a new Heroku app: `heroku create andikar-ai`
4. Add a Procfile:
   ```
   web: gunicorn app:app
   ```
5. Add environment variables:
   ```
   heroku config:set FLASK_APP=app.py
   heroku config:set SECRET_KEY=your-secret-key
   heroku config:set MONGODB_URI=your-mongodb-uri
   heroku config:set DB_NAME=andikar_ai
   heroku config:set GOOGLE_CLIENT_ID=934412857118-i13t5ma9afueo40tmohosprsjf4555f0.apps.googleusercontent.com
   heroku config:set GOOGLE_CLIENT_SECRET=your-google-client-secret
   ```
6. Deploy to Heroku: `git push heroku main`

### AWS Deployment

1. Create an EC2 instance or Elastic Beanstalk environment
2. Configure environment variables in the AWS console
3. Use a process manager like Supervisor, systemd, or PM2 to run the Flask app
4. Set up a reverse proxy with Nginx or Apache

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
