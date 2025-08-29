"""
MCP tools and decorators for Agni API framework.
Provides decorators for registering MCP tools and resources.
"""

from __future__ import annotations

import inspect
from typing import Any, Callable, Dict, List, Optional
from functools import wraps

from ..exceptions import MCPException
from ..types import is_async_callable


class MCPToolRegistry:
    """
    Registry for MCP tools, resources, and prompts.
    Used by the framework to track registered MCP components.
    """
    
    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._resources: Dict[str, Dict[str, Any]] = {}
        self._prompts: Dict[str, Dict[str, Any]] = {}
    
    def register_tool(
        self,
        name: str,
        handler: Callable,
        description: str = "",
        input_schema: Optional[Dict[str, Any]] = None,
    ):
        """Register an MCP tool."""
        if name in self._tools:
            raise MCPException(f"Tool '{name}' already registered", error_code="TOOL_ALREADY_EXISTS")
        
        self._tools[name] = {
            "handler": handler,
            "description": description,
            "input_schema": input_schema,
            "is_async": is_async_callable(handler),
        }
    
    def register_resource(
        self,
        uri: str,
        handler: Callable,
        name: str = "",
        description: str = "",
        mime_type: str = "text/plain",
    ):
        """Register an MCP resource."""
        if uri in self._resources:
            raise MCPException(f"Resource '{uri}' already registered", error_code="RESOURCE_ALREADY_EXISTS")
        
        self._resources[uri] = {
            "handler": handler,
            "name": name or uri,
            "description": description,
            "mime_type": mime_type,
            "is_async": is_async_callable(handler),
        }
    
    def register_prompt(
        self,
        name: str,
        handler: Callable,
        description: str = "",
        arguments: Optional[List[Dict[str, Any]]] = None,
    ):
        """Register an MCP prompt."""
        if name in self._prompts:
            raise MCPException(f"Prompt '{name}' already registered", error_code="PROMPT_ALREADY_EXISTS")
        
        self._prompts[name] = {
            "handler": handler,
            "description": description,
            "arguments": arguments or [],
            "is_async": is_async_callable(handler),
        }
    
    def get_tool(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a registered tool."""
        return self._tools.get(name)
    
    def get_resource(self, uri: str) -> Optional[Dict[str, Any]]:
        """Get a registered resource."""
        return self._resources.get(uri)
    
    def get_prompt(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a registered prompt."""
        return self._prompts.get(name)
    
    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        return list(self._tools.keys())
    
    def list_resources(self) -> List[str]:
        """List all registered resource URIs."""
        return list(self._resources.keys())
    
    def list_prompts(self) -> List[str]:
        """List all registered prompt names."""
        return list(self._prompts.keys())
    
    def get_all_tools(self) -> Dict[str, Dict[str, Any]]:
        """Get all registered tools."""
        return self._tools.copy()
    
    def get_all_resources(self) -> Dict[str, Dict[str, Any]]:
        """Get all registered resources."""
        return self._resources.copy()
    
    def get_all_prompts(self) -> Dict[str, Dict[str, Any]]:
        """Get all registered prompts."""
        return self._prompts.copy()
    
    def clear(self):
        """Clear all registrations."""
        self._tools.clear()
        self._resources.clear()
        self._prompts.clear()


# Global registry instance
_global_registry = MCPToolRegistry()


def mcp_tool(
    name: Optional[str] = None,
    description: str = "",
    input_schema: Optional[Dict[str, Any]] = None,
):
    """
    Decorator to register a function as an MCP tool.
    
    Args:
        name: Tool name (defaults to function name)
        description: Tool description
        input_schema: JSON schema for tool inputs
    
    Example:
        @mcp_tool("get_weather", "Get weather information for a location")
        async def get_weather(location: str) -> dict:
            return {"location": location, "temperature": "22°C"}
    """
    def decorator(func: Callable) -> Callable:
        tool_name = name or func.__name__
        
        # Generate input schema if not provided
        schema = input_schema
        if schema is None:
            schema = _generate_input_schema_from_function(func)
        
        # Register with global registry
        _global_registry.register_tool(
            tool_name,
            func,
            description or func.__doc__ or "",
            schema
        )
        
        # Mark function as MCP tool
        func._mcp_tool = True
        func._mcp_tool_name = tool_name
        func._mcp_tool_description = description
        func._mcp_tool_schema = schema
        
        return func
    
    return decorator


def mcp_resource(
    uri: Optional[str] = None,
    name: str = "",
    description: str = "",
    mime_type: str = "text/plain",
):
    """
    Decorator to register a function as an MCP resource.
    
    Args:
        uri: Resource URI (defaults to function name)
        name: Resource name
        description: Resource description
        mime_type: MIME type of the resource
    
    Example:
        @mcp_resource("database://users", "User Database", "Access to user data")
        async def get_users() -> list:
            return [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
    """
    def decorator(func: Callable) -> Callable:
        resource_uri = uri or f"resource://{func.__name__}"
        
        # Register with global registry
        _global_registry.register_resource(
            resource_uri,
            func,
            name or func.__name__,
            description or func.__doc__ or "",
            mime_type
        )
        
        # Mark function as MCP resource
        func._mcp_resource = True
        func._mcp_resource_uri = resource_uri
        func._mcp_resource_name = name
        func._mcp_resource_description = description
        func._mcp_resource_mime_type = mime_type
        
        return func
    
    return decorator


def mcp_prompt(
    name: Optional[str] = None,
    description: str = "",
    arguments: Optional[List[Dict[str, Any]]] = None,
):
    """
    Decorator to register a function as an MCP prompt.
    
    Args:
        name: Prompt name (defaults to function name)
        description: Prompt description
        arguments: List of prompt arguments
    
    Example:
        @mcp_prompt("code_review", "Generate code review prompt")
        async def code_review_prompt(code: str, language: str) -> dict:
            return {
                "messages": [
                    {"role": "user", "content": f"Review this {language} code: {code}"}
                ]
            }
    """
    def decorator(func: Callable) -> Callable:
        prompt_name = name or func.__name__
        
        # Generate arguments schema if not provided
        args = arguments
        if args is None:
            args = _generate_arguments_from_function(func)
        
        # Register with global registry
        _global_registry.register_prompt(
            prompt_name,
            func,
            description or func.__doc__ or "",
            args
        )
        
        # Mark function as MCP prompt
        func._mcp_prompt = True
        func._mcp_prompt_name = prompt_name
        func._mcp_prompt_description = description
        func._mcp_prompt_arguments = args
        
        return func
    
    return decorator


def _generate_input_schema_from_function(func: Callable) -> Dict[str, Any]:
    """Generate JSON schema from function signature."""
    sig = inspect.signature(func)
    properties = {}
    required = []
    
    for param_name, param in sig.parameters.items():
        # Skip self and cls parameters
        if param_name in ('self', 'cls'):
            continue
        
        param_schema = {"type": "string"}  # Default type
        
        # Infer type from annotation
        if param.annotation != inspect.Parameter.empty:
            if param.annotation == int:
                param_schema["type"] = "integer"
            elif param.annotation == float:
                param_schema["type"] = "number"
            elif param.annotation == bool:
                param_schema["type"] = "boolean"
            elif param.annotation == list:
                param_schema["type"] = "array"
            elif param.annotation == dict:
                param_schema["type"] = "object"
            elif hasattr(param.annotation, '__origin__'):
                # Handle generic types like List[str], Dict[str, int], etc.
                origin = param.annotation.__origin__
                if origin == list:
                    param_schema["type"] = "array"
                elif origin == dict:
                    param_schema["type"] = "object"
        
        # Add description from docstring if available
        if func.__doc__:
            # Simple docstring parsing - could be enhanced
            param_schema["description"] = f"Parameter {param_name}"
        
        properties[param_name] = param_schema
        
        # Required if no default value
        if param.default == inspect.Parameter.empty:
            required.append(param_name)
    
    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


def _generate_arguments_from_function(func: Callable) -> List[Dict[str, Any]]:
    """Generate prompt arguments from function signature."""
    sig = inspect.signature(func)
    arguments = []
    
    for param_name, param in sig.parameters.items():
        # Skip self and cls parameters
        if param_name in ('self', 'cls'):
            continue
        
        arg_def = {
            "name": param_name,
            "description": f"Parameter {param_name}",
            "required": param.default == inspect.Parameter.empty,
        }
        
        # Add type information
        if param.annotation != inspect.Parameter.empty:
            if param.annotation == str:
                arg_def["type"] = "string"
            elif param.annotation == int:
                arg_def["type"] = "integer"
            elif param.annotation == float:
                arg_def["type"] = "number"
            elif param.annotation == bool:
                arg_def["type"] = "boolean"
        
        arguments.append(arg_def)
    
    return arguments


def get_global_registry() -> MCPToolRegistry:
    """Get the global MCP tool registry."""
    return _global_registry


def register_with_server(server, registry: Optional[MCPToolRegistry] = None):
    """
    Register all tools, resources, and prompts from a registry with an MCP server.
    
    Args:
        server: MCP server instance
        registry: Registry to use (defaults to global registry)
    """
    if registry is None:
        registry = _global_registry
    
    # Register tools
    for tool_name, tool_info in registry.get_all_tools().items():
        server.register_tool(
            tool_name,
            tool_info["handler"],
            tool_info["description"],
            tool_info["input_schema"]
        )
    
    # Register resources
    for resource_uri, resource_info in registry.get_all_resources().items():
        server.register_resource(
            resource_uri,
            resource_info["handler"],
            resource_info["name"],
            resource_info["description"],
            resource_info["mime_type"]
        )
    
    # Register prompts
    for prompt_name, prompt_info in registry.get_all_prompts().items():
        server.register_prompt(
            prompt_name,
            prompt_info["handler"],
            prompt_info["description"],
            prompt_info["arguments"]
        )


# Type definitions for MCP components
MCPTool = Callable[..., Any]
MCPResource = Callable[..., Any]
MCPPrompt = Callable[..., Any]
