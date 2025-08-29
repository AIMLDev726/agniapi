"""
Dependency injection system for Agni API framework.
Based on FastAPI's dependency injection with Flask compatibility.
"""

from __future__ import annotations

import inspect
from typing import Any, Callable, Dict, List, Optional, Type, Union, get_type_hints
from functools import wraps

from .types import Dependency, DependencyCallable, is_async_callable
from .request import Request
from .exceptions import HTTPException


class DependencyInjector:
    """
    Main dependency injection system.
    Handles resolving and caching dependencies.
    """
    
    def __init__(self):
        self._dependency_cache: Dict[str, Dict[str, Any]] = {}
        self._global_dependencies: List[Dependency] = []
    
    def add_global_dependency(self, dependency: Union[Dependency, DependencyCallable]):
        """Add a global dependency that applies to all routes."""
        if not isinstance(dependency, Dependency):
            dependency = Dependency(dependency)
        self._global_dependencies.append(dependency)
    
    async def resolve_dependencies(
        self,
        func: Callable,
        request: Request,
        path_params: Dict[str, Any],
        extra_dependencies: Optional[List[Dependency]] = None,
    ) -> Dict[str, Any]:
        """
        Resolve all dependencies for a function.
        Returns a dictionary of resolved dependency values.
        """
        resolved = {}

        # Get function signature and type hints
        sig = inspect.signature(func)
        type_hints = get_type_hints(func)

        # Create cache key for this request
        cache_key = id(request)
        if cache_key not in self._dependency_cache:
            self._dependency_cache[cache_key] = {}

        # Resolve global dependencies first
        for dependency in self._global_dependencies:
            await self._resolve_single_dependency(dependency, request, cache_key)

        # Resolve extra dependencies
        if extra_dependencies:
            for dependency in extra_dependencies:
                await self._resolve_single_dependency(dependency, request, cache_key)

        # Resolve each parameter
        for param_name, param in sig.parameters.items():
            # Skip request parameter (will be injected automatically)
            if param_name == "request" and (param.annotation in (Request, inspect.Parameter.empty) or param.annotation == Request):
                resolved[param_name] = request
                continue

            # Check if parameter has a default value that's a Dependency
            if isinstance(param.default, Dependency):
                dependency = param.default
                resolved[param_name] = await self._resolve_single_dependency(
                    dependency, request, cache_key
                )
                continue

            # Check for path parameters first (highest priority)
            if param_name in path_params:
                value = path_params[param_name]
                # Type conversion for path parameters
                if param.annotation != inspect.Parameter.empty:
                    try:
                        value = self._convert_type(value, param.annotation, param_name, "path")
                    except (ValueError, TypeError) as e:
                        raise HTTPException(
                            status_code=422,
                            detail=f"Invalid type for path parameter '{param_name}': {str(e)}"
                        )
                resolved[param_name] = value
                continue

            # Check for query parameters
            if param_name in request.query_params:
                value = request.query_params[param_name]
                # Type conversion
                if param.annotation != inspect.Parameter.empty:
                    try:
                        if param.annotation == list or (hasattr(param.annotation, '__origin__') and param.annotation.__origin__ == list):
                            value = request.query_params.getlist(param_name)
                        else:
                            value = self._convert_type(value, param.annotation, param_name, "query")
                    except (ValueError, TypeError) as e:
                        raise HTTPException(
                            status_code=422,
                            detail=f"Invalid type for query parameter '{param_name}': {str(e)}"
                        )
                resolved[param_name] = value
                continue

            # Try to resolve from type annotation (for request body models)
            if param.annotation != inspect.Parameter.empty:
                # Check for Pydantic models
                if self._is_pydantic_model(param.annotation):
                    try:
                        model_data = await request.parse_model(param.annotation)
                        resolved[param_name] = model_data
                        continue
                    except Exception as e:
                        raise HTTPException(
                            status_code=422,
                            detail=f"Validation error for {param_name}: {str(e)}"
                        )

                # Check for special types like UploadFile, BackgroundTasks, etc.
                if param.annotation.__name__ == 'UploadFile':
                    # Handle file uploads
                    form_data = await request.form()
                    if param_name in form_data:
                        resolved[param_name] = form_data[param_name]
                        continue

                if param.annotation.__name__ == 'BackgroundTasks':
                    from .types import BackgroundTasks
                    resolved[param_name] = BackgroundTasks()
                    continue

            # Check if parameter has a default value
            if param.default != inspect.Parameter.empty:
                resolved[param_name] = param.default
                continue

            # If we reach here and the parameter is required, it's missing
            if param.default == inspect.Parameter.empty:
                # Only raise error if it's not a special parameter we handle elsewhere
                if param_name not in ['request'] and not isinstance(param.default, Dependency):
                    raise HTTPException(
                        status_code=422,
                        detail=f"Missing required parameter: {param_name}"
                    )

        return resolved

    def _convert_type(self, value: str, target_type: type, param_name: str, param_source: str) -> Any:
        """Convert string value to target type."""
        if target_type == str:
            return value
        elif target_type == int:
            return int(value)
        elif target_type == float:
            return float(value)
        elif target_type == bool:
            return value.lower() in ('true', '1', 'yes', 'on')
        else:
            # Try to call the type constructor
            try:
                return target_type(value)
            except (ValueError, TypeError):
                raise ValueError(f"Cannot convert {param_source} parameter '{param_name}' to {target_type.__name__}")

    def _is_pydantic_model(self, annotation: type) -> bool:
        """Check if annotation is a Pydantic model."""
        try:
            # Check for Pydantic v2
            if hasattr(annotation, 'model_validate'):
                return True
            # Check for Pydantic v1
            if hasattr(annotation, '__pydantic_model__'):
                return True
            # Check if it's a BaseModel subclass
            if hasattr(annotation, '__bases__'):
                for base in annotation.__bases__:
                    if base.__name__ == 'BaseModel':
                        return True
            return False
        except:
            return False

    async def _resolve_single_dependency(
        self,
        dependency: Dependency,
        request: Request,
        cache_key: str,
    ) -> Any:
        """Resolve a single dependency."""
        # Check cache if caching is enabled
        if dependency.use_cache:
            dep_cache_key = f"{dependency.dependency.__name__}_{id(dependency)}"
            if dep_cache_key in self._dependency_cache[cache_key]:
                return self._dependency_cache[cache_key][dep_cache_key]
        
        # Recursively resolve dependencies of this dependency
        dep_resolved = await self.resolve_dependencies(
            dependency.dependency,
            request,
            {},  # No path params for dependencies
        )
        
        # Call the dependency function
        try:
            if dependency.is_async:
                result = await dependency.dependency(**dep_resolved)
            else:
                result = dependency.dependency(**dep_resolved)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Dependency resolution failed: {str(e)}"
            )
        
        # Cache the result if caching is enabled
        if dependency.use_cache:
            dep_cache_key = f"{dependency.dependency.__name__}_{id(dependency)}"
            self._dependency_cache[cache_key][dep_cache_key] = result
        
        return result
    
    def clear_cache(self, request: Request):
        """Clear dependency cache for a request."""
        cache_key = id(request)
        if cache_key in self._dependency_cache:
            del self._dependency_cache[cache_key]


