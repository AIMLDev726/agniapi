"""
Session management for AgniAPI with Flask-style secure cookie sessions.

This module provides comprehensive session management including:
- Secure cookie sessions with signing and encryption
- Multiple session backends (Redis, database, file)
- Flask-style session interface
- Configurable session options and security features
"""

from __future__ import annotations

import json
import pickle
import time
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, MutableMapping, Optional, Union
import hashlib
import hmac
import base64

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False

try:
    import redis
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from .request import Request
from .response import Response


class SessionInterface(ABC):
    """Abstract base class for session interfaces."""
    
    @abstractmethod
    async def open_session(self, request: Request) -> Optional['Session']:
        """Open a session from the request."""
        pass
    
    @abstractmethod
    async def save_session(self, session: 'Session', response: Response) -> None:
        """Save the session to the response."""
        pass


class Session(MutableMapping[str, Any]):
    """
    Session object that behaves like a dictionary.
    Provides Flask-style session interface.
    """
    
    def __init__(self, data: Optional[Dict[str, Any]] = None, session_id: Optional[str] = None):
        self._data: Dict[str, Any] = data or {}
        self.session_id = session_id or str(uuid.uuid4())
        self.new = session_id is None
        self.modified = False
        self.permanent = False
        self.accessed = False
    
    def __getitem__(self, key: str) -> Any:
        self.accessed = True
        return self._data[key]
    
    def __setitem__(self, key: str, value: Any) -> None:
        self._data[key] = value
        self.modified = True
    
    def __delitem__(self, key: str) -> None:
        del self._data[key]
        self.modified = True
    
    def __iter__(self):
        self.accessed = True
        return iter(self._data)
    
    def __len__(self) -> int:
        self.accessed = True
        return len(self._data)
    
    def __contains__(self, key: Any) -> bool:
        self.accessed = True
        return key in self._data
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the session."""
        self.accessed = True
        return self._data.get(key, default)
    
    def pop(self, key: str, default: Any = None) -> Any:
        """Pop a value from the session."""
        self.modified = True
        return self._data.pop(key, default)
    
    def setdefault(self, key: str, default: Any = None) -> Any:
        """Set default value if key doesn't exist."""
        if key not in self._data:
            self.modified = True
        return self._data.setdefault(key, default)
    
    def clear(self) -> None:
        """Clear all session data."""
        self._data.clear()
        self.modified = True
    
    def update(self, *args, **kwargs) -> None:
        """Update session data."""
        self._data.update(*args, **kwargs)
        self.modified = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary."""
        return dict(self._data)


class SecureCookieSessionInterface(SessionInterface):
    """
    Secure cookie-based session interface.
    Signs and optionally encrypts session data in cookies.
    """
    
    def __init__(
        self,
        secret_key: str,
        *,
        cookie_name: str = "session",
        cookie_domain: Optional[str] = None,
        cookie_path: str = "/",
        cookie_httponly: bool = True,
        cookie_secure: bool = False,
        cookie_samesite: str = "Lax",
        permanent_session_lifetime: timedelta = timedelta(days=31),
        use_encryption: bool = True,
        salt: str = "agniapi-session",
    ):
        if not secret_key:
            raise ValueError("Secret key is required for secure sessions")
        
        self.secret_key = secret_key.encode() if isinstance(secret_key, str) else secret_key
        self.cookie_name = cookie_name
        self.cookie_domain = cookie_domain
        self.cookie_path = cookie_path
        self.cookie_httponly = cookie_httponly
        self.cookie_secure = cookie_secure
        self.cookie_samesite = cookie_samesite
        self.permanent_session_lifetime = permanent_session_lifetime
        self.use_encryption = use_encryption and CRYPTOGRAPHY_AVAILABLE
        self.salt = salt.encode()
        
        # Initialize encryption if available and requested
        if self.use_encryption:
            self._init_encryption()
    
    def _init_encryption(self) -> None:
        """Initialize encryption key derivation."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.secret_key))
        self.fernet = Fernet(key)
    
    def _sign_data(self, data: bytes) -> str:
        """Sign data with HMAC."""
        signature = hmac.new(self.secret_key, data, hashlib.sha256).hexdigest()
        return base64.urlsafe_b64encode(data).decode() + "." + signature
    
    def _unsign_data(self, signed_data: str) -> Optional[bytes]:
        """Verify and unsign data."""
        try:
            data_b64, signature = signed_data.rsplit(".", 1)
            data = base64.urlsafe_b64decode(data_b64.encode())
            expected_signature = hmac.new(self.secret_key, data, hashlib.sha256).hexdigest()
            
            if hmac.compare_digest(signature, expected_signature):
                return data
        except (ValueError, TypeError):
            pass
        return None
    
    def _serialize_session(self, session: Session) -> str:
        """Serialize session data."""
        data = {
            'data': session.to_dict(),
            'session_id': session.session_id,
            'permanent': session.permanent,
            'created': time.time(),
        }
        
        serialized = json.dumps(data, separators=(',', ':')).encode()
        
        if self.use_encryption:
            serialized = self.fernet.encrypt(serialized)
        
        return self._sign_data(serialized)
    
    def _deserialize_session(self, session_data: str) -> Optional[Session]:
        """Deserialize session data."""
        try:
            data = self._unsign_data(session_data)
            if data is None:
                return None
            
            if self.use_encryption:
                data = self.fernet.decrypt(data)
            
            session_dict = json.loads(data.decode())
            
            # Check if session is expired
            created = session_dict.get('created', 0)
            is_permanent = session_dict.get('permanent', False)
            
            if is_permanent:
                max_age = self.permanent_session_lifetime.total_seconds()
            else:
                max_age = 86400  # 24 hours for non-permanent sessions
            
            if time.time() - created > max_age:
                return None
            
            session = Session(
                data=session_dict.get('data', {}),
                session_id=session_dict.get('session_id')
            )
            session.permanent = is_permanent
            session.new = False
            
            return session
            
        except Exception:
            return None
    
    async def open_session(self, request: Request) -> Optional[Session]:
        """Open a session from the request."""
        session_cookie = request.cookies.get(self.cookie_name)
        
        if session_cookie:
            session = self._deserialize_session(session_cookie)
            if session:
                return session
        
        # Return new empty session
        return Session()
    
    async def save_session(self, session: Session, response: Response) -> None:
        """Save the session to the response."""
        if not session.modified and not session.new:
            return
        
        # If session is empty and not new, delete the cookie
        if not session and not session.new:
            response.delete_cookie(
                self.cookie_name,
                domain=self.cookie_domain,
                path=self.cookie_path
            )
            return
        
        # Serialize and set cookie
        cookie_value = self._serialize_session(session)
        
        # Calculate expiry
        if session.permanent:
            expires = datetime.utcnow() + self.permanent_session_lifetime
            max_age = int(self.permanent_session_lifetime.total_seconds())
        else:
            expires = None
            max_age = None
        
        response.set_cookie(
            self.cookie_name,
            cookie_value,
            max_age=max_age,
            expires=expires,
            domain=self.cookie_domain,
            path=self.cookie_path,
            secure=self.cookie_secure,
            httponly=self.cookie_httponly,
            samesite=self.cookie_samesite
        )


