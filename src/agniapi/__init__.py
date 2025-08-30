"""
Agni API - A unified REST API framework combining Flask and FastAPI features with built-in MCP support.

This framework provides:
- Flask-style blueprints and routing
- FastAPI-style async support and type hints
- Built-in Model Context Protocol (MCP) integration
- Automatic OpenAPI documentation
- Dependency injection system
- WebSocket support
- Security features (OAuth2, JWT, API keys)
- High performance async/sync request handling
"""

from __future__ import annotations

__version__ = "0.1.1"
__author__ = "Agni API Team"
__license__ = "MIT"

# Core imports
from .app import AgniAPI
from .routing import Router
from .request import Request
from .response import Response, JSONResponse, HTMLResponse
from .blueprints import Blueprint
from .dependencies import Depends
from .security import HTTPBasic, HTTPBearer, OAuth2PasswordBearer
from .exceptions import HTTPException, ValidationError
from .middleware import Middleware
from .websockets import WebSocket

# MCP imports
from .mcp import MCPServer, MCPClient, mcp_tool, mcp_resource, mcp_prompt

# Testing imports
from .testing import TestClient

# Type imports
from .types import ASGIApp, WSGIApp, BackgroundTasks

# Forms and file uploads
from .forms import Form, UploadFile, FormData

# Caching system
from .cache import Cache, MemoryCache, RedisCache, FileCache, cache, configure_cache

# Database integration
from .database import Database, Model, Base, configure_database, get_database, MigrationManager

# Rate limiting
from .limiter import RateLimiter, RateLimit, RateLimitExceeded, limiter, configure_limiter

# Session management
from .sessions import Session, SessionInterface, SecureCookieSessionInterface, RedisSessionInterface, SessionMiddleware, configure_sessions

# Configuration management
from .config import Config, ConfigError, load_config, DatabaseConfig, RedisConfig, SessionConfig, Environment

# Content negotiation
from .content_negotiation import ContentNegotiator, MediaType, ContentHandler, JSONHandler, XMLHandler, CSVHandler, HTMLHandler, negotiate_content

# Monitoring and metrics
from .monitoring import MetricsRegistry, HealthChecker, StructuredLogger, MetricsMiddleware, LoggingMiddleware, get_metrics_response, get_health_response, monitor_function

# Streaming responses
from .streaming import StreamingResponse, SSEResponse, FileStreamingResponse, ServerSentEvent, stream_file, stream_response, sse_response, create_sse_event

# Static files and templating
from .static import StaticFiles, send_file, send_from_directory
from .templating import render_template, render_template_string

__all__ = [
    # Core classes
    "AgniAPI",
    "Router", 
    "Request",
    "Response",
    "JSONResponse", 
    "HTMLResponse",
    "Blueprint",
    "WebSocket",
    
    # Dependencies and security
    "Depends",
    "HTTPBasic",
    "HTTPBearer", 
    "OAuth2PasswordBearer",
    
    # Exceptions
    "HTTPException",
    "ValidationError",
    
    # Middleware
    "Middleware",
    
    # MCP
    "MCPServer",
    "MCPClient",
    "mcp_tool",
    "mcp_resource",
    "mcp_prompt",
    
    # Testing
    "TestClient",
    
    # Types
    "ASGIApp",
    "WSGIApp",
    "BackgroundTasks",

    # Forms and file uploads
    "Form",
    "UploadFile",
    "FormData",

    # Caching system
    "Cache",
    "MemoryCache",
    "RedisCache",
    "FileCache",
    "cache",
    "configure_cache",

    # Database integration
    "Database",
    "Model",
    "Base",
    "configure_database",
    "get_database",
    "MigrationManager",

    # Rate limiting
    "RateLimiter",
    "RateLimit",
    "RateLimitExceeded",
    "limiter",
    "configure_limiter",

    # Session management
    "Session",
    "SessionInterface",
    "SecureCookieSessionInterface",
    "RedisSessionInterface",
    "SessionMiddleware",
    "configure_sessions",

    # Configuration management
    "Config",
    "ConfigError",
    "load_config",
    "DatabaseConfig",
    "RedisConfig",
    "SessionConfig",
    "Environment",

    # Content negotiation
    "ContentNegotiator",
    "MediaType",
    "ContentHandler",
    "JSONHandler",
    "XMLHandler",
    "CSVHandler",
    "HTMLHandler",
    "negotiate_content",

    # Monitoring and metrics
    "MetricsRegistry",
    "HealthChecker",
    "StructuredLogger",
    "MetricsMiddleware",
    "LoggingMiddleware",
    "get_metrics_response",
    "get_health_response",
    "monitor_function",

    # Streaming responses
    "StreamingResponse",
    "SSEResponse",
    "FileStreamingResponse",
    "ServerSentEvent",
    "stream_file",
    "stream_response",
    "sse_response",
    "create_sse_event",

    # Static files and templating
    "StaticFiles",
    "send_file",
    "send_from_directory",
    "render_template",
    "render_template_string",
]