def Depends(
    dependency: DependencyCallable,
    *,
    use_cache: bool = True,
    scope: str = "request",
) -> Any:
    """
    Create a dependency (FastAPI-style).
    
    Args:
        dependency: The dependency function to call
        use_cache: Whether to cache the dependency result
        scope: Scope of the dependency cache
    
    Returns:
        A Dependency object that can be used as a default parameter value
    """
    return Dependency(dependency, use_cache=use_cache, scope=scope)


def get_typed_signature(func: Callable) -> inspect.Signature:
    """Get function signature with type information."""
    return inspect.signature(func)


async def resolve_dependencies(
    func: Callable,
    request: Request,
    path_params: Dict[str, Any],
    injector: DependencyInjector,
    extra_dependencies: Optional[List[Dependency]] = None,
) -> Dict[str, Any]:
    """
    Convenience function to resolve dependencies.
    """
    return await injector.resolve_dependencies(
        func, request, path_params, extra_dependencies
    )


# Common dependency functions
async def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """
    Example dependency to get current user from request.
    This would typically check authentication tokens, sessions, etc.
    """
    # Check for Authorization header
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]
        # Here you would validate the token and return user info
        # For now, return a mock user
        return {"id": 1, "username": "user", "token": token}
    
    # Check for session
    session_id = request.cookies.get("session_id")
    if session_id:
        # Here you would validate the session and return user info
        return {"id": 1, "username": "user", "session": session_id}
    
    return None


async def get_database() -> Dict[str, Any]:
    """
    Example dependency to get database connection.
    This would typically return a real database connection.
    """
    # Mock database connection
    return {"type": "mock", "connected": True}


def require_auth(request: Request, user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Dependency that requires authentication.
    Raises HTTPException if user is not authenticated.
    """
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_admin(user: Dict[str, Any] = Depends(require_auth)) -> Dict[str, Any]:
    """
    Dependency that requires admin privileges.
    """
    if not user.get("is_admin", False):
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required"
        )
    return user


# Dependency decorators for Flask-style usage
def inject_dependencies(func: Callable) -> Callable:
    """
    Decorator to automatically inject dependencies into a function.
    This allows Flask-style functions to use dependency injection.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Find request object in args/kwargs
        request = None
        for arg in args:
            if isinstance(arg, Request):
                request = arg
                break
        
        if not request:
            request = kwargs.get('request')
        
        if not request:
            raise ValueError("Request object not found for dependency injection")
        
        # Create injector and resolve dependencies
        injector = DependencyInjector()
        resolved = await injector.resolve_dependencies(func, request, kwargs)
        
        # Merge resolved dependencies with existing kwargs
        kwargs.update(resolved)
        
        # Call the original function
        if is_async_callable(func):
            return await func(*args, **kwargs)
        else:
            return func(*args, **kwargs)
    
    return wrapper
