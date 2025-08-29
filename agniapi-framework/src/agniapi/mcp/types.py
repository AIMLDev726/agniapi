"""
Type definitions for MCP integration in Agni API framework.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Union
from dataclasses import dataclass

# MCP component types
MCPTool = Callable[..., Any]
MCPResource = Callable[..., Any] 
MCPPrompt = Callable[..., Any]


@dataclass
class MCPToolInfo:
    """Information about an MCP tool."""
    name: str
    handler: MCPTool
    description: str
    input_schema: Dict[str, Any]
    is_async: bool


@dataclass
class MCPResourceInfo:
    """Information about an MCP resource."""
    uri: str
    handler: MCPResource
    name: str
    description: str
    mime_type: str
    is_async: bool


@dataclass
class MCPPromptInfo:
    """Information about an MCP prompt."""
    name: str
    handler: MCPPrompt
    description: str
    arguments: List[Dict[str, Any]]
    is_async: bool


@dataclass
class MCPServerConfig:
    """Configuration for MCP server."""
    name: str
    version: str
    description: str
    enabled: bool = True
    transports: List[str] = None
    
    def __post_init__(self):
        if self.transports is None:
            self.transports = ["stdio"]


@dataclass
class MCPClientConfig:
    """Configuration for MCP client connection."""
    name: str
    transport: str
    connection_params: Dict[str, Any]
    auto_connect: bool = True
    retry_attempts: int = 3
    timeout: float = 30.0


# Transport-specific configuration types
@dataclass
class StdioTransportConfig:
    """Configuration for stdio transport."""
    command: str
    args: List[str] = None
    env: Dict[str, str] = None
    
    def __post_init__(self):
        if self.args is None:
            self.args = []
        if self.env is None:
            self.env = {}


@dataclass
class SSETransportConfig:
    """Configuration for SSE transport."""
    url: str
    headers: Dict[str, str] = None
    
    def __post_init__(self):
        if self.headers is None:
            self.headers = {}


@dataclass
class WebSocketTransportConfig:
    """Configuration for WebSocket transport."""
    url: str
    headers: Dict[str, str] = None
    
    def __post_init__(self):
        if self.headers is None:
            self.headers = {}


# MCP message types (simplified versions)
@dataclass
class MCPMessage:
    """Base MCP message."""
    type: str
    id: Optional[str] = None


@dataclass
class MCPRequest(MCPMessage):
    """MCP request message."""
    method: str = ""
    params: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.params is None:
            self.params = {}


@dataclass
class MCPResponse(MCPMessage):
    """MCP response message."""
    result: Any = None
    error: Optional[Dict[str, Any]] = None


@dataclass
class MCPNotification(MCPMessage):
    """MCP notification message."""
    method: str = ""
    params: Dict[str, Any] = None

    def __post_init__(self):
        if self.params is None:
            self.params = {}


# Tool execution types
@dataclass
class ToolCall:
    """Represents a tool call."""
    name: str
    arguments: Dict[str, Any]
    call_id: Optional[str] = None


@dataclass
class ToolResult:
    """Represents a tool execution result."""
    content: List[Dict[str, Any]]
    is_error: bool = False
    call_id: Optional[str] = None


# Resource access types
@dataclass
class ResourceRequest:
    """Represents a resource access request."""
    uri: str
    range: Optional[Dict[str, Any]] = None


@dataclass
class ResourceContent:
    """Represents resource content."""
    uri: str
    content: str
    mime_type: str
    encoding: str = "utf-8"


# Prompt types
@dataclass
class PromptArgument:
    """Represents a prompt argument."""
    name: str
    description: str
    required: bool = False
    type: str = "string"


@dataclass
class PromptMessage:
    """Represents a prompt message."""
    role: str
    content: str


@dataclass
class PromptTemplate:
    """Represents a prompt template."""
    name: str
    description: str
    arguments: List[PromptArgument]
    messages: List[PromptMessage]


# Error types
@dataclass
class MCPError:
    """Represents an MCP error."""
    code: int
    message: str
    data: Optional[Dict[str, Any]] = None


# Capability types
@dataclass
class ServerCapabilities:
    """Represents server capabilities."""
    tools: bool = False
    resources: bool = False
    prompts: bool = False
    logging: bool = False


@dataclass
class ClientCapabilities:
    """Represents client capabilities."""
    roots: bool = False
    sampling: bool = False


# Connection state types
class ConnectionState:
    """Enumeration of connection states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    ERROR = "error"


# Transport types
TransportType = Union[
    StdioTransportConfig,
    SSETransportConfig, 
    WebSocketTransportConfig
]


# Registry types
MCPRegistry = Dict[str, Union[MCPToolInfo, MCPResourceInfo, MCPPromptInfo]]


# Callback types
ToolCallback = Callable[[ToolCall], ToolResult]
ResourceCallback = Callable[[ResourceRequest], ResourceContent]
PromptCallback = Callable[[str, Dict[str, Any]], PromptTemplate]


# Event types for MCP integration
@dataclass
class MCPEvent:
    """Base class for MCP events."""
    type: str
    timestamp: float
    source: str


@dataclass
class ToolCallEvent(MCPEvent):
    """Event fired when a tool is called."""
    tool_name: str
    arguments: Dict[str, Any]
    call_id: Optional[str] = None


@dataclass
class ResourceAccessEvent(MCPEvent):
    """Event fired when a resource is accessed."""
    resource_uri: str
    access_type: str = "read"


@dataclass
class ConnectionEvent(MCPEvent):
    """Event fired when connection state changes."""
    client_name: str
    old_state: str
    new_state: str


# Type aliases for convenience
MCPHandler = Union[MCPTool, MCPResource, MCPPrompt]
MCPConfig = Union[MCPServerConfig, MCPClientConfig]
MCPTransport = Union[StdioTransportConfig, SSETransportConfig, WebSocketTransportConfig]
