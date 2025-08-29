"""
Security features for Agni API framework.
Includes authentication schemes compatible with FastAPI patterns.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from typing import Any, Dict, Optional, Union
from datetime import datetime, timedelta

from .request import Request
from .exceptions import HTTPException, SecurityException
from .dependencies import Dependency


class SecurityManager:
    """
    Manages security schemes and authentication for the application.
    """
    
    def __init__(self):
        self._schemes: Dict[str, Any] = {}
        self._secret_key: Optional[str] = None
    
    def set_secret_key(self, secret_key: str):
        """Set the secret key for signing tokens."""
        self._secret_key = secret_key
    
    def register_scheme(self, name: str, scheme: Any):
        """Register a security scheme."""
        self._schemes[name] = scheme
    
    def get_scheme(self, name: str) -> Optional[Any]:
        """Get a registered security scheme."""
        return self._schemes.get(name)


class HTTPBasic:
    """
    HTTP Basic Authentication scheme.
    """
    
    def __init__(
        self,
        realm: str = "Secure Area",
        auto_error: bool = True,
    ):
        self.realm = realm
        self.auto_error = auto_error
    
    async def __call__(self, request: Request) -> Optional[Dict[str, str]]:
        """Extract and validate basic auth credentials."""
        authorization = request.headers.get("authorization")
        
        if not authorization:
            if self.auto_error:
                raise HTTPException(
                    status_code=401,
                    detail="Missing Authorization header",
                    headers={"WWW-Authenticate": f'Basic realm="{self.realm}"'},
                )
            return None
        
        if not authorization.startswith("Basic "):
            if self.auto_error:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid authentication scheme",
                    headers={"WWW-Authenticate": f'Basic realm="{self.realm}"'},
                )
            return None
        
        try:
            # Decode base64 credentials
            encoded_credentials = authorization[6:]  # Remove "Basic "
            decoded_credentials = base64.b64decode(encoded_credentials).decode("utf-8")
            username, password = decoded_credentials.split(":", 1)
            
            return {
                "username": username,
                "password": password,
            }
        
        except (ValueError, UnicodeDecodeError):
            if self.auto_error:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid credentials format",
                    headers={"WWW-Authenticate": f'Basic realm="{self.realm}"'},
                )
            return None


class HTTPBearer:
    """
    HTTP Bearer Token Authentication scheme.
    """
    
    def __init__(
        self,
        scheme_name: str = "Bearer",
        auto_error: bool = True,
    ):
        self.scheme_name = scheme_name
        self.auto_error = auto_error
    
    async def __call__(self, request: Request) -> Optional[str]:
        """Extract and validate bearer token."""
        authorization = request.headers.get("authorization")
        
        if not authorization:
            if self.auto_error:
                raise HTTPException(
                    status_code=401,
                    detail="Missing Authorization header",
                    headers={"WWW-Authenticate": self.scheme_name},
                )
            return None
        
        scheme, _, token = authorization.partition(" ")
        
        if scheme.lower() != "bearer":
            if self.auto_error:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid authentication scheme",
                    headers={"WWW-Authenticate": self.scheme_name},
                )
            return None
        
        if not token:
            if self.auto_error:
                raise HTTPException(
                    status_code=401,
                    detail="Missing token",
                    headers={"WWW-Authenticate": self.scheme_name},
                )
            return None
        
        return token


class OAuth2PasswordBearer:
    """
    OAuth2 Password Bearer scheme for token-based authentication.
    """
    
    def __init__(
        self,
        token_url: str,
        scheme_name: str = "OAuth2PasswordBearer",
        scopes: Optional[Dict[str, str]] = None,
        auto_error: bool = True,
    ):
        self.token_url = token_url
        self.scheme_name = scheme_name
        self.scopes = scopes or {}
        self.auto_error = auto_error
    
    async def __call__(self, request: Request) -> Optional[str]:
        """Extract OAuth2 bearer token."""
        authorization = request.headers.get("authorization")
        
        if not authorization:
            if self.auto_error:
                raise HTTPException(
                    status_code=401,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return None
        
        scheme, _, token = authorization.partition(" ")
        
        if scheme.lower() != "bearer":
            if self.auto_error:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid authentication scheme",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return None
        
        return token


class APIKeyHeader:
    """
    API Key authentication via header.
    """
    
    def __init__(
        self,
        name: str = "X-API-Key",
        auto_error: bool = True,
    ):
        self.name = name
        self.auto_error = auto_error
    
    async def __call__(self, request: Request) -> Optional[str]:
        """Extract API key from header."""
        api_key = request.headers.get(self.name.lower())
        
        if not api_key:
            if self.auto_error:
                raise HTTPException(
                    status_code=401,
                    detail=f"Missing {self.name} header",
                )
            return None
        
        return api_key


class APIKeyQuery:
    """
    API Key authentication via query parameter.
    """
    
    def __init__(
        self,
        name: str = "api_key",
        auto_error: bool = True,
    ):
        self.name = name
        self.auto_error = auto_error
    
    async def __call__(self, request: Request) -> Optional[str]:
        """Extract API key from query parameter."""
        api_key = request.query_params.get(self.name)
        
        if not api_key:
            if self.auto_error:
                raise HTTPException(
                    status_code=401,
                    detail=f"Missing {self.name} query parameter",
                )
            return None
        
        return api_key


class APIKeyCookie:
    """
    API Key authentication via cookie.
    """
    
    def __init__(
        self,
        name: str = "api_key",
        auto_error: bool = True,
    ):
        self.name = name
        self.auto_error = auto_error
    
    async def __call__(self, request: Request) -> Optional[str]:
        """Extract API key from cookie."""
        api_key = request.cookies.get(self.name)
        
        if not api_key:
            if self.auto_error:
                raise HTTPException(
                    status_code=401,
                    detail=f"Missing {self.name} cookie",
                )
            return None
        
        return api_key


class JWTManager:
    """
    Simple JWT token manager for authentication.
    """
    
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
    
    def create_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """Create a JWT token."""
        try:
            import jwt
        except ImportError:
            raise SecurityException("PyJWT library required for JWT support")
        
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        
        to_encode.update({"exp": expire})
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode a JWT token."""
        try:
            import jwt
        except ImportError:
            raise SecurityException("PyJWT library required for JWT support")
        
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise SecurityException("Token has expired")
        except jwt.JWTError:
            raise SecurityException("Invalid token")


