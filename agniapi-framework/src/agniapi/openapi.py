"""
OpenAPI documentation generation for Agni API framework.
Automatically generates OpenAPI/Swagger documentation from routes.
"""

from __future__ import annotations

import inspect
from typing import Any, Dict, List, Optional, Type, Union, get_type_hints
from enum import Enum

from .routing import Route, Router
from .types import get_type_hints_with_defaults


class OpenAPIGenerator:
    """
    Generates OpenAPI 3.0 documentation from application routes.
    """
    
    def __init__(
        self,
        title: str = "Agni API",
        description: str = "",
        version: str = "1.0.0",
        openapi_version: str = "3.0.2",
    ):
        self.title = title
        self.description = description
        self.version = version
        self.openapi_version = openapi_version
        
        # Schema definitions
        self._schemas: Dict[str, Dict[str, Any]] = {}
        self._security_schemes: Dict[str, Dict[str, Any]] = {}
    
    def generate_openapi(self, router: Router) -> Dict[str, Any]:
        """Generate complete OpenAPI specification."""
        openapi_spec = {
            "openapi": self.openapi_version,
            "info": {
                "title": self.title,
                "description": self.description,
                "version": self.version,
            },
            "paths": {},
            "components": {
                "schemas": self._schemas,
                "securitySchemes": self._security_schemes,
            },
        }
        
        # Generate paths from routes
        for route in router.get_all_routes():
            path_item = self._generate_path_item(route)
            
            # Convert path parameters to OpenAPI format
            openapi_path = self._convert_path_to_openapi(route.path)
            
            if openapi_path not in openapi_spec["paths"]:
                openapi_spec["paths"][openapi_path] = {}
            
            # Add operations for each method
            for method in route.methods:
                operation = self._generate_operation(route, method.lower())
                openapi_spec["paths"][openapi_path][method.lower()] = operation
        
        return openapi_spec
    
    def _convert_path_to_openapi(self, path: str) -> str:
        """Convert path parameters to OpenAPI format."""
        import re
        
        # Convert Flask-style <param> to OpenAPI {param}
        path = re.sub(r'<([^>:]+)>', r'{\1}', path)
        
        # Convert Flask-style <type:param> to OpenAPI {param}
        path = re.sub(r'<[^>:]+:([^>]+)>', r'{\1}', path)
        
        return path
    
    def _generate_path_item(self, route: Route) -> Dict[str, Any]:
        """Generate path item for a route."""
        return {
            "summary": route.summary or f"Operations for {route.path}",
            "description": route.description or "",
        }
    
    def _generate_operation(self, route: Route, method: str) -> Dict[str, Any]:
        """Generate operation object for a route method."""
        operation = {
            "operationId": f"{method}_{route.name}",
            "summary": route.summary or f"{method.upper()} {route.path}",
            "description": route.description or route.handler.__doc__ or "",
            "tags": route.tags,
            "responses": self._generate_responses(route),
        }
        
        # Add parameters
        parameters = self._generate_parameters(route)
        if parameters:
            operation["parameters"] = parameters
        
        # Add request body for methods that typically have one
        if method.lower() in ["post", "put", "patch"]:
            request_body = self._generate_request_body(route)
            if request_body:
                operation["requestBody"] = request_body
        
        # Add security if route has dependencies that look like security
        security = self._generate_security(route)
        if security:
            operation["security"] = security
        
        return operation
    
    def _generate_parameters(self, route: Route) -> List[Dict[str, Any]]:
        """Generate parameters for a route."""
        parameters = []
        
        # Get function signature
        sig = route.signature
        type_hints = get_type_hints(route.handler)
        
        for param_name, param in sig.parameters.items():
            # Skip special parameters
            if param_name in ("self", "request", "websocket"):
                continue
            
            # Check if it's a path parameter
            if param_name in route.param_names:
                param_schema = self._get_parameter_schema(param, type_hints.get(param_name))
                parameters.append({
                    "name": param_name,
                    "in": "path",
                    "required": True,
                    "schema": param_schema,
                    "description": f"Path parameter {param_name}",
                })
            
            # Check if it's a query parameter (has default value or is Optional)
            elif param.default != inspect.Parameter.empty or self._is_optional_type(type_hints.get(param_name)):
                param_schema = self._get_parameter_schema(param, type_hints.get(param_name))
                parameters.append({
                    "name": param_name,
                    "in": "query",
                    "required": param.default == inspect.Parameter.empty,
                    "schema": param_schema,
                    "description": f"Query parameter {param_name}",
                })
        
        return parameters
    
    def _generate_request_body(self, route: Route) -> Optional[Dict[str, Any]]:
        """Generate request body for a route."""
        sig = route.signature
        type_hints = get_type_hints(route.handler)
        
        # Look for Pydantic models or complex types in parameters
        for param_name, param in sig.parameters.items():
            if param_name in ("self", "request", "websocket"):
                continue
            
            param_type = type_hints.get(param_name)
            if param_type and self._is_model_type(param_type):
                schema = self._get_model_schema(param_type)
                return {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": schema
                        }
                    }
                }
        
        return None
    
    def _generate_responses(self, route: Route) -> Dict[str, Any]:
        """Generate responses for a route."""
        responses = {
            str(route.status_code): {
                "description": "Successful response",
            }
        }
        
        # Add response model if specified
        if route.response_model:
            schema = self._get_model_schema(route.response_model)
            responses[str(route.status_code)]["content"] = {
                "application/json": {
                    "schema": schema
                }
            }
        
        # Add common error responses
        responses.update({
            "422": {
                "description": "Validation Error",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "detail": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "loc": {"type": "array", "items": {"type": "string"}},
                                            "msg": {"type": "string"},
                                            "type": {"type": "string"},
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        })
        
        return responses
    
    def _generate_security(self, route: Route) -> List[Dict[str, List[str]]]:
        """Generate security requirements for a route."""
        # This is a simplified implementation
        # In a real implementation, you'd analyze the route's dependencies
        # to determine security requirements
        return []
    
    def _get_parameter_schema(self, param: inspect.Parameter, param_type: Optional[Type]) -> Dict[str, Any]:
        """Get schema for a parameter."""
        if param_type:
            return self._type_to_schema(param_type)
        
        # Default to string
        return {"type": "string"}
    
    def _type_to_schema(self, type_hint: Type) -> Dict[str, Any]:
        """Convert Python type to OpenAPI schema."""
        if type_hint == str:
            return {"type": "string"}
        elif type_hint == int:
            return {"type": "integer"}
        elif type_hint == float:
            return {"type": "number"}
        elif type_hint == bool:
            return {"type": "boolean"}
        elif type_hint == list:
            return {"type": "array", "items": {"type": "string"}}
        elif type_hint == dict:
            return {"type": "object"}
        elif hasattr(type_hint, "__origin__"):
            # Handle generic types like List[str], Dict[str, int], etc.
            origin = type_hint.__origin__
            if origin == list:
                args = getattr(type_hint, "__args__", ())
                item_type = args[0] if args else str
                return {
                    "type": "array",
                    "items": self._type_to_schema(item_type)
                }
            elif origin == dict:
                return {"type": "object"}
            elif origin == Union:
                # Handle Optional types
                args = getattr(type_hint, "__args__", ())
                if len(args) == 2 and type(None) in args:
                    # This is Optional[T]
                    non_none_type = args[0] if args[1] == type(None) else args[1]
                    schema = self._type_to_schema(non_none_type)
                    schema["nullable"] = True
                    return schema
        elif isinstance(type_hint, type) and issubclass(type_hint, Enum):
            # Handle Enum types
            return {
                "type": "string",
                "enum": [item.value for item in type_hint]
            }
        elif self._is_model_type(type_hint):
            # Handle Pydantic models
            return self._get_model_schema(type_hint)
        
        # Default fallback
        return {"type": "string"}
    
    def _is_optional_type(self, type_hint: Optional[Type]) -> bool:
        """Check if type is Optional."""
        if not type_hint:
            return False
        
        if hasattr(type_hint, "__origin__") and type_hint.__origin__ == Union:
            args = getattr(type_hint, "__args__", ())
            return len(args) == 2 and type(None) in args
        
        return False
    
    def _is_model_type(self, type_hint: Type) -> bool:
        """Check if type is a Pydantic model."""
        if not type_hint:
            return False
        
        # Check for Pydantic model
        return (hasattr(type_hint, "__pydantic_model__") or 
                hasattr(type_hint, "model_validate") or
                hasattr(type_hint, "__fields__"))
    
    def _get_model_schema(self, model_type: Type) -> Dict[str, Any]:
        """Get schema for a Pydantic model."""
        model_name = model_type.__name__
        
        # Check if already generated
        if model_name in self._schemas:
            return {"$ref": f"#/components/schemas/{model_name}"}
        
        # Generate schema
        try:
            if hasattr(model_type, "model_json_schema"):
                # Pydantic v2
                schema = model_type.model_json_schema()
            elif hasattr(model_type, "schema"):
                # Pydantic v1
                schema = model_type.schema()
            else:
                # Fallback for non-Pydantic models
                schema = {"type": "object"}
            
            # Store in schemas
            self._schemas[model_name] = schema
            
            return {"$ref": f"#/components/schemas/{model_name}"}
        
        except Exception:
            # Fallback
            return {"type": "object"}
    
    def add_security_scheme(self, name: str, scheme: Dict[str, Any]):
        """Add a security scheme to the OpenAPI spec."""
        self._security_schemes[name] = scheme
    
    def get_openapi_schema(self, router: Router) -> Dict[str, Any]:
        """Get the complete OpenAPI schema."""
        return self.generate_openapi(router)
