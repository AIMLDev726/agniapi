"""
MCP Client implementation for Agni API framework.
Allows the framework to connect to other MCP servers.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Optional, Union

# Import MCP SDK components
try:
    from mcp.client import Client
    from mcp.client.stdio import stdio_client
    from mcp.client.sse import sse_client
    from mcp.client.websocket import websocket_client
    from mcp.types import (
        Tool,
        Resource,
        Prompt,
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
    Client = None

from ..exceptions import MCPException


class MCPClient:
    """
    MCP Client implementation for connecting to external MCP servers.
    """
    
    def __init__(self):
        self._clients: Dict[str, Client] = {}
        self._connections: Dict[str, Dict[str, Any]] = {}
        self._mcp_available = MCP_AVAILABLE

        if not MCP_AVAILABLE:
            # MCP not available - graceful degradation without warnings
            pass
    
    async def connect_stdio(
        self,
        name: str,
        command: str,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> Optional[Client]:
        """
        Connect to an MCP server via stdio transport.

        Args:
            name: Connection name for reference
            command: Command to execute the MCP server
            args: Command arguments
            env: Environment variables

        Returns:
            Client: Connected MCP client or None if MCP SDK not available
        """
        if not self._mcp_available:
            return None

        if name in self._clients:
            raise MCPException(f"Client '{name}' already exists", error_code="CLIENT_EXISTS")
        
        try:
            # Create stdio client
            client = await stdio_client(command, args or [], env or {})
            
            # Initialize connection
            await client.initialize()
            
            self._clients[name] = client
            self._connections[name] = {
                "type": "stdio",
                "command": command,
                "args": args,
                "env": env,
            }
            
            return client
        
        except Exception as e:
            raise MCPException(f"Failed to connect via stdio: {str(e)}", error_code="STDIO_CONNECTION_ERROR")
    
    async def connect_sse(
        self,
        name: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> Client:
        """
        Connect to an MCP server via SSE transport.
        
        Args:
            name: Connection name for reference
            url: SSE endpoint URL
            headers: Additional headers
        
        Returns:
            Client: Connected MCP client
        """
        if name in self._clients:
            raise MCPException(f"Client '{name}' already exists", error_code="CLIENT_EXISTS")
        
        try:
            # Create SSE client
            client = await sse_client(url, headers or {})
            
            # Initialize connection
            await client.initialize()
            
            self._clients[name] = client
            self._connections[name] = {
                "type": "sse",
                "url": url,
                "headers": headers,
            }
            
            return client
        
        except Exception as e:
            raise MCPException(f"Failed to connect via SSE: {str(e)}", error_code="SSE_CONNECTION_ERROR")
    
    async def connect_websocket(
        self,
        name: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> Client:
        """
        Connect to an MCP server via WebSocket transport.
        
        Args:
            name: Connection name for reference
            url: WebSocket endpoint URL
            headers: Additional headers
        
        Returns:
            Client: Connected MCP client
        """
        if name in self._clients:
            raise MCPException(f"Client '{name}' already exists", error_code="CLIENT_EXISTS")
        
        try:
            # Create WebSocket client
            client = await websocket_client(url, headers or {})
            
            # Initialize connection
            await client.initialize()
            
            self._clients[name] = client
            self._connections[name] = {
                "type": "websocket",
                "url": url,
                "headers": headers,
            }
            
            return client
        
        except Exception as e:
            raise MCPException(f"Failed to connect via WebSocket: {str(e)}", error_code="WEBSOCKET_CONNECTION_ERROR")
    
    async def disconnect(self, name: str):
        """Disconnect from an MCP server."""
        if name not in self._clients:
            raise MCPException(f"Client '{name}' not found", error_code="CLIENT_NOT_FOUND")
        
        try:
            client = self._clients[name]
            await client.close()
            
            del self._clients[name]
            del self._connections[name]
        
        except Exception as e:
            raise MCPException(f"Failed to disconnect: {str(e)}", error_code="DISCONNECT_ERROR")
    
    async def list_tools(self, client_name: str) -> List[Tool]:
        """List tools available on a connected MCP server."""
        client = self._get_client(client_name)
        
        try:
            result = await client.list_tools()
            return result.tools
        
        except Exception as e:
            raise MCPException(f"Failed to list tools: {str(e)}", error_code="LIST_TOOLS_ERROR")
    
    async def call_tool(
        self,
        client_name: str,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> CallToolResult:
        """Call a tool on a connected MCP server."""
        client = self._get_client(client_name)
        
        try:
            request = CallToolRequest(name=tool_name, arguments=arguments)
            result = await client.call_tool(request)
            return result
        
        except Exception as e:
            raise MCPException(f"Failed to call tool: {str(e)}", error_code="CALL_TOOL_ERROR")
    
    async def list_resources(self, client_name: str) -> List[Resource]:
        """List resources available on a connected MCP server."""
        client = self._get_client(client_name)
        
        try:
            result = await client.list_resources()
            return result.resources
        
        except Exception as e:
            raise MCPException(f"Failed to list resources: {str(e)}", error_code="LIST_RESOURCES_ERROR")
    
    async def read_resource(self, client_name: str, uri: str) -> str:
        """Read a resource from a connected MCP server."""
        client = self._get_client(client_name)
        
        try:
            request = ReadResourceRequest(uri=uri)
            result = await client.read_resource(request)
            
            # Extract text content
            if result.contents:
                content_parts = []
                for content in result.contents:
                    if hasattr(content, 'text'):
                        content_parts.append(content.text)
                    else:
                        content_parts.append(str(content))
                return "\n".join(content_parts)
            
            return ""
        
        except Exception as e:
            raise MCPException(f"Failed to read resource: {str(e)}", error_code="READ_RESOURCE_ERROR")
    
    async def list_prompts(self, client_name: str) -> List[Prompt]:
        """List prompts available on a connected MCP server."""
        client = self._get_client(client_name)
        
        try:
            result = await client.list_prompts()
            return result.prompts
        
        except Exception as e:
            raise MCPException(f"Failed to list prompts: {str(e)}", error_code="LIST_PROMPTS_ERROR")
    
    async def get_prompt(
        self,
        client_name: str,
        prompt_name: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> GetPromptRequest:
        """Get a prompt from a connected MCP server."""
        client = self._get_client(client_name)
        
        try:
            request = GetPromptRequest(name=prompt_name, arguments=arguments or {})
            result = await client.get_prompt(request)
            return result
        
        except Exception as e:
            raise MCPException(f"Failed to get prompt: {str(e)}", error_code="GET_PROMPT_ERROR")
    
    def _get_client(self, name: str) -> Client:
        """Get a client by name."""
        if name not in self._clients:
            raise MCPException(f"Client '{name}' not found", error_code="CLIENT_NOT_FOUND")
        
        return self._clients[name]
    
    def get_client(self, name: str) -> Optional[Client]:
        """Get a client by name (public method)."""
        return self._clients.get(name)
    
    def list_clients(self) -> List[str]:
        """List all connected client names."""
        return list(self._clients.keys())
    
    def get_connection_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get connection information for a client."""
        return self._connections.get(name)
    
    async def disconnect_all(self):
        """Disconnect from all MCP servers."""
        for name in list(self._clients.keys()):
            try:
                await self.disconnect(name)
            except Exception:
                # Continue disconnecting other clients even if one fails
                pass
    
    async def ping(self, client_name: str) -> bool:
        """Ping an MCP server to check if it's responsive."""
        try:
            # Try to list tools as a simple ping
            await self.list_tools(client_name)
            return True
        except Exception:
            return False
    
    async def get_server_info(self, client_name: str) -> Dict[str, Any]:
        """Get information about a connected MCP server."""
        client = self._get_client(client_name)
        
        try:
            # Gather information about the server
            tools = await self.list_tools(client_name)
            resources = await self.list_resources(client_name)
            prompts = await self.list_prompts(client_name)
            
            return {
                "name": client_name,
                "connection": self._connections[client_name],
                "capabilities": {
                    "tools": len(tools),
                    "resources": len(resources),
                    "prompts": len(prompts),
                },
                "tools": [{"name": tool.name, "description": tool.description} for tool in tools],
                "resources": [{"uri": res.uri, "name": res.name} for res in resources],
                "prompts": [{"name": prompt.name, "description": prompt.description} for prompt in prompts],
            }
        
        except Exception as e:
            raise MCPException(f"Failed to get server info: {str(e)}", error_code="SERVER_INFO_ERROR")
    
    def __repr__(self):
        return f"<MCPClient clients={list(self._clients.keys())}>"
