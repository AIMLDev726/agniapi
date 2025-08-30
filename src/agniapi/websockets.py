"""
WebSocket support for Agni API framework.
Provides WebSocket handling capabilities similar to FastAPI.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Callable, Dict, List, Optional, Union
from enum import Enum

from starlette.websockets import WebSocket as StarletteWebSocket
from starlette.websockets import WebSocketDisconnect
from starlette.websockets import WebSocketState as StarletteWebSocketState

from .exceptions import WebSocketException
from .types import is_async_callable


class WebSocketState(Enum):
    """WebSocket connection states."""
    CONNECTING = 0
    CONNECTED = 1
    DISCONNECTED = 2


class WebSocket:
    """
    WebSocket wrapper that provides a unified interface.
    Compatible with both Starlette WebSockets and custom implementations.
    """
    
    def __init__(self, scope: Dict[str, Any], receive=None, send=None):
        self.scope = scope
        self.receive = receive
        self.send = send
        
        # Create underlying WebSocket
        if scope.get("type") == "websocket":
            self._websocket = StarletteWebSocket(scope, receive, send)
        else:
            self._websocket = None
        
        self._state = WebSocketState.CONNECTING
        self._client_state = "CONNECTING"
        self._application_state = "CONNECTING"
    
    @property
    def client(self) -> Optional[str]:
        """Get client address."""
        if self._websocket:
            return self._websocket.client.host if self._websocket.client else None
        
        client = self.scope.get("client")
        return client[0] if client else None
    
    @property
    def url(self) -> str:
        """Get WebSocket URL."""
        if self._websocket:
            return str(self._websocket.url)
        
        # Construct URL from scope
        scheme = self.scope.get("scheme", "ws")
        server = self.scope.get("server", ("localhost", 80))
        path = self.scope.get("path", "/")
        query_string = self.scope.get("query_string", b"")
        
        url = f"{scheme}://{server[0]}:{server[1]}{path}"
        if query_string:
            url += f"?{query_string.decode()}"
        
        return url
    
    @property
    def headers(self) -> Dict[str, str]:
        """Get WebSocket headers."""
        if self._websocket:
            return dict(self._websocket.headers)
        
        headers = {}
        for name, value in self.scope.get("headers", []):
            headers[name.decode()] = value.decode()
        return headers
    
    @property
    def query_params(self) -> Dict[str, str]:
        """Get query parameters."""
        if self._websocket:
            return dict(self._websocket.query_params)
        
        query_string = self.scope.get("query_string", b"").decode()
        params = {}
        if query_string:
            for param in query_string.split("&"):
                if "=" in param:
                    key, value = param.split("=", 1)
                    params[key] = value
        return params
    
    @property
    def path_params(self) -> Dict[str, Any]:
        """Get path parameters."""
        if self._websocket:
            return dict(self._websocket.path_params)
        
        return self.scope.get("path_params", {})
    
    @property
    def cookies(self) -> Dict[str, str]:
        """Get cookies."""
        if self._websocket:
            return dict(self._websocket.cookies)
        
        cookie_header = self.headers.get("cookie", "")
        cookies = {}
        for item in cookie_header.split(";"):
            if "=" in item:
                key, value = item.strip().split("=", 1)
                cookies[key] = value
        return cookies
    
    @property
    def state(self) -> WebSocketState:
        """Get connection state."""
        return self._state
    
    async def accept(
        self,
        subprotocol: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        """Accept the WebSocket connection."""
        if self._websocket:
            await self._websocket.accept(subprotocol, headers)
        else:
            # Send accept message manually
            message = {
                "type": "websocket.accept",
            }
            if subprotocol:
                message["subprotocol"] = subprotocol
            if headers:
                message["headers"] = [(k.encode(), v.encode()) for k, v in headers.items()]
            
            await self.send(message)
        
        self._state = WebSocketState.CONNECTED
        self._client_state = "CONNECTED"
        self._application_state = "CONNECTED"
    
    async def close(self, code: int = 1000, reason: str = ""):
        """Close the WebSocket connection."""
        if self._websocket:
            await self._websocket.close(code, reason)
        else:
            # Send close message manually
            await self.send({
                "type": "websocket.close",
                "code": code,
                "reason": reason,
            })
        
        self._state = WebSocketState.DISCONNECTED
        self._client_state = "DISCONNECTED"
        self._application_state = "DISCONNECTED"
    
    async def send_text(self, data: str):
        """Send text data."""
        if self._state != WebSocketState.CONNECTED:
            raise WebSocketException("WebSocket is not connected")
        
        if self._websocket:
            await self._websocket.send_text(data)
        else:
            await self.send({
                "type": "websocket.send",
                "text": data,
            })
    
    async def send_bytes(self, data: bytes):
        """Send binary data."""
        if self._state != WebSocketState.CONNECTED:
            raise WebSocketException("WebSocket is not connected")
        
        if self._websocket:
            await self._websocket.send_bytes(data)
        else:
            await self.send({
                "type": "websocket.send",
                "bytes": data,
            })
    
    async def send_json(self, data: Any, mode: str = "text"):
        """Send JSON data."""
        json_data = json.dumps(data)
        
        if mode == "text":
            await self.send_text(json_data)
        elif mode == "binary":
            await self.send_bytes(json_data.encode())
        else:
            raise ValueError("Mode must be 'text' or 'binary'")
    
    async def receive_text(self) -> str:
        """Receive text data."""
        if self._state != WebSocketState.CONNECTED:
            raise WebSocketException("WebSocket is not connected")
        
        if self._websocket:
            return await self._websocket.receive_text()
        else:
            message = await self.receive()
            if message["type"] == "websocket.receive":
                if "text" in message:
                    return message["text"]
                else:
                    raise WebSocketException("Expected text message")
            elif message["type"] == "websocket.disconnect":
                self._state = WebSocketState.DISCONNECTED
                raise WebSocketDisconnect(message.get("code", 1000))
            else:
                raise WebSocketException(f"Unexpected message type: {message['type']}")
    
    async def receive_bytes(self) -> bytes:
        """Receive binary data."""
        if self._state != WebSocketState.CONNECTED:
            raise WebSocketException("WebSocket is not connected")
        
        if self._websocket:
            return await self._websocket.receive_bytes()
        else:
            message = await self.receive()
            if message["type"] == "websocket.receive":
                if "bytes" in message:
                    return message["bytes"]
                else:
                    raise WebSocketException("Expected binary message")
            elif message["type"] == "websocket.disconnect":
                self._state = WebSocketState.DISCONNECTED
                raise WebSocketDisconnect(message.get("code", 1000))
            else:
                raise WebSocketException(f"Unexpected message type: {message['type']}")
    
    async def receive_json(self, mode: str = "text") -> Any:
        """Receive JSON data."""
        if mode == "text":
            data = await self.receive_text()
        elif mode == "binary":
            data = (await self.receive_bytes()).decode()
        else:
            raise ValueError("Mode must be 'text' or 'binary'")
        
        try:
            return json.loads(data)
        except json.JSONDecodeError as e:
            raise WebSocketException(f"Invalid JSON: {e}")
    
    async def iter_text(self):
        """Iterate over text messages."""
        try:
            while True:
                yield await self.receive_text()
        except WebSocketDisconnect:
            pass
    
    async def iter_bytes(self):
        """Iterate over binary messages."""
        try:
            while True:
                yield await self.receive_bytes()
        except WebSocketDisconnect:
            pass
    
    async def iter_json(self, mode: str = "text"):
        """Iterate over JSON messages."""
        try:
            while True:
                yield await self.receive_json(mode)
        except WebSocketDisconnect:
            pass


class WebSocketManager:
    """
    Manages WebSocket routes and connections.
    """
    
    def __init__(self):
        self._routes: Dict[str, Callable] = {}
        self._connections: Dict[str, List[WebSocket]] = {}
    
    def add_route(self, path: str, handler: Callable, **kwargs):
        """Add a WebSocket route."""
        self._routes[path] = {
            "handler": handler,
            "kwargs": kwargs,
        }
    
    def get_route(self, path: str) -> Optional[Dict[str, Any]]:
        """Get a WebSocket route."""
        return self._routes.get(path)
    
    async def handle_websocket(self, websocket: WebSocket, path: str):
        """Handle a WebSocket connection."""
        route = self.get_route(path)
        if not route:
            await websocket.close(code=1000, reason="Route not found")
            return
        
        handler = route["handler"]
        
        try:
            # Add to connections
            if path not in self._connections:
                self._connections[path] = []
            self._connections[path].append(websocket)
            
            # Call the handler
            if is_async_callable(handler):
                await handler(websocket)
            else:
                handler(websocket)
        
        except WebSocketDisconnect:
            pass
        except Exception as e:
            await websocket.close(code=1011, reason=f"Internal error: {str(e)}")
        finally:
            # Remove from connections
            if path in self._connections:
                try:
                    self._connections[path].remove(websocket)
                except ValueError:
                    pass
                
                # Clean up empty connection lists
                if not self._connections[path]:
                    del self._connections[path]
    
    def get_connections(self, path: str) -> List[WebSocket]:
        """Get all active connections for a path."""
        return self._connections.get(path, []).copy()
    
    async def broadcast(self, path: str, message: Any, mode: str = "text"):
        """Broadcast a message to all connections on a path."""
        connections = self.get_connections(path)
        
        if not connections:
            return
        
        # Send to all connections
        tasks = []
        for websocket in connections:
            if websocket.state == WebSocketState.CONNECTED:
                if mode == "text":
                    if isinstance(message, str):
                        task = websocket.send_text(message)
                    else:
                        task = websocket.send_json(message)
                elif mode == "bytes":
                    if isinstance(message, bytes):
                        task = websocket.send_bytes(message)
                    else:
                        task = websocket.send_bytes(str(message).encode())
                else:
                    continue
                
                tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def get_connection_count(self, path: str) -> int:
        """Get the number of active connections for a path."""
        return len(self._connections.get(path, []))
    
    def get_all_connections(self) -> Dict[str, List[WebSocket]]:
        """Get all active connections."""
        return self._connections.copy()
    
    async def disconnect_all(self, path: str, code: int = 1000, reason: str = ""):
        """Disconnect all connections on a path."""
        connections = self.get_connections(path)
        
        tasks = []
        for websocket in connections:
            if websocket.state == WebSocketState.CONNECTED:
                tasks.append(websocket.close(code, reason))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