class RedisSessionInterface(SessionInterface):
    """Redis-based session interface."""
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        *,
        cookie_name: str = "session_id",
        cookie_domain: Optional[str] = None,
        cookie_path: str = "/",
        cookie_httponly: bool = True,
        cookie_secure: bool = False,
        cookie_samesite: str = "Lax",
        permanent_session_lifetime: timedelta = timedelta(days=31),
        key_prefix: str = "session:",
        **redis_kwargs
    ):
        if not REDIS_AVAILABLE:
            raise ImportError("Redis is not available. Install with: pip install redis")
        
        self.redis_url = redis_url
        self.redis_kwargs = redis_kwargs
        self.cookie_name = cookie_name
        self.cookie_domain = cookie_domain
        self.cookie_path = cookie_path
        self.cookie_httponly = cookie_httponly
        self.cookie_secure = cookie_secure
        self.cookie_samesite = cookie_samesite
        self.permanent_session_lifetime = permanent_session_lifetime
        self.key_prefix = key_prefix
        self._client: Optional[aioredis.Redis] = None
    
    async def _get_client(self) -> aioredis.Redis:
        """Get or create Redis client."""
        if self._client is None:
            self._client = aioredis.from_url(self.redis_url, **self.redis_kwargs)
        return self._client
    
    async def open_session(self, request: Request) -> Optional[Session]:
        """Open a session from Redis."""
        session_id = request.cookies.get(self.cookie_name)
        
        if session_id:
            client = await self._get_client()
            session_key = f"{self.key_prefix}{session_id}"
            
            session_data = await client.get(session_key)
            if session_data:
                try:
                    data = pickle.loads(session_data)
                    session = Session(data=data, session_id=session_id)
                    session.new = False
                    return session
                except (pickle.PickleError, TypeError):
                    # Invalid session data, delete it
                    await client.delete(session_key)
        
        # Return new session
        return Session()
    
    async def save_session(self, session: Session, response: Response) -> None:
        """Save the session to Redis."""
        if not session.modified and not session.new:
            return
        
        client = await self._get_client()
        session_key = f"{self.key_prefix}{session.session_id}"
        
        # If session is empty and not new, delete it
        if not session and not session.new:
            await client.delete(session_key)
            response.delete_cookie(
                self.cookie_name,
                domain=self.cookie_domain,
                path=self.cookie_path
            )
            return
        
        # Serialize and store session data
        session_data = pickle.dumps(session.to_dict())
        
        # Calculate TTL
        if session.permanent:
            ttl = int(self.permanent_session_lifetime.total_seconds())
            expires = datetime.utcnow() + self.permanent_session_lifetime
            max_age = ttl
        else:
            ttl = 86400  # 24 hours
            expires = None
            max_age = None
        
        await client.setex(session_key, ttl, session_data)
        
        # Set session ID cookie
        response.set_cookie(
            self.cookie_name,
            session.session_id,
            max_age=max_age,
            expires=expires,
            domain=self.cookie_domain,
            path=self.cookie_path,
            secure=self.cookie_secure,
            httponly=self.cookie_httponly,
            samesite=self.cookie_samesite
        )


# Session middleware for automatic session handling
class SessionMiddleware:
    """Middleware to automatically handle sessions."""
    
    def __init__(self, session_interface: SessionInterface):
        self.session_interface = session_interface
    
    async def __call__(self, request: Request, call_next):
        """Process request with session handling."""
        # Open session
        session = await self.session_interface.open_session(request)
        request.state.session = session
        
        # Process request
        response = await call_next(request)
        
        # Save session
        if session:
            await self.session_interface.save_session(session, response)
        
        return response


def configure_sessions(
    session_type: str = "secure_cookie",
    secret_key: Optional[str] = None,
    **kwargs
) -> SessionInterface:
    """Configure and return a session interface."""
    if session_type == "secure_cookie":
        if not secret_key:
            raise ValueError("Secret key is required for secure cookie sessions")
        return SecureCookieSessionInterface(secret_key, **kwargs)
    elif session_type == "redis":
        return RedisSessionInterface(**kwargs)
    else:
        raise ValueError(f"Unknown session type: {session_type}")
