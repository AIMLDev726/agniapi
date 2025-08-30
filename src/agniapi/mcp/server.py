"""
MCP Server implementation for Agni API framework.
Integrates with the MCP Python SDK to provide server capabilities.
"""

from __future__ import annotations

import asyncio
import inspect
import json
from typing import Any, Callable, Dict, List, Optional, Union

# Import MCP SDK components
try:
    from mcp.server import Server
    from mcp.server.models import InitializationOptions
    from mcp.server.stdio import stdio_server
    from mcp.server.sse import sse_server
    from mcp.server.websocket import websocket_server
    from mcp.types import (
        Tool, 
        Resource, 
        Prompt,
        TextContent,
        ImageContent,
        EmbeddedResource,
        CallToolRequest,
        CallToolResult,
        ListToolsRequest,
        ListResourcesRequest,
        ReadResourceRequest,
        GetPromptRequest,
    )
    MCP_AVAILABLE = True
except ImportError:
    # Fallback if MCP SDK is not available
    MCP_AVAILABLE = False
    Server = None
    Tool = Dict[str, Any]
    Resource = Dict[str, Any]
    Prompt = Dict[str, Any]

from ..exceptions import MCPException
from ..types import is_async_callable


class MCPServer:
    """
    MCP Server implementation that integrates with Agni API.
    Provides tool and resource registration capabilities.
    """
    
    def __init__(
        self,
        name: str = "agni-api-server",
        version: str = "1.0.0",
        description: str = "Agni API MCP Server",
    ):
        self.name = name
        self.version = version
        self.description = description
        
        # Tool and resource registries
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._resources: Dict[str, Dict[str, Any]] = {}
        self._prompts: Dict[str, Dict[str, Any]] = {}
        
        # MCP server instance
        self._server: Optional[Server] = None
        self._initialized = False
        self._mcp_available = MCP_AVAILABLE

        if not MCP_AVAILABLE:
            # MCP not available - graceful degradation without warnings
            pass
    
    def initialize(self) -> Optional[Server]:
        """Initialize the MCP server."""
        if self._initialized:
            return self._server

        if not self._mcp_available:
            self._initialized = True
            return None

        self._server = Server(self.name)

        # Register handlers
        self._setup_handlers()

        self._initialized = True
        return self._server
    
    def _setup_handlers(self):
        """Setup MCP server handlers."""
        if not self._server or not self._mcp_available:
            return
        
        @self._server.list_tools()
        async def list_tools() -> List[Tool]:
            """List all available tools."""
            tools = []
            for tool_name, tool_info in self._tools.items():
                tool = Tool(
                    name=tool_name,
                    description=tool_info["description"],
                    inputSchema=tool_info.get("input_schema", {
                        "type": "object",
                        "properties": {},
                    })
                )
                tools.append(tool)
            return tools
        
        @self._server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
            """Call a registered tool."""
            if name not in self._tools:
                raise MCPException(f"Tool '{name}' not found", error_code="TOOL_NOT_FOUND")
            
            tool_info = self._tools[name]
            handler = tool_info["handler"]
            
            try:
                # Call the tool handler
                if is_async_callable(handler):
                    result = await handler(**arguments)
                else:
                    result = handler(**arguments)
                
                # Format result as MCP content
                if isinstance(result, str):
                    content = [TextContent(type="text", text=result)]
                elif isinstance(result, dict):
                    content = [TextContent(type="text", text=json.dumps(result, indent=2))]
                elif isinstance(result, list):
                    content = [TextContent(type="text", text=json.dumps(result, indent=2))]
                else:
                    content = [TextContent(type="text", text=str(result))]
                
                return CallToolResult(content=content)
            
            except Exception as e:
                raise MCPException(f"Tool execution failed: {str(e)}", error_code="TOOL_EXECUTION_ERROR")
        
        @self._server.list_resources()
        async def list_resources() -> List[Resource]:
            """List all available resources."""
            resources = []
            for resource_uri, resource_info in self._resources.items():
                resource = Resource(
                    uri=resource_uri,
                    name=resource_info.get("name", resource_uri),
                    description=resource_info.get("description", ""),
                    mimeType=resource_info.get("mime_type", "text/plain")
                )
                resources.append(resource)
            return resources
        
        @self._server.read_resource()
        async def read_resource(uri: str) -> str:
            """Read a resource by URI."""
            if uri not in self._resources:
                raise MCPException(f"Resource '{uri}' not found", error_code="RESOURCE_NOT_FOUND")
            
            resource_info = self._resources[uri]
            handler = resource_info["handler"]
            
            try:
                # Call the resource handler
                if is_async_callable(handler):
                    result = await handler()
                else:
                    result = handler()
                
                # Convert result to string
                if isinstance(result, str):
                    return result
                elif isinstance(result, (dict, list)):
                    return json.dumps(result, indent=2)
                else:
                    return str(result)
            
            except Exception as e:
                raise MCPException(f"Resource read failed: {str(e)}", error_code="RESOURCE_READ_ERROR")
        
        @self._server.get_prompt()
        async def get_prompt(name: str, arguments: Optional[Dict[str, Any]] = None) -> GetPromptRequest:
            """Get a prompt by name."""
            if name not in self._prompts:
                raise MCPException(f"Prompt '{name}' not found", error_code="PROMPT_NOT_FOUND")
            
            prompt_info = self._prompts[name]
            handler = prompt_info["handler"]
            
            try:
                # Call the prompt handler
                if is_async_callable(handler):
                    result = await handler(**(arguments or {}))
                else:
                    result = handler(**(arguments or {}))
                
                # Format as prompt response
                if isinstance(result, str):
                    messages = [{"role": "user", "content": result}]
                elif isinstance(result, dict) and "messages" in result:
                    messages = result["messages"]
                else:
                    messages = [{"role": "user", "content": str(result)}]
                
                return GetPromptRequest(
                    description=prompt_info.get("description", ""),
                    messages=messages
                )
            
            except Exception as e:
                raise MCPException(f"Prompt generation failed: {str(e)}", error_code="PROMPT_GENERATION_ERROR")
    
    def register_tool(
        self,
        name: str,
        handler: Callable,
        description: str = "",
        input_schema: Optional[Dict[str, Any]] = None,
    ):
        """Register a tool with the MCP server."""
        if not self._mcp_available:
            # Silently ignore if MCP SDK is not available
            return

        if input_schema is None:
            # Generate schema from function signature
            input_schema = self._generate_input_schema(handler)

        self._tools[name] = {
            "handler": handler,
            "description": description,
            "input_schema": input_schema,
        }
    
    def register_resource(
        self,
        uri: str,
        handler: Callable,
        name: str = "",
        description: str = "",
        mime_type: str = "text/plain",
    ):
        """Register a resource with the MCP server."""
        if not self._mcp_available:
            # Silently ignore if MCP SDK is not available
            return

        self._resources[uri] = {
            "handler": handler,
            "name": name or uri,
            "description": description,
            "mime_type": mime_type,
        }
    
    def register_prompt(
        self,
        name: str,
        handler: Callable,
        description: str = "",
        arguments: Optional[List[Dict[str, Any]]] = None,
    ):
        """Register a prompt with the MCP server."""
        if not self._mcp_available:
            # Silently ignore if MCP SDK is not available
            return

        self._prompts[name] = {
            "handler": handler,
            "description": description,
            "arguments": arguments or [],
        }
    
    def _generate_input_schema(self, func: Callable) -> Dict[str, Any]:
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
    
    async def run_stdio(self):
        """Run MCP server with stdio transport."""
        if not self._initialized:
            self.initialize()
        
        async with stdio_server() as (read_stream, write_stream):
            await self._server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name=self.name,
                    server_version=self.version,
                )
            )
    
    async def run_sse(self, host: str = "localhost", port: int = 8080):
        """Run MCP server with SSE transport."""
        if not self._initialized:
            self.initialize()
        
        async with sse_server(host, port) as server:
            await server.run(self._server)
    
    async def run_websocket(self, host: str = "localhost", port: int = 8080):
        """Run MCP server with WebSocket transport."""
        if not self._initialized:
            self.initialize()
        
        async with websocket_server(host, port) as server:
            await server.run(self._server)
    
    def get_server(self) -> Optional[Server]:
        """Get the underlying MCP server instance."""
        return self._server
    
    def is_initialized(self) -> bool:
        """Check if the server is initialized."""
        return self._initialized
    
    def get_tools(self) -> Dict[str, Dict[str, Any]]:
        """Get all registered tools."""
        return self._tools.copy()
    
    def get_resources(self) -> Dict[str, Dict[str, Any]]:
        """Get all registered resources."""
        return self._resources.copy()
    
    def get_prompts(self) -> Dict[str, Dict[str, Any]]:
        """Get all registered prompts."""
        return self._prompts.copy()
