# Andikar AI Backend

This is the backend implementation for the Andikar AI system that humanizes AI-generated text. The backend handles user authentication, API communication, and business logic, providing a secure layer between the frontend and external APIs.

## Features

- **Secure Authentication**: JWT-based authentication for frontend and API access
- **User Management**: Account information, subscription plans, and usage tracking
- **API Integration**: Secure communication with the Humanizer API
- **Rate Limiting**: Prevents API abuse based on subscription plan
- **RESTful API**: Complete API for frontend and potential third-party integration

## Architecture

The backend is structured into several modules:

- `auth.py`: Handles user authentication and authorization
- `users.py`: Manages user accounts, rate limits, and subscription plans
- `api_service.py`: Communicates with the external humanization API
- `api_routes.py`: Defines RESTful API endpoints for the frontend

## API Endpoints

The backend exposes RESTful API endpoints at `/api/v1/`:

- `/api/v1/auth/login`: User login, returns JWT token
- `/api/v1/auth/register`: User registration
- `/api/v1/auth/logout`: User logout
- `/api/v1/user`: Get user account information
- `/api/v1/humanize`: Humanize text through the API
- `/api/v1/status`: Get API status

## Authentication Flow

1. User logs in through the frontend
2. Backend validates credentials and returns a JWT token
3. Frontend stores token and includes it in subsequent requests
4. Backend validates token for protected routes

## Text Humanization Flow

1. User enters text in the frontend
2. Frontend sends text to backend API
3. Backend validates user authentication and checks rate limits
4. Backend calls external API securely
5. Backend returns humanized text to frontend
6. Frontend displays results to user

## Configuration

The backend uses environment variables for configuration:

- `JWT_SECRET`: Secret key for JWT token generation
- `JWT_EXPIRATION`: Token expiration time in seconds
- `HUMANIZER_API_URL`: URL of the external humanization API
- `HUMANIZER_API_KEY`: API key for the external API

## Extending the Backend

To extend the backend:

1. Add new modules to the `backend` directory
2. Update `api_routes.py` to include new endpoints
3. Update the main app to include new functionality

## Security

The backend implements several security measures:

- JWT-based authentication
- Password hashing
- Rate limiting
- Input validation
- Error handling

## Integration with Frontend

The backend integrates with the frontend through:

1. JWT-based authentication
2. RESTful API endpoints
3. Session management

## Development

To run the backend for development:

1. Clone the repository
2. Install dependencies with `pip install -r requirements.txt`
3. Set up environment variables
4. Run the Flask app with `python app.py`

## Testing

To test the backend:

1. Use the `api-test` endpoint at `/api-test`
2. Check API status at `/api/v1/status`
3. Test authentication with `/api/v1/auth/login`
