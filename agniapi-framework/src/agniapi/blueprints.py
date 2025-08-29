"""
Blueprint system for Agni API framework.
Based on Flask blueprints with async support and FastAPI features.
"""

from __future__ import annotations

import os
from typing import Any, Callable, Dict, List, Optional, Union

from .routing import Route, Router
from .types import RouteHandler, MiddlewareType, ErrorHandler
from .exceptions import HTTPException
from .dependencies import Dependency


class Blueprint:
    """
    Blueprint for organizing routes and functionality.
    Compatible with Flask blueprints but with async support.
    """
    
    def __init__(
        self,
        name: str,
        import_name: str,
        *,
        url_prefix: Optional[str] = None,
        subdomain: Optional[str] = None,
        url_defaults: Optional[Dict[str, Any]] = None,
        static_folder: Optional[str] = None,
        static_url_path: Optional[str] = None,
        template_folder: Optional[str] = None,
        root_path: Optional[str] = None,
        tags: Optional[List[str]] = None,
        dependencies: Optional[List[Dependency]] = None,
        responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
    ):
        """
        Initialize a blueprint.
        
        Args:
            name: Blueprint name
            import_name: Import name (usually __name__)
            url_prefix: URL prefix for all routes
            subdomain: Subdomain for routes
            url_defaults: Default values for URL variables
            static_folder: Folder for static files
            static_url_path: URL path for static files
            template_folder: Folder for templates
            root_path: Root path for the blueprint
            tags: OpenAPI tags for all routes
            dependencies: Global dependencies for all routes
            responses: Global response definitions
        """
        self.name = name
        self.import_name = import_name
        self.url_prefix = url_prefix
        self.subdomain = subdomain
        self.url_defaults = url_defaults or {}
        self.static_folder = static_folder
        self.static_url_path = static_url_path
        self.template_folder = template_folder
        self.root_path = root_path
        self.tags = tags or []
        self.dependencies = dependencies or []
        self.responses = responses or {}
        
        # Internal storage
        self._deferred_functions: List[Callable] = []
        self.router = Router()
        self._error_handlers: Dict[Union[int, type], ErrorHandler] = {}
        self._before_request_handlers: List[Callable] = []
        self._after_request_handlers: List[Callable] = []
        self._middleware: List[MiddlewareType] = []
        
        # Track if blueprint is registered
        self._registered = False
    
    def route(
        self,
        rule: str,
        *,
        methods: Optional[List[str]] = None,
        endpoint: Optional[str] = None,
        **options
    ):
        """Register a route (Flask-style)."""
        def decorator(func: RouteHandler):
            self.add_url_rule(rule, endpoint, func, methods=methods, **options)
            return func
        return decorator
    
    def get(self, path: str, **kwargs):
        """FastAPI-style GET route."""
        def decorator(func: RouteHandler):
            self.add_url_rule(path, None, func, methods=["GET"], **kwargs)
            return func
        return decorator
    
    def post(self, path: str, **kwargs):
        """FastAPI-style POST route."""
        def decorator(func: RouteHandler):
            self.add_url_rule(path, None, func, methods=["POST"], **kwargs)
            return func
        return decorator
    
    def put(self, path: str, **kwargs):
        """FastAPI-style PUT route."""
        def decorator(func: RouteHandler):
            self.add_url_rule(path, None, func, methods=["PUT"], **kwargs)
            return func
        return decorator
    
    def delete(self, path: str, **kwargs):
        """FastAPI-style DELETE route."""
        def decorator(func: RouteHandler):
            self.add_url_rule(path, None, func, methods=["DELETE"], **kwargs)
            return func
        return decorator
    
    def patch(self, path: str, **kwargs):
        """FastAPI-style PATCH route."""
        def decorator(func: RouteHandler):
            self.add_url_rule(path, None, func, methods=["PATCH"], **kwargs)
            return func
        return decorator
    
    def add_url_rule(
        self,
        rule: str,
        endpoint: Optional[str] = None,
        view_func: Optional[RouteHandler] = None,
        *,
        methods: Optional[List[str]] = None,
        **options
    ):
        """Add a URL rule to the blueprint."""
        if endpoint is None:
            endpoint = view_func.__name__ if view_func else None
        
        if methods is None:
            methods = ["GET"]
        
        # Merge blueprint tags and dependencies
        route_tags = options.get('tags', [])
        options['tags'] = self.tags + route_tags
        
        route_dependencies = options.get('dependencies', [])
        options['dependencies'] = self.dependencies + route_dependencies
        
        # Store the rule for later registration
        def register_rule(app):
            # Apply URL prefix
            full_rule = rule
            if self.url_prefix:
                full_rule = self.url_prefix.rstrip('/') + '/' + rule.lstrip('/')
            
            # Create endpoint name with blueprint prefix
            full_endpoint = f"{self.name}.{endpoint}" if endpoint else None
            
            app.router.add_route(
                full_rule,
                view_func,
                methods=methods,
                name=full_endpoint,
                **options
            )
        
        self._deferred_functions.append(register_rule)
    
    def errorhandler(self, code_or_exception: Union[int, type]):
        """Register an error handler."""
        def decorator(func: ErrorHandler):
            self._error_handlers[code_or_exception] = func
            return func
        return decorator
    
    def before_request(self, func: Callable):
        """Register a before request handler."""
        self._before_request_handlers.append(func)
        return func
    
    def after_request(self, func: Callable):
        """Register an after request handler."""
        self._after_request_handlers.append(func)
        return func
    
    def middleware(self, middleware_class: type):
        """Register middleware for this blueprint."""
        def decorator(func):
            self._middleware.append(middleware_class)
            return func
        return decorator
    
    def include_router(self, router, *, prefix: str = "", tags: Optional[List[str]] = None):
        """Include a FastAPI-style router."""
        def register_router(app):
            # Apply blueprint prefix to router prefix
            full_prefix = ""
            if self.url_prefix:
                full_prefix += self.url_prefix.rstrip('/')
            if prefix:
                full_prefix += '/' + prefix.strip('/')
            
            # Merge tags
            router_tags = tags or []
            merged_tags = self.tags + router_tags
            
            # Register all routes from the router
            for route in router.routes:
                full_path = full_prefix + route.path
                route_tags = route.tags + merged_tags
                
                app.router.add_route(
                    full_path,
                    route.handler,
                    methods=route.methods,
                    name=f"{self.name}.{route.name}",
                    tags=route_tags,
                    dependencies=self.dependencies + route.dependencies,
                    response_model=route.response_model,
                    status_code=route.status_code,
                    summary=route.summary,
                    description=route.description,
                    **route.kwargs
                )
        
        self._deferred_functions.append(register_router)
    
    def register(self, app, options: Optional[Dict[str, Any]] = None):
        """Register the blueprint with an application."""
        if self._registered:
            raise RuntimeError(f"Blueprint '{self.name}' is already registered")
        
        options = options or {}
        
        # Apply options
        if 'url_prefix' in options:
            self.url_prefix = options['url_prefix']
        if 'subdomain' in options:
            self.subdomain = options['subdomain']
        
        # Register all deferred functions
        for func in self._deferred_functions:
            func(app)
        
        # Register error handlers
        for code_or_exception, handler in self._error_handlers.items():
            app._error_handlers[code_or_exception] = handler
        
        # Register before/after request handlers
        app._before_request_handlers.extend(self._before_request_handlers)
        app._after_request_handlers.extend(self._after_request_handlers)
        
        # Register middleware
        for middleware in self._middleware:
            app.add_middleware(middleware)
        
        self._registered = True
    
    def send_static_file(self, filename: str):
        """Send a static file from the blueprint's static folder."""
        if not self.static_folder:
            raise RuntimeError("No static folder configured for blueprint")
        
        # This would typically use send_from_directory
        # For now, return a placeholder
        return f"Static file: {filename} from {self.static_folder}"
    
    def open_resource(self, resource: str, mode: str = 'rb'):
        """Open a resource file relative to the blueprint."""
        if self.root_path:
            return open(os.path.join(self.root_path, resource), mode)
        else:
            # Use import_name to find the package
            import importlib.util
            spec = importlib.util.find_spec(self.import_name)
            if spec and spec.origin:
                package_dir = os.path.dirname(spec.origin)
                return open(os.path.join(package_dir, resource), mode)
            else:
                raise FileNotFoundError(f"Cannot locate resource: {resource}")
    
    def get_send_file_max_age(self, filename: Optional[str]) -> Optional[int]:
        """Get the max age for sending files."""
        # Default implementation
        return None
    
    def __repr__(self):
        return f"<Blueprint '{self.name}'>"


class BlueprintSetupState:
    """
    State object for blueprint registration.
    Tracks the state during blueprint registration process.
    """
    
    def __init__(
        self,
        blueprint: Blueprint,
        app,
        options: Dict[str, Any],
        first_registration: bool,
    ):
        self.blueprint = blueprint
        self.app = app
        self.options = options
        self.first_registration = first_registration
        
        # Computed properties
        self.url_prefix = options.get('url_prefix', blueprint.url_prefix)
        self.subdomain = options.get('subdomain', blueprint.subdomain)
        self.url_defaults = dict(blueprint.url_defaults)
        self.url_defaults.update(options.get('url_defaults', {}))
    
    def add_url_rule(
        self,
        rule: str,
        endpoint: Optional[str] = None,
        view_func: Optional[RouteHandler] = None,
        **options
    ):
        """Add a URL rule during blueprint registration."""
        if self.url_prefix:
            rule = self.url_prefix.rstrip('/') + '/' + rule.lstrip('/')
        
        if endpoint:
            endpoint = f"{self.blueprint.name}.{endpoint}"
        
        self.app.router.add_route(rule, view_func, **options)
