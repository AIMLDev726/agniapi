"""
Security example using Agni API framework.
Demonstrates authentication, authorization, and security features.
"""

from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel

from agniapi import AgniAPI, HTTPException, Depends
from agniapi.security import (
    HTTPBearer, HTTPBasic, OAuth2PasswordBearer, APIKeyHeader,
    JWTManager, PasswordHasher, generate_api_key
)
from agniapi.response import JSONResponse


# Pydantic models
class User(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool = True
    is_admin: bool = False
    scopes: List[str] = []


class UserCreate(BaseModel):
    username: str
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


class LoginRequest(BaseModel):
    username: str
    password: str


# Create the application
app = AgniAPI(
    title="Security Example",
    description="Comprehensive security features demonstration",
    version="1.0.0"
)

# Security setup
jwt_manager = JWTManager("your-super-secret-key-change-in-production")
password_hasher = PasswordHasher()

# Security schemes
bearer_security = HTTPBearer()
basic_security = HTTPBasic()
oauth2_security = OAuth2PasswordBearer(token_url="/auth/token")
api_key_security = APIKeyHeader(name="X-API-Key")

# Mock database
users_db = [
    {
        "id": 1,
        "username": "admin",
        "email": "admin@aimldev726.com",
        "password_hash": password_hasher.hash_password("admin123"),
        "is_active": True,
        "is_admin": True,
        "scopes": ["read", "write", "admin"]
    },
    {
        "id": 2,
        "username": "user",
        "email": "user@aimldev726.com",
        "password_hash": password_hasher.hash_password("user123"),
        "is_active": True,
        "is_admin": False,
        "scopes": ["read"]
    },
    {
        "id": 3,
        "username": "editor",
        "email": "editor@aimldev726.com",
        "password_hash": password_hasher.hash_password("editor123"),
        "is_active": True,
        "is_admin": False,
        "scopes": ["read", "write"]
    }
]

api_keys_db = {
    "sk-test-key-123": {"user_id": 1, "scopes": ["read", "write", "admin"]},
    "sk-user-key-456": {"user_id": 2, "scopes": ["read"]},
}


# Dependency functions
async def get_user_by_username(username: str) -> Optional[dict]:
    """Get user by username."""
    return next((u for u in users_db if u["username"] == username), None)


async def get_user_by_id(user_id: int) -> Optional[dict]:
    """Get user by ID."""
    return next((u for u in users_db if u["id"] == user_id), None)


async def authenticate_user(username: str, password: str) -> Optional[dict]:
    """Authenticate user with username and password."""
    user = await get_user_by_username(username)
    if not user:
        return None
    
    if not password_hasher.verify_password(password, user["password_hash"]):
        return None
    
    if not user["is_active"]:
        return None
    
    return user


async def get_current_user_jwt(token: str = Depends(bearer_security)) -> User:
    """Get current user from JWT token."""
    try:
        payload = jwt_manager.verify_token(token)
        user_id = payload.get("sub")
        
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user_data = await get_user_by_id(int(user_id))
        if not user_data:
            raise HTTPException(status_code=401, detail="User not found")
        
        if not user_data["is_active"]:
            raise HTTPException(status_code=401, detail="User is inactive")
        
        return User(
            id=user_data["id"],
            username=user_data["username"],
            email=user_data["email"],
            is_active=user_data["is_active"],
            is_admin=user_data["is_admin"],
            scopes=user_data["scopes"]
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_basic(credentials = Depends(basic_security)) -> User:
    """Get current user from basic auth."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    user_data = await authenticate_user(credentials["username"], credentials["password"])
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    return User(
        id=user_data["id"],
        username=user_data["username"],
        email=user_data["email"],
        is_active=user_data["is_active"],
        is_admin=user_data["is_admin"],
        scopes=user_data["scopes"]
    )


async def get_current_user_api_key(api_key: str = Depends(api_key_security)) -> User:
    """Get current user from API key."""
    if api_key not in api_keys_db:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    key_data = api_keys_db[api_key]
    user_data = await get_user_by_id(key_data["user_id"])
    
    if not user_data or not user_data["is_active"]:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return User(
        id=user_data["id"],
        username=user_data["username"],
        email=user_data["email"],
        is_active=user_data["is_active"],
        is_admin=user_data["is_admin"],
        scopes=key_data["scopes"]
    )


def require_scope(required_scope: str):
    """Dependency that requires a specific scope."""
    def scope_checker(current_user: User = Depends(get_current_user_jwt)) -> User:
        if required_scope not in current_user.scopes:
            raise HTTPException(
                status_code=403,
                detail=f"Operation requires '{required_scope}' scope"
            )
        return current_user
    return scope_checker


def require_admin(current_user: User = Depends(get_current_user_jwt)) -> User:
    """Dependency that requires admin privileges."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required"
        )
    return current_user


# Public endpoints
@app.get("/")
async def root():
    """Public root endpoint."""
    return {
        "message": "Security Example API",
        "auth_methods": ["JWT Bearer", "Basic Auth", "API Key"],
        "endpoints": {
            "login": "/auth/login",
            "token": "/auth/token",
            "register": "/auth/register",
            "profile": "/auth/me",
            "protected": "/protected/*"
        }
    }


@app.get("/public")
async def public_endpoint():
    """Public endpoint that doesn't require authentication."""
    return {"message": "This is a public endpoint", "timestamp": datetime.now().isoformat()}


# Authentication endpoints
@app.post("/auth/register", response_model=User, status_code=201)
async def register(user_data: UserCreate):
    """Register a new user."""
    # Check if username already exists
    existing_user = await get_user_by_username(user_data.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # Create new user
    new_id = max([u["id"] for u in users_db], default=0) + 1
    password_hash = password_hasher.hash_password(user_data.password)
    
    new_user = {
        "id": new_id,
        "username": user_data.username,
        "email": user_data.email,
        "password_hash": password_hash,
        "is_active": True,
        "is_admin": False,
        "scopes": ["read"]
    }
    
    users_db.append(new_user)
    
    return User(
        id=new_user["id"],
        username=new_user["username"],
        email=new_user["email"],
        is_active=new_user["is_active"],
        is_admin=new_user["is_admin"],
        scopes=new_user["scopes"]
    )


@app.post("/auth/login", response_model=Token)
async def login(login_data: LoginRequest):
    """Login with username and password."""
    user = await authenticate_user(login_data.username, login_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create JWT token
    expires_delta = timedelta(hours=24)
    token_data = {
        "sub": str(user["id"]),
        "username": user["username"],
        "scopes": user["scopes"]
    }
    
    access_token = jwt_manager.create_token(token_data, expires_delta)
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=int(expires_delta.total_seconds())
    )


@app.post("/auth/token", response_model=Token)
async def get_token(username: str, password: str):
    """OAuth2-style token endpoint."""
    user = await authenticate_user(username, password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    expires_delta = timedelta(hours=24)
    token_data = {
        "sub": str(user["id"]),
        "username": user["username"],
        "scopes": user["scopes"]
    }
    
    access_token = jwt_manager.create_token(token_data, expires_delta)
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=int(expires_delta.total_seconds())
    )


# Protected endpoints with different auth methods
@app.get("/auth/me", response_model=User)
async def get_current_user_info(current_user: User = Depends(get_current_user_jwt)):
    """Get current user information (JWT auth)."""
    return current_user


@app.get("/auth/me/basic", response_model=User)
async def get_current_user_basic_auth(current_user: User = Depends(get_current_user_basic)):
    """Get current user information (Basic auth)."""
    return current_user


@app.get("/auth/me/apikey", response_model=User)
async def get_current_user_api_key_auth(current_user: User = Depends(get_current_user_api_key)):
    """Get current user information (API key auth)."""
    return current_user


# Scope-based protection
@app.get("/protected/read")
async def read_protected(current_user: User = Depends(require_scope("read"))):
    """Endpoint that requires 'read' scope."""
    return {
        "message": "You have read access",
        "user": current_user.username,
        "scopes": current_user.scopes
    }


@app.get("/protected/write")
async def write_protected(current_user: User = Depends(require_scope("write"))):
    """Endpoint that requires 'write' scope."""
    return {
        "message": "You have write access",
        "user": current_user.username,
        "scopes": current_user.scopes
    }


@app.get("/protected/admin")
async def admin_protected(current_user: User = Depends(require_admin)):
    """Endpoint that requires admin privileges."""
    return {
        "message": "You have admin access",
        "user": current_user.username,
        "is_admin": current_user.is_admin,
        "all_users": len(users_db)
    }


# API key management (admin only)
@app.post("/admin/api-keys")
async def create_api_key(
    user_id: int,
    scopes: List[str],
    current_user: User = Depends(require_admin)
):
    """Create a new API key (admin only)."""
    target_user = await get_user_by_id(user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Generate new API key
    api_key = generate_api_key()
    api_keys_db[api_key] = {
        "user_id": user_id,
        "scopes": scopes
    }
    
    return {
        "api_key": api_key,
        "user_id": user_id,
        "scopes": scopes,
        "created_by": current_user.username
    }


@app.get("/admin/users")
async def list_users(current_user: User = Depends(require_admin)):
    """List all users (admin only)."""
    return {
        "users": [
            {
                "id": u["id"],
                "username": u["username"],
                "email": u["email"],
                "is_active": u["is_active"],
                "is_admin": u["is_admin"],
                "scopes": u["scopes"]
            }
            for u in users_db
        ],
        "total": len(users_db)
    }


if __name__ == "__main__":
    print("Starting Security Example Server...")
    print("\nTest credentials:")
    print("  Admin: admin / admin123")
    print("  User: user / user123")
    print("  Editor: editor / editor123")
    print("\nTest API keys:")
    print("  Admin: sk-test-key-123")
    print("  User: sk-user-key-456")
    print("\nEndpoints:")
    print("  POST /auth/register - Register new user")
    print("  POST /auth/login - Login with credentials")
    print("  GET /auth/me - Get user info (JWT)")
    print("  GET /protected/read - Requires 'read' scope")
    print("  GET /protected/write - Requires 'write' scope")
    print("  GET /protected/admin - Requires admin privileges")
    print("  GET /docs - API documentation")
    
    app.run(host="127.0.0.1", port=8000, debug=True)
