# Authentication & User Management Guide

## Overview

This system implements JWT-based authentication with user CRUD operations. Users can authenticate, and the system tracks the current authenticated user through dependencies.

## Key Components

### 1. **Authentication Utilities** (`app/core/security.py`)
- Password hashing using bcrypt
- JWT token creation and verification
- Token expiration management

### 2. **Dependencies** (`app/core/dependencies.py`)
- `get_db()`: Database session dependency
- `get_current_user()`: Gets authenticated user from JWT token
- `get_current_active_user()`: Gets current active user (can be extended for additional checks)

### 3. **User Service** (`app/services/user_service.py`)
- User CRUD operations
- User authentication
- Password management

### 4. **Routes**
- **Auth Routes** (`app/api/v1/auth.py`): Login endpoints
- **User Routes** (`app/api/v1/user.py`): User CRUD operations

## How to Use

### 1. **Login and Get Token**

```bash
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "user_id": "OWN-ABC12345",
    "email": "user@example.com",
    "name": "John Doe",
    "role": "owner"
  }
}
```

### 2. **Using the Token**

Include the token in the Authorization header:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 3. **Get Current User Info**

```bash
GET /api/v1/users/me
Authorization: Bearer <token>
```

### 4. **Create a User** (Requires Authentication)

```bash
POST /api/v1/users
Authorization: Bearer <token>
Content-Type: application/json

{
  "email": "newuser@example.com",
  "password": "password123",
  "name": "New User",
  "role": "supplier"
}
```

### 5. **Update User** (Requires Authentication)

```bash
PUT /api/v1/users/{user_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Updated Name",
  "email": "updated@example.com"
}
```

### 6. **Change Password** (Requires Authentication)

```bash
POST /api/v1/users/{user_id}/change-password
Authorization: Bearer <token>
Content-Type: application/json

{
  "old_password": "oldpassword",
  "new_password": "newpassword123"
}
```

## Session Management

### How Current User is Validated

1. **Token Extraction**: The `oauth2_scheme` dependency extracts the Bearer token from the Authorization header
2. **Token Verification**: `decode_access_token()` verifies the token signature and expiration
3. **User Lookup**: The system looks up the user by email (stored in token's `sub` claim)
4. **User Return**: The authenticated user is returned and available in route handlers

### Using Current User in Routes

```python
from app.core.dependencies import get_current_active_user
from app.models.user import User

@router.get("/protected")
def protected_route(current_user: User = Depends(get_current_active_user)):
    # current_user is automatically validated and available
    return {"user_id": current_user.id, "email": current_user.email}
```

### Checking User Role

```python
from app.models.user import UserRole

@router.get("/admin-only")
def admin_route(current_user: User = Depends(get_current_active_user)):
    if current_user.role != UserRole.owner:
        raise HTTPException(status_code=403, detail="Admin access required")
    return {"message": "Admin content"}
```

## Environment Variables

Make sure to set these in your `.env` file:

```env
SECRET_KEY=your-secret-key-here  # Used for JWT signing
ACCESS_TOKEN_EXPIRE_MINUTES=30   # Token expiration time
DATABASE_URL=postgresql://user:password@localhost/dbname
```

## User Roles

- `owner`: Full access, can manage all users
- `supplier`: Supplier role
- `customer`: Customer role

## Security Features

1. **Password Hashing**: All passwords are hashed using bcrypt
2. **JWT Tokens**: Secure token-based authentication
3. **Token Expiration**: Tokens expire after configured time
4. **Role-Based Access**: Different roles have different permissions
5. **Self-Protection**: Users can only update/delete themselves (unless owner)

## API Endpoints Summary

### Authentication
- `POST /api/v1/auth/login` - Login and get token
- `POST /api/v1/auth/token` - OAuth2 compatible token endpoint (for Swagger UI)

### Users (All require authentication)
- `GET /api/v1/users/me` - Get current user info
- `GET /api/v1/users` - List all users (with filters)
- `GET /api/v1/users/{user_id}` - Get user by ID
- `POST /api/v1/users` - Create new user
- `PUT /api/v1/users/{user_id}` - Update user
- `DELETE /api/v1/users/{user_id}` - Delete user (owners only)
- `POST /api/v1/users/{user_id}/change-password` - Change password

## Testing with Swagger UI

1. Start your server: `uvicorn app.main:app --reload`
2. Go to `http://localhost:8000/docs`
3. Click "Authorize" button
4. Use the `/api/v1/auth/token` endpoint to get a token
5. Enter the token in the authorization dialog
6. Now you can test all protected endpoints
