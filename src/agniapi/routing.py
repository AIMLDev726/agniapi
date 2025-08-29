"""
Routing system for Agni API framework.
Combines Flask and FastAPI routing patterns with type validation.
"""

from __future__ import annotations

import inspect
import re
from typing import Any, Callable, Dict, List, Optional, Pattern, Tuple, Union
from urllib.parse import unquote

from .types import RouteHandler
from .dependencies import get_typed_signature, resolve_dependencies
from .exceptions import HTTPException


class Route:
    """Represents a single route in the application."""
    
    def __init__(
        self,
        path: str,
        handler: RouteHandler,
        methods: List[str],
        name: Optional[str] = None,
        dependencies: Optional[List[Any]] = None,
        response_model: Optional[type] = None,
        status_code: int = 200,
        tags: Optional[List[str]] = None,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        **kwargs
    ):
        self.path = path
        self.handler = handler
        self.methods = [method.upper() for method in methods]
        self.name = name or handler.__name__
        self.dependencies = dependencies or []
        self.response_model = response_model
        self.status_code = status_code
        self.tags = tags or []
        self.summary = summary
        self.description = description
        self.kwargs = kwargs
        
        # Compile path pattern for matching
        self.path_pattern, self.param_names = self._compile_path(path)
        
        # Get function signature for type validation
        self.signature = get_typed_signature(handler)
    
    def _compile_path(self, path: str) -> Tuple[Pattern[str], List[str]]:
        """
        Compile path pattern for matching.
        Supports both Flask-style <param> and FastAPI-style {param} syntax.
        """
        param_names = []
        
        # Convert FastAPI-style {param} to Flask-style <param>
        path = re.sub(r'\{([^}]+)\}', r'<\1>', path)
        
        # Find all parameters
        param_pattern = re.compile(r'<([^>]+)>')
        
        def replace_param(match):
            param_spec = match.group(1)
            if ':' in param_spec:
                param_type, param_name = param_spec.split(':', 1)
            else:
                param_type = 'string'
                param_name = param_spec
            
            param_names.append(param_name)
            
            # Type-specific patterns
            if param_type in ('int', 'integer'):
                return r'(\d+)'
            elif param_type == 'float':
                return r'(\d+\.?\d*)'
            elif param_type == 'path':
                return r'([^/]+(?:/[^/]+)*)'
            elif param_type == 'uuid':
                return r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})'
            else:  # string
                return r'([^/]+)'
        
        # Replace parameters with regex groups
        pattern_str = param_pattern.sub(replace_param, path)
        
        # Escape other regex characters and anchor the pattern
        pattern_str = '^' + pattern_str + '$'
        
        return re.compile(pattern_str), param_names
    
    def match(self, path: str) -> Optional[Dict[str, Any]]:
        """Check if this route matches the given path."""
        match = self.path_pattern.match(path)
        if match:
            # Extract parameters
            params = {}
            for i, name in enumerate(self.param_names):
                value = unquote(match.group(i + 1))
                # Store raw value - type conversion will be handled by dependency injection
                params[name] = value
            return params
        return None


class Router:
    """Main routing system that manages all routes."""
    
    def __init__(self):
        self.routes: List[Route] = []
        self._route_map: Dict[str, List[Route]] = {}
    
    def add_route(
        self,
        path: str,
        handler: RouteHandler,
        methods: Optional[List[str]] = None,
        **kwargs
    ):
        """Add a new route to the router."""
        if methods is None:
            methods = ["GET"]
        
        route = Route(path, handler, methods, **kwargs)
        self.routes.append(route)
        
        # Index by method for faster lookup
        for method in route.methods:
            if method not in self._route_map:
                self._route_map[method] = []
            self._route_map[method].append(route)
    
    def match(self, path: str, method: str) -> Tuple[Optional[RouteHandler], Dict[str, Any]]:
        """
        Find a matching route for the given path and method.
        Returns (handler, params) or (None, {}) if no match.
        """
        method = method.upper()
        
        if method not in self._route_map:
            return None, {}
        
        for route in self._route_map[method]:
            params = route.match(path)
            if params is not None:
                return route.handler, params
        
        return None, {}
    
    def get_route_by_name(self, name: str) -> Optional[Route]:
        """Get a route by its name."""
        for route in self.routes:
            if route.name == name:
                return route
        return None
    
    def url_for(self, name: str, **params) -> str:
        """
        Generate URL for a named route with parameters.
        Similar to Flask's url_for function.
        """
        route = self.get_route_by_name(name)
        if not route:
            raise ValueError(f"No route found with name '{name}'")
        
        url = route.path
        
        # Replace parameters in the URL
        for param_name, param_value in params.items():
            # Handle both Flask and FastAPI style parameters
            flask_pattern = f'<{param_name}>'
            fastapi_pattern = f'{{{param_name}}}'
            
            if flask_pattern in url:
                url = url.replace(flask_pattern, str(param_value))
            elif fastapi_pattern in url:
                url = url.replace(fastapi_pattern, str(param_value))
        
        return url
    
    def get_routes_for_path(self, path: str) -> List[Route]:
        """Get all routes that match a given path pattern."""
        matching_routes = []
        for route in self.routes:
            if route.match(path) is not None:
                matching_routes.append(route)
        return matching_routes
    
    def get_all_routes(self) -> List[Route]:
        """Get all registered routes."""
        return self.routes.copy()
    
    def remove_route(self, name: str) -> bool:
        """Remove a route by name. Returns True if removed, False if not found."""
        for i, route in enumerate(self.routes):
            if route.name == name:
                # Remove from main list
                removed_route = self.routes.pop(i)
                
                # Remove from method map
                for method in removed_route.methods:
                    if method in self._route_map:
                        try:
                            self._route_map[method].remove(removed_route)
                        except ValueError:
                            pass
                
                return True
        return False
    
    def clear_routes(self):
        """Clear all routes."""
        self.routes.clear()
        self._route_map.clear()


class APIRouter(Router):
    """
    FastAPI-style router for grouping related routes.
    Can be included in the main application.
    """
    
    def __init__(
        self,
        prefix: str = "",
        tags: Optional[List[str]] = None,
        dependencies: Optional[List[Any]] = None,
        responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
    ):
        super().__init__()
        self.prefix = prefix.rstrip('/')
        self.tags = tags or []
        self.dependencies = dependencies or []
        self.responses = responses or {}
    
    def add_route(self, path: str, handler: RouteHandler, methods: Optional[List[str]] = None, **kwargs):
        """Add route with prefix applied."""
        # Apply prefix to path
        full_path = self.prefix + path
        
        # Merge tags and dependencies
        route_tags = kwargs.get('tags', [])
        kwargs['tags'] = self.tags + route_tags
        
        route_dependencies = kwargs.get('dependencies', [])
        kwargs['dependencies'] = self.dependencies + route_dependencies
        
        super().add_route(full_path, handler, methods, **kwargs)
    
    def include_router(self, router: 'APIRouter', prefix: str = ""):
        """Include another router in this router."""
        combined_prefix = self.prefix + prefix.rstrip('/')
        
        for route in router.routes:
            # Create new route with combined prefix
            new_path = combined_prefix + route.path[len(router.prefix):]
            self.add_route(
                new_path,
                route.handler,
                route.methods,
                name=route.name,
                dependencies=route.dependencies,
                response_model=route.response_model,
                status_code=route.status_code,
                tags=route.tags,
                summary=route.summary,
                description=route.description,
                **route.kwargs
            )
