"""
Exception handling for Agni API framework.
Combines Flask and FastAPI exception patterns.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from http import HTTPStatus


class AgniAPIException(Exception):
    """Base exception for all Agni API framework exceptions."""
    pass


class HTTPException(AgniAPIException):
    """
    HTTP exception that can be raised to return an HTTP error response.
    Compatible with both Flask and FastAPI patterns.
    """
    
    def __init__(
        self,
        status_code: int,
        detail: Any = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        self.status_code = status_code
        self.detail = detail or HTTPStatus(status_code).phrase
        self.headers = headers or {}
        
        super().__init__(self.detail)
    
    def __repr__(self):
        return f"HTTPException(status_code={self.status_code}, detail={self.detail!r})"


class ValidationError(AgniAPIException):
    """
    Validation error for request data.
    Similar to FastAPI's RequestValidationError.
    """
    
    def __init__(
        self,
        errors: List[Dict[str, Any]],
        body: Any = None,
    ):
        self.errors = errors
        self.body = body
        
        # Create a readable error message
        error_messages = []
        for error in errors:
            loc = " -> ".join(str(x) for x in error.get("loc", []))
            msg = error.get("msg", "Validation error")
            error_messages.append(f"{loc}: {msg}")
        
        detail = "; ".join(error_messages)
        super().__init__(detail)
    
    def __repr__(self):
        return f"ValidationError(errors={self.errors!r})"


class WebSocketException(AgniAPIException):
    """Exception for WebSocket-related errors."""
    
    def __init__(
        self,
        code: int = 1000,
        reason: Optional[str] = None,
    ):
        self.code = code
        self.reason = reason or "WebSocket error"
        super().__init__(self.reason)


class DependencyException(AgniAPIException):
    """Exception raised when dependency injection fails."""
    
    def __init__(
        self,
        dependency_name: str,
        detail: str,
    ):
        self.dependency_name = dependency_name
        self.detail = detail
        super().__init__(f"Dependency '{dependency_name}': {detail}")


class ConfigurationError(AgniAPIException):
    """Exception raised for configuration-related errors."""
    pass


class SecurityException(AgniAPIException):
    """Exception raised for security-related errors."""
    
    def __init__(
        self,
        detail: str,
        scheme_name: Optional[str] = None,
    ):
        self.detail = detail
        self.scheme_name = scheme_name
        super().__init__(detail)


class MCPException(AgniAPIException):
    """Exception raised for MCP-related errors."""
    
    def __init__(
        self,
        detail: str,
        error_code: Optional[str] = None,
    ):
        self.detail = detail
        self.error_code = error_code
        super().__init__(detail)


# HTTP status code exceptions (Flask-style)
class BadRequest(HTTPException):
    """400 Bad Request"""
    def __init__(self, description: str = "Bad Request"):
        super().__init__(400, description)


class Unauthorized(HTTPException):
    """401 Unauthorized"""
    def __init__(self, description: str = "Unauthorized"):
        super().__init__(401, description)


class Forbidden(HTTPException):
    """403 Forbidden"""
    def __init__(self, description: str = "Forbidden"):
        super().__init__(403, description)


class NotFound(HTTPException):
    """404 Not Found"""
    def __init__(self, description: str = "Not Found"):
        super().__init__(404, description)


class MethodNotAllowed(HTTPException):
    """405 Method Not Allowed"""
    def __init__(self, description: str = "Method Not Allowed"):
        super().__init__(405, description)


class NotAcceptable(HTTPException):
    """406 Not Acceptable"""
    def __init__(self, description: str = "Not Acceptable"):
        super().__init__(406, description)


class Conflict(HTTPException):
    """409 Conflict"""
    def __init__(self, description: str = "Conflict"):
        super().__init__(409, description)


class Gone(HTTPException):
    """410 Gone"""
    def __init__(self, description: str = "Gone"):
        super().__init__(410, description)


class LengthRequired(HTTPException):
    """411 Length Required"""
    def __init__(self, description: str = "Length Required"):
        super().__init__(411, description)


class PreconditionFailed(HTTPException):
    """412 Precondition Failed"""
    def __init__(self, description: str = "Precondition Failed"):
        super().__init__(412, description)


class RequestEntityTooLarge(HTTPException):
    """413 Request Entity Too Large"""
    def __init__(self, description: str = "Request Entity Too Large"):
        super().__init__(413, description)


class UnsupportedMediaType(HTTPException):
    """415 Unsupported Media Type"""
    def __init__(self, description: str = "Unsupported Media Type"):
        super().__init__(415, description)


class UnprocessableEntity(HTTPException):
    """422 Unprocessable Entity"""
    def __init__(self, description: str = "Unprocessable Entity"):
        super().__init__(422, description)


class TooManyRequests(HTTPException):
    """429 Too Many Requests"""
    def __init__(self, description: str = "Too Many Requests"):
        super().__init__(429, description)


class InternalServerError(HTTPException):
    """500 Internal Server Error"""
    def __init__(self, description: str = "Internal Server Error"):
        super().__init__(500, description)


class NotImplemented(HTTPException):
    """501 Not Implemented"""
    def __init__(self, description: str = "Not Implemented"):
        super().__init__(501, description)


class BadGateway(HTTPException):
    """502 Bad Gateway"""
    def __init__(self, description: str = "Bad Gateway"):
        super().__init__(502, description)


class ServiceUnavailable(HTTPException):
    """503 Service Unavailable"""
    def __init__(self, description: str = "Service Unavailable"):
        super().__init__(503, description)


class GatewayTimeout(HTTPException):
    """504 Gateway Timeout"""
    def __init__(self, description: str = "Gateway Timeout"):
        super().__init__(504, description)


# Exception handler registry
class ExceptionHandlerRegistry:
    """Registry for exception handlers."""
    
    def __init__(self):
        self._handlers: Dict[Union[int, type], Any] = {}
    
    def add_handler(self, exc_class_or_status_code: Union[int, type], handler):
        """Add an exception handler."""
        self._handlers[exc_class_or_status_code] = handler
    
    def get_handler(self, exc_class_or_status_code: Union[int, type]):
        """Get an exception handler."""
        return self._handlers.get(exc_class_or_status_code)
    
    def remove_handler(self, exc_class_or_status_code: Union[int, type]):
        """Remove an exception handler."""
        if exc_class_or_status_code in self._handlers:
            del self._handlers[exc_class_or_status_code]
    
    def handle_exception(self, exc: Exception, request=None):
        """Handle an exception using registered handlers."""
        # Try to find handler by exception type
        for exc_type in type(exc).__mro__:
            if exc_type in self._handlers:
                handler = self._handlers[exc_type]
                return handler(request, exc)
        
        # Try to find handler by status code for HTTP exceptions
        if isinstance(exc, HTTPException):
            if exc.status_code in self._handlers:
                handler = self._handlers[exc.status_code]
                return handler(request, exc)
        
        # No handler found
        return None


# Utility functions
def abort(status_code: int, description: Optional[str] = None):
    """
    Abort with an HTTP error (Flask-style).
    
    Args:
        status_code: HTTP status code
        description: Error description
    
    Raises:
        HTTPException: With the specified status code and description
    """
    if description is None:
        description = HTTPStatus(status_code).phrase
    
    raise HTTPException(status_code=status_code, detail=description)


def create_validation_error(
    field: str,
    message: str,
    value: Any = None,
    location: List[str] = None,
) -> ValidationError:
    """
    Create a validation error for a specific field.
    
    Args:
        field: Field name that failed validation
        message: Error message
        value: The invalid value
        location: Location of the error (e.g., ["body", "field_name"])
    
    Returns:
        ValidationError: The validation error
    """
    if location is None:
        location = [field]
    
    error = {
        "loc": location,
        "msg": message,
        "type": "value_error",
    }
    
    if value is not None:
        error["input"] = value
    
    return ValidationError([error])


def format_validation_errors(errors: List[Dict[str, Any]]) -> str:
    """
    Format validation errors into a readable string.
    
    Args:
        errors: List of validation error dictionaries
    
    Returns:
        str: Formatted error message
    """
    formatted_errors = []
    
    for error in errors:
        loc = " -> ".join(str(x) for x in error.get("loc", []))
        msg = error.get("msg", "Validation error")
        formatted_errors.append(f"{loc}: {msg}")
    
    return "; ".join(formatted_errors)
