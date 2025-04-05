# Setting up Environment Variables in Railway

## CRITICAL: Your Google OAuth is failing because the client secret is not set

The logs clearly show that your Google client secret is not properly configured in Railway:
```
Google Client Secret is set: False
```

## Step-by-Step Instructions for Setting Environment Variables

1. Go to your Railway dashboard: https://railway.app/dashboard
2. Select your project (Test-front-end or Andikar AI)
3. Click on the "Variables" tab in the top navigation
4. Click the "New Variable" button
5. Add the following variable:
   - **KEY:** `GOOGLE_CLIENT_SECRET`
   - **VALUE:** `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`
6. Click "Add" to save the variable

## Verifying the Variable is Set

1. After adding the variable, Railway will automatically trigger a new deployment
2. Wait for the deployment to complete (usually 1-3 minutes)
3. Once deployed, try logging in again
4. If issues persist, check the `/debug` endpoint on your application

## Common Mistakes to Avoid

- **Typos in the variable name:** Make sure it's exactly `GOOGLE_CLIENT_SECRET` (case-sensitive)
- **Extra spaces:** Ensure there are no leading or trailing spaces in the value
- **Quotes:** Do not include quotation marks around the value
- **Project selection:** Make sure you're adding the variable to the correct Railway project

## Environment Variables That Should Be Set

| Variable Name | Description | Status |
|---------------|-------------|--------|
| GOOGLE_CLIENT_SECRET | Google OAuth client secret | ❌ Not set |
| MONGODB_URI | MongoDB connection string (optional) | ⚠️ Optional |
| SECRET_KEY | Flask session encryption key | ✅ Auto-generated |

## Quick Verification Script

To verify if environment variables are set correctly, Railway has a "Variables" tab that shows all currently set variables. You can also see logs in the "Deployments" tab that will show if variables are properly loaded.

![Railway Variables Interface](https://railway.app/brand/logo-light.svg)
