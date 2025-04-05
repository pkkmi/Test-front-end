# Railway Environment Variables Setup

To fix the Google OAuth authentication, you need to set the following environment variables in your Railway project:

## Required Environment Variables

1. **GOOGLE_CLIENT_SECRET**
   - Set this to: `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`
   - This is your Google OAuth client secret that was visible in the Google Cloud Console

## How to Set Environment Variables in Railway

1. Go to your Railway project dashboard: https://railway.app/project
2. Select your Andikar AI project
3. Click on the "Variables" tab
4. Add a new variable with:
   - Name: `GOOGLE_CLIENT_SECRET`
   - Value: `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`
5. Click "Add" to save the variable

## After Setting Variables

After adding the environment variable, Railway will automatically redeploy your application. Wait for the deployment to complete, then try the login again.

## Troubleshooting

If you still encounter issues after setting the environment variable:

1. Check the Railway logs for any error messages
2. Verify that the redirect URI in Google Cloud Console exactly matches `https://web-production-c1f4.up.railway.app/callback`
3. Ensure that the JavaScript origins in Google Cloud Console includes `https://web-production-c1f4.up.railway.app`
4. Try clearing your browser cookies and cache before attempting to log in again