class PasswordHasher:
    """
    Password hashing utilities.
    """
    
    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> str:
        """Hash a password with salt."""
        if salt is None:
            salt = secrets.token_hex(16)
        
        # Use PBKDF2 for password hashing
        key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return f"{salt}:{key.hex()}"
    
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify a password against its hash."""
        try:
            salt, key = hashed.split(':', 1)
            new_key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
            return hmac.compare_digest(key, new_key.hex())
        except ValueError:
            return False
    
    @staticmethod
    def generate_salt() -> str:
        """Generate a random salt."""
        return secrets.token_hex(16)


# Security dependency functions
def get_current_user_from_token(
    token: str,
    jwt_manager: JWTManager,
) -> Dict[str, Any]:
    """
    Get current user from JWT token.
    This is an example - customize based on your user model.
    """
    try:
        payload = jwt_manager.verify_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise SecurityException("Invalid token payload")
        
        # Here you would typically fetch user from database
        # For now, return mock user data
        return {
            "id": user_id,
            "username": payload.get("username"),
            "email": payload.get("email"),
            "scopes": payload.get("scopes", []),
        }
    
    except SecurityException:
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_scopes(*required_scopes: str):
    """
    Dependency that requires specific OAuth2 scopes.
    """
    def dependency(user: Dict[str, Any]) -> Dict[str, Any]:
        user_scopes = user.get("scopes", [])
        
        for scope in required_scopes:
            if scope not in user_scopes:
                raise HTTPException(
                    status_code=403,
                    detail=f"Missing required scope: {scope}",
                )
        
        return user
    
    return dependency


# Utility functions
def generate_api_key(length: int = 32) -> str:
    """Generate a random API key."""
    return secrets.token_urlsafe(length)


def constant_time_compare(a: str, b: str) -> bool:
    """Compare two strings in constant time to prevent timing attacks."""
    return hmac.compare_digest(a, b)
