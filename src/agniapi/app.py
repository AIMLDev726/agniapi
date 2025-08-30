"""
Core application class for Agni API framework.
Combines Flask and FastAPI patterns with MCP support.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
from typing import Any, Callable, Dict, List, Optional, Sequence, Union

# Import key components from Flask and FastAPI patterns
from werkzeug.serving import run_simple
from werkzeug.wrappers import Response as WerkzeugResponse
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.responses import Response as StarletteResponse, JSONResponse as StarletteJSONResponse
from starlette.types import ASGIApp, Lifespan

from .routing import Router
from .request import Request
from .response import Response, JSONResponse
from .blueprints import Blueprint
from .middleware import MiddlewareStack
from .exceptions import HTTPException
from .dependencies import DependencyInjector
from .mcp import MCPServer, MCPClient
from .openapi import OpenAPIGenerator
from .security import SecurityManager
from .websockets import WebSocketManager
from .types import RouteHandler, is_async_callable, Scope, Receive, Send


class AgniAPI:
    """
    Main application class that combines Flask and FastAPI features.
    
    Supports both WSGI and ASGI protocols, sync and async handlers,
    with built-in MCP integration.
    """
    
    def __init__(
        self,
        *,
        title: str = "Agni API",
        description: str = "",
        version: str = "0.1.1",
        debug: bool = False,
        docs_url: Optional[str] = "/docs",
        redoc_url: Optional[str] = "/redoc",
        openapi_url: Optional[str] = "/openapi.json",
        static_folder: Optional[str] = "static",
        template_folder: Optional[str] = "templates",
        instance_relative_config: bool = False,
        root_path: str = "",
        middleware: Optional[Sequence[Middleware]] = None,
        lifespan: Optional[Lifespan] = None,
        mcp_enabled: bool = True,
        mcp_server_name: str = "agni-api-server",
    ):
        """
        Initialize the Agni API application.
        
        Args:
            title: API title for documentation
            description: API description
            version: API version
            debug: Enable debug mode
            docs_url: URL for Swagger UI docs (None to disable)
            redoc_url: URL for ReDoc docs (None to disable)
            openapi_url: URL for OpenAPI schema (None to disable)
            static_folder: Folder for static files
            template_folder: Folder for templates
            instance_relative_config: Enable instance relative config
            root_path: Root path for the application
            middleware: List of middleware
            lifespan: ASGI lifespan handler
            mcp_enabled: Enable MCP server functionality
            mcp_server_name: Name for the MCP server
        """
        self.title = title
        self.description = description
        self.version = version
        self.debug = debug
        self.docs_url = docs_url
        self.redoc_url = redoc_url
        self.openapi_url = openapi_url
        self.static_folder = static_folder
        self.template_folder = template_folder
        self.instance_relative_config = instance_relative_config
        self.root_path = root_path
        
        # Core components
        self.router = Router()
        self.middleware_stack = MiddlewareStack()
        self.dependency_injector = DependencyInjector()
        self.security_manager = SecurityManager()
        self.websocket_manager = WebSocketManager()
        
        # OpenAPI documentation
        self.openapi_generator = OpenAPIGenerator(
            title=title,
            description=description,
            version=version
        )
        
        # MCP integration
        self.mcp_enabled = mcp_enabled
        if mcp_enabled:
            self.mcp_server = MCPServer(name=mcp_server_name)
            self.mcp_client = MCPClient()
        
        # Blueprints registry
        self._blueprints: Dict[str, Blueprint] = {}

        # Event handlers
        self._startup_handlers: List[Callable] = []
        self._shutdown_handlers: List[Callable] = []

        # Configuration
        self.config: Dict[str, Any] = {}
        
        # Error handlers
        self._error_handlers: Dict[Union[int, type], Callable] = {}
        
        # Before/after request handlers
        self._before_request_handlers: List[Callable] = []
        self._after_request_handlers: List[Callable] = []
        
        # Initialize middleware
        if middleware:
            for mw in middleware:
                self.middleware_stack.add(mw)

        # Register OpenAPI documentation routes
        self._setup_openapi_routes()
        
        # ASGI app for async operations
        self._asgi_app = self._create_asgi_app(lifespan)
        
        # Setup default error handlers
        self._setup_default_error_handlers()
    
    def _create_asgi_app(self, lifespan: Optional[Lifespan] = None) -> Starlette:
        """Create the underlying ASGI application."""
        return Starlette(
            debug=self.debug,
            routes=[],
            middleware=[],
            lifespan=lifespan,
        )
    
    def _setup_default_error_handlers(self):
        """Setup default error handlers."""
        @self.exception_handler(HTTPException)
        async def http_exception_handler(request: Request, exc: HTTPException):
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail}
            )
        
        @self.exception_handler(404)
        async def not_found_handler(request: Request, exc):
            return JSONResponse(
                status_code=404,
                content={"detail": "Not Found"}
            )
        
        @self.exception_handler(500)
        async def internal_error_handler(request: Request, exc):
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal Server Error"}
            )
    
    # Flask-style routing decorators
    def route(
        self,
        path: str,
        *,
        methods: Optional[List[str]] = None,
        **kwargs
    ):
        """Flask-style route decorator."""
        def decorator(func: RouteHandler):
            self.router.add_route(path, func, methods=methods or ["GET"], **kwargs)
            return func
        return decorator
    
    def get(self, path: str, **kwargs):
        """FastAPI-style GET route decorator."""
        def decorator(func: RouteHandler):
            self.router.add_route(path, func, methods=["GET"], **kwargs)
            return func
        return decorator
    
    def post(self, path: str, **kwargs):
        """FastAPI-style POST route decorator."""
        def decorator(func: RouteHandler):
            self.router.add_route(path, func, methods=["POST"], **kwargs)
            return func
        return decorator
    
    def put(self, path: str, **kwargs):
        """FastAPI-style PUT route decorator."""
        def decorator(func: RouteHandler):
            self.router.add_route(path, func, methods=["PUT"], **kwargs)
            return func
        return decorator
    
    def delete(self, path: str, **kwargs):
        """FastAPI-style DELETE route decorator."""
        def decorator(func: RouteHandler):
            self.router.add_route(path, func, methods=["DELETE"], **kwargs)
            return func
        return decorator
    
    def patch(self, path: str, **kwargs):
        """FastAPI-style PATCH route decorator."""
        def decorator(func: RouteHandler):
            self.router.add_route(path, func, methods=["PATCH"], **kwargs)
            return func
        return decorator
    
    def websocket(self, path: str, **kwargs):
        """WebSocket route decorator."""
        def decorator(func: RouteHandler):
            self.websocket_manager.add_route(path, func, **kwargs)
            return func
        return decorator

    # MCP decorators
    def mcp_tool(self, name: str, description: str = ""):
        """Register a function as an MCP tool."""
        def decorator(func: RouteHandler):
            if self.mcp_enabled:
                self.mcp_server.register_tool(name, func, description)
            return func
        return decorator

    def mcp_resource(self, uri: str, name: str = "", description: str = ""):
        """Register a function as an MCP resource."""
        def decorator(func: RouteHandler):
            if self.mcp_enabled:
                self.mcp_server.register_resource(uri, func, name, description)
            return func
        return decorator

    # Blueprint registration
    def register_blueprint(self, blueprint: Blueprint, **options):
        """Register a Flask-style blueprint."""
        blueprint.register(self, **options)
        self._blueprints[blueprint.name] = blueprint

    # Middleware management
    def add_middleware(self, middleware_class: type, **kwargs):
        """Add middleware to the application."""
        self.middleware_stack.add(middleware_class, **kwargs)

    # Error handlers
    def exception_handler(self, exc_class_or_status_code: Union[int, type]):
        """Register an exception handler."""
        def decorator(func: Callable):
            self._error_handlers[exc_class_or_status_code] = func
            return func
        return decorator

    def errorhandler(self, code_or_exception: Union[int, type]):
        """Flask-style error handler decorator."""
        return self.exception_handler(code_or_exception)

    # Request lifecycle hooks
    def before_request(self, func: Callable):
        """Register a before request handler."""
        self._before_request_handlers.append(func)
        return func

    def after_request(self, func: Callable):
        """Register an after request handler."""
        self._after_request_handlers.append(func)
        return func

    def on_event(self, event_type: str):
        """Event handler decorator for startup and shutdown events."""
        def decorator(func: Callable):
            if event_type == "startup":
                self._startup_handlers.append(func)
            elif event_type == "shutdown":
                self._shutdown_handlers.append(func)
            else:
                raise ValueError(f"Unknown event type: {event_type}")
            return func
        return decorator

    async def _run_startup_handlers(self):
        """Run all startup event handlers."""
        for handler in self._startup_handlers:
            if inspect.iscoroutinefunction(handler):
                await handler()
            else:
                handler()

    async def _run_shutdown_handlers(self):
        """Run all shutdown event handlers."""
        for handler in self._shutdown_handlers:
            if inspect.iscoroutinefunction(handler):
                await handler()
            else:
                handler()

    def _setup_openapi_routes(self):
        """Setup OpenAPI documentation routes."""
        from .response import JSONResponse, HTMLResponse

        # OpenAPI JSON schema endpoint
        if self.openapi_url:
            @self.get(self.openapi_url)
            async def openapi_schema():
                """Get OpenAPI schema."""
                return JSONResponse(content=self.openapi_generator.generate_openapi(self.router))

        # Swagger UI documentation
        if self.docs_url:
            @self.get(self.docs_url)
            async def swagger_ui():
                """Swagger UI documentation."""
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>{self.title} - Swagger UI</title>
                    <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui.css" />
                    <style>
                        html {{ box-sizing: border-box; overflow: -moz-scrollbars-vertical; overflow-y: scroll; }}
                        *, *:before, *:after {{ box-sizing: inherit; }}
                        body {{ margin:0; background: #fafafa; }}
                    </style>
                </head>
                <body>
                    <div id="swagger-ui"></div>
                    <script src="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui-bundle.js"></script>
                    <script src="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui-standalone-preset.js"></script>
                    <script>
                        window.onload = function() {{
                            const ui = SwaggerUIBundle({{
                                url: '{self.openapi_url or "/openapi.json"}',
                                dom_id: '#swagger-ui',
                                deepLinking: true,
                                presets: [
                                    SwaggerUIBundle.presets.apis,
                                    SwaggerUIStandalonePreset
                                ],
                                plugins: [
                                    SwaggerUIBundle.plugins.DownloadUrl
                                ],
                                layout: "StandaloneLayout"
                            }});
                        }};
                    </script>
                </body>
                </html>
                """
                return HTMLResponse(content=html_content)

        # ReDoc documentation
        if self.redoc_url:
            @self.get(self.redoc_url)
            async def redoc():
                """ReDoc documentation."""
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>{self.title} - ReDoc</title>
                    <meta charset="utf-8"/>
                    <meta name="viewport" content="width=device-width, initial-scale=1">
                    <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
                    <style>
                        body {{ margin: 0; padding: 0; }}
                    </style>
                </head>
                <body>
                    <redoc spec-url='{self.openapi_url or "/openapi.json"}'></redoc>
                    <script src="https://cdn.jsdelivr.net/npm/redoc@2.0.0/bundles/redoc.standalone.js"></script>
                </body>
                </html>
                """
                return HTMLResponse(content=html_content)

    # ASGI interface
    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        """ASGI application interface."""
        if scope["type"] == "http":
            await self._handle_http_request(scope, receive, send)
        elif scope["type"] == "websocket":
            await self._handle_websocket_request(scope, receive, send)
        else:
            await self._asgi_app(scope, receive, send)

    async def _handle_http_request(self, scope: Scope, receive: Receive, send: Send):
        """Handle HTTP requests using our router."""
        request = None
        try:
            # Create Request object from ASGI scope
            request = Request(scope, receive, send)

            # Extract path and method from scope
            path = scope["path"]
            method = scope["method"]

            # Run before request handlers
            for handler in self._before_request_handlers:
                if is_async_callable(handler):
                    await handler(request)
                else:
                    handler(request)

            # Find matching route
            route_handler, path_params = self.router.match(path, method)

            if route_handler:
                # Get the route object for additional metadata
                route = None
                for r in self.router.routes:
                    if r.handler == route_handler:
                        route = r
                        break

                # Resolve dependencies for the handler
                try:
                    resolved_params = await self.dependency_injector.resolve_dependencies(
                        route_handler,
                        request,
                        path_params,
                        route.dependencies if route else None
                    )
                except Exception as dep_error:
                    # Handle dependency resolution errors
                    if isinstance(dep_error, HTTPException):
                        raise dep_error
                    else:
                        raise HTTPException(
                            status_code=500,
                            detail=f"Dependency resolution failed: {str(dep_error)}"
                        )

                # Execute handler with resolved dependencies
                if is_async_callable(route_handler):
                    result = await route_handler(**resolved_params)
                else:
                    result = route_handler(**resolved_params)

                # Extract background tasks if present
                background_tasks = None
                if 'background_tasks' in resolved_params:
                    from .types import BackgroundTasks
                    background_tasks = resolved_params['background_tasks']
                    if isinstance(background_tasks, BackgroundTasks):
                        # Remove from resolved params so it doesn't interfere with response
                        pass

                # Convert result to response
                response = self._convert_to_starlette_response(result, route.status_code)

                # Run after request handlers
                for handler in self._after_request_handlers:
                    if is_async_callable(handler):
                        await handler(request, response)
                    else:
                        handler(request, response)

                # Send response
                await response(scope, receive, send)

                # Execute background tasks after response is sent
                if background_tasks and hasattr(background_tasks, 'tasks') and background_tasks.tasks:
                    try:
                        await background_tasks.execute_all()
                    except Exception as bg_error:
                        # Log background task errors but don't affect the response
                        logging.error(f"Background task execution failed: {bg_error}")
            else:
                # 404 Not Found - use error handler if available
                error_handler = self._error_handlers.get(404)
                if error_handler:
                    try:
                        if is_async_callable(error_handler):
                            result = await error_handler(request, HTTPException(404, "Not Found"))
                        else:
                            result = error_handler(request, HTTPException(404, "Not Found"))

                        # Ensure result is not a coroutine
                        if inspect.iscoroutine(result):
                            result = await result

                        response = self._convert_to_starlette_response(result, 404)
                    except Exception as handler_error:
                        # Fallback if error handler fails
                        logging.error(f"404 error handler failed: {handler_error}")
                        response = StarletteJSONResponse({"detail": "Not Found"}, status_code=404)
                else:
                    response = StarletteJSONResponse({"detail": "Not Found"}, status_code=404)

                await response(scope, receive, send)

        except HTTPException as http_exc:
            # Handle HTTP exceptions
            error_handler = self._error_handlers.get(http_exc.status_code) or self._error_handlers.get(HTTPException)
            if error_handler:
                try:
                    if is_async_callable(error_handler):
                        result = await error_handler(request, http_exc)
                    else:
                        result = error_handler(request, http_exc)

                    # Ensure result is not a coroutine
                    if inspect.iscoroutine(result):
                        result = await result

                    response = self._convert_to_starlette_response(result, http_exc.status_code)
                except Exception as handler_error:
                    # Fallback if error handler fails
                    logging.error(f"HTTP error handler failed: {handler_error}")
                    response = StarletteJSONResponse(
                        {"detail": http_exc.detail},
                        status_code=http_exc.status_code,
                        headers=http_exc.headers
                    )
            else:
                response = StarletteJSONResponse(
                    {"detail": http_exc.detail},
                    status_code=http_exc.status_code,
                    headers=http_exc.headers
                )

            await response(scope, receive, send)

        except Exception as e:
            # Handle general exceptions
            error_handler = self._error_handlers.get(500) or self._error_handlers.get(Exception)
            if error_handler:
                try:
                    if is_async_callable(error_handler):
                        result = await error_handler(request, e)
                    else:
                        result = error_handler(request, e)

                    # Ensure result is not a coroutine
                    if inspect.iscoroutine(result):
                        result = await result

                    response = self._convert_to_starlette_response(result, 500)
                except Exception as handler_error:
                    # Fallback if error handler fails
                    logging.error(f"Error handler failed: {handler_error}")
                    response = StarletteJSONResponse({"detail": "Internal Server Error"}, status_code=500)
            else:
                response = StarletteJSONResponse({"detail": "Internal Server Error"}, status_code=500)

            await response(scope, receive, send)

        finally:
            # Clean up dependency cache for this request
            if request:
                self.dependency_injector.clear_cache(request)

    def _convert_to_starlette_response(self, result: Any, status_code: int = None) -> StarletteResponse:
        """Convert various result types to Starlette Response objects."""
        if isinstance(result, StarletteResponse):
            return result
        elif isinstance(result, Response):
            # Convert our Response to Starlette Response
            if isinstance(result.content, dict):
                return StarletteJSONResponse(
                    result.content,
                    status_code=result.status_code,
                    headers=result.headers
                )
            else:
                return StarletteResponse(
                    str(result.content),
                    status_code=result.status_code,
                    headers=result.headers
                )
        elif isinstance(result, dict):
            return StarletteJSONResponse(result, status_code=status_code or 200)
        else:
            return StarletteResponse(str(result), status_code=status_code or 200)

    async def _handle_websocket_request(self, scope: Scope, receive: Receive, send: Send):
        """Handle WebSocket requests."""
        # For now, delegate to the underlying ASGI app
        await self._asgi_app(scope, receive, send)

    # WSGI interface
    def wsgi_app(self, environ, start_response):
        """WSGI application interface for compatibility."""
        # Convert WSGI to ASGI and handle synchronously
        # This is a simplified implementation
        from werkzeug.wrappers import Request as WerkzeugRequest

        request = WerkzeugRequest(environ)

        # Find matching route
        handler, params = self.router.match(request.path, request.method)

        if handler:
            try:
                # Execute handler
                if inspect.iscoroutinefunction(handler):
                    # Run async handler in event loop (safely handle existing loop)
                    try:
                        # Try to get existing event loop
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            # If loop is running, we can't use run_until_complete
                            # This is a limitation of WSGI with async handlers
                            raise RuntimeError("Cannot run async handler in WSGI context with running event loop")
                        result = loop.run_until_complete(handler(request, **params))
                    except RuntimeError:
                        # No event loop exists, create a new one
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            result = loop.run_until_complete(handler(request, **params))
                        finally:
                            loop.close()
                            asyncio.set_event_loop(None)
                else:
                    result = handler(request, **params)

                # Convert result to WSGI response
                if isinstance(result, (WerkzeugResponse, StarletteResponse)):
                    response = result
                else:
                    response = WerkzeugResponse(str(result))

                return response(environ, start_response)

            except Exception as e:
                # Handle errors
                error_handler = self._error_handlers.get(type(e)) or self._error_handlers.get(500)
                if error_handler:
                    result = error_handler(request, e)
                    response = WerkzeugResponse(str(result))
                else:
                    response = WerkzeugResponse("Internal Server Error", status=500)

                return response(environ, start_response)

        # 404 Not Found
        response = WerkzeugResponse("Not Found", status=404)
        return response(environ, start_response)

    # Development server
    def run(
        self,
        host: str = "127.0.0.1",
        port: int = 5000,
        debug: Optional[bool] = None,
        use_reloader: bool = True,
        use_debugger: bool = True,
        **kwargs
    ):
        """Run the development server (Flask-style)."""
        if debug is not None:
            self.debug = debug

        # Use Werkzeug development server for WSGI compatibility
        run_simple(
            host,
            port,
            self.wsgi_app,
            use_reloader=use_reloader,
            use_debugger=use_debugger,
            **kwargs
        )

    def run_async(
        self,
        host: str = "127.0.0.1",
        port: int = 8000,
        **kwargs
    ):
        """Run the async server (FastAPI-style)."""
        import uvicorn
        uvicorn.run(self, host=host, port=port, **kwargs)

    # Configuration
    def config_from_object(self, obj):
        """Load configuration from an object."""
        if isinstance(obj, str):
            obj = __import__(obj, fromlist=[''])

        for key in dir(obj):
            if key.isupper():
                self.config[key] = getattr(obj, key)

    def config_from_file(self, filename: str):
        """Load configuration from a file."""
        import json
        with open(filename) as f:
            config = json.load(f)
            self.config.update(config)
