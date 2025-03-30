# Andikar AI Backend

This directory contains the backend implementation for the Andikar AI frontend application. The backend provides secure API access, user authentication, and data management services.

## Architecture

The backend is integrated with the Flask frontend and provides the following features:

1. **User Authentication and Authorization**
   - Secure login and session management
   - API token generation and validation (JWT-based)
   - User permission checking based on subscription plan

2. **API Service Layer**
   - Secure communication with external APIs
   - Error handling and retry mechanisms
   - Rate limiting to prevent abuse
   - Caching for performance optimization

3. **User Account Management**
   - User registration and profile management
   - Subscription plan handling
   - Payment processing
   - Usage tracking

4. **RESTful API Endpoints**
   - Provides a complete REST API for frontend and potential third-party integrations
   - Versioned API routes (/api/v1/...)
   - Proper error responses and status codes

## Module Structure

- **auth.py**: Authentication and authorization services
- **api_service.py**: External API communication layer
- **users.py**: User data and account management
- **api_routes.py**: RESTful API endpoint definitions

## API Endpoints

The backend exposes the following API endpoints:

### Authentication

- `GET /api/v1/health`: Health check endpoint
- `GET /api/v1/status`: External API status check
- `POST /api/v1/auth/login`: User login (returns JWT token)
- `POST /api/v1/auth/logout`: User logout
- `POST /api/v1/auth/register`: User registration

### User Management

- `GET /api/v1/user/profile`: Get user profile information
- `POST /api/v1/user/update-plan`: Update subscription plan
- `POST /api/v1/user/payment`: Process a payment
- `POST /api/v1/user/update-api-keys`: Update user API keys

### Text Processing

- `POST /api/v1/humanize`: Humanize AI-generated text
- `POST /api/v1/detect`: Detect if text is AI-generated

## Authentication

The backend uses JWT (JSON Web Tokens) for API authentication. To use the API:

1. Obtain a token by calling the login endpoint with valid credentials
2. Include the token in the Authorization header for subsequent requests:
   ```
   Authorization: Bearer <your_token>
   ```

## Security Measures

The backend implements several security measures:

1. Rate limiting to prevent abuse
2. Permission checking based on user plan
3. Secure token-based authentication
4. Input validation to prevent injection attacks
5. Error handling that doesn't leak sensitive information

## Future Enhancements

Planned enhancements for future versions:

1. Database integration for persistent storage
2. Email verification system
3. Enhanced analytics and usage reporting
4. OAuth integration for third-party authentication
5. Additional payment gateways
6. Webhooks for integration with other services

## Usage Example

```python
import requests

# Login to get a token
response = requests.post('http://localhost:5000/api/v1/auth/login', 
                        json={'username': 'demo', 'password': 'demo'})
token = response.json()['token']

# Use the token to access protected endpoints
headers = {'Authorization': f'Bearer {token}'}
response = requests.post('http://localhost:5000/api/v1/humanize',
                        headers=headers,
                        json={'text': 'Your AI-generated text here'})

print(response.json()['humanized_text'])
```
