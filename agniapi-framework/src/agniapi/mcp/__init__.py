"""
Model Context Protocol (MCP) integration for Agni API framework.
Provides built-in MCP server and client capabilities.
"""

from __future__ import annotations

from .server import MCPServer
from .client import MCPClient
from .tools import mcp_tool, mcp_resource, mcp_prompt, MCPToolRegistry
from .types import MCPTool, MCPResource, MCPPrompt

__all__ = [
    "MCPServer",
    "MCPClient",
    "mcp_tool",
    "mcp_resource",
    "mcp_prompt",
    "MCPToolRegistry",
    "MCPTool",
    "MCPResource",
    "MCPPrompt",
]
