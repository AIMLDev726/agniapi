"""
WebSocket example using Agni API framework.
Demonstrates real-time communication capabilities.
"""

import asyncio
import json
from typing import Dict, List
from datetime import datetime

from agniapi import AgniAPI
from agniapi.websockets import WebSocket, WebSocketDisconnect
from agniapi.response import HTMLResponse


# Create the application
app = AgniAPI(
    title="WebSocket Example",
    description="Real-time communication with WebSockets",
    version="1.0.0"
)

# Connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.rooms: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, room: str = "general"):
        """Connect a WebSocket to a room."""
        await websocket.accept()
        self.active_connections.append(websocket)
        
        if room not in self.rooms:
            self.rooms[room] = []
        self.rooms[room].append(websocket)
        
        # Notify room about new connection
        await self.broadcast_to_room(
            room,
            {
                "type": "user_joined",
                "message": "A user joined the room",
                "timestamp": datetime.now().isoformat(),
                "room": room,
                "connections": len(self.rooms[room])
            },
            exclude=websocket
        )
    
    def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket from all rooms."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        # Remove from all rooms
        for room, connections in self.rooms.items():
            if websocket in connections:
                connections.remove(websocket)
                # Notify room about disconnection
                asyncio.create_task(
                    self.broadcast_to_room(
                        room,
                        {
                            "type": "user_left",
                            "message": "A user left the room",
                            "timestamp": datetime.now().isoformat(),
                            "room": room,
                            "connections": len(connections)
                        }
                    )
                )
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific WebSocket."""
        try:
            await websocket.send_json(message)
        except:
            self.disconnect(websocket)
    
    async def broadcast_to_room(self, room: str, message: dict, exclude: WebSocket = None):
        """Broadcast a message to all connections in a room."""
        if room not in self.rooms:
            return
        
        disconnected = []
        for connection in self.rooms[room]:
            if connection == exclude:
                continue
            
            try:
                await connection.send_json(message)
            except:
                disconnected.append(connection)
        
        # Clean up disconnected connections
        for connection in disconnected:
            self.disconnect(connection)
    
    async def broadcast_to_all(self, message: dict):
        """Broadcast a message to all active connections."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                disconnected.append(connection)
        
        # Clean up disconnected connections
        for connection in disconnected:
            self.disconnect(connection)
    
    def get_room_info(self, room: str) -> dict:
        """Get information about a room."""
        return {
            "room": room,
            "connections": len(self.rooms.get(room, [])),
            "active": room in self.rooms
        }
    
    def get_stats(self) -> dict:
        """Get connection statistics."""
        return {
            "total_connections": len(self.active_connections),
            "rooms": {room: len(connections) for room, connections in self.rooms.items()},
            "timestamp": datetime.now().isoformat()
        }


# Global connection manager
manager = ConnectionManager()


# Regular HTTP endpoints
@app.get("/")
async def get_chat_page():
    """Serve the chat page."""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>WebSocket Chat Example</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            #messages { border: 1px solid #ccc; height: 400px; overflow-y: scroll; padding: 10px; margin: 10px 0; }
            #messageInput { width: 70%; padding: 10px; }
            #sendButton { padding: 10px 20px; }
            .message { margin: 5px 0; padding: 5px; border-radius: 5px; }
            .user-message { background-color: #e3f2fd; }
            .system-message { background-color: #f3e5f5; font-style: italic; }
            .error-message { background-color: #ffebee; color: #c62828; }
            #roomSelect { padding: 10px; margin: 10px 0; }
        </style>
    </head>
    <body>
        <h1>WebSocket Chat Example</h1>
        
        <div>
            <label for="roomSelect">Room:</label>
            <select id="roomSelect">
                <option value="general">General</option>
                <option value="tech">Tech</option>
                <option value="random">Random</option>
            </select>
            <button onclick="changeRoom()">Change Room</button>
        </div>
        
        <div id="messages"></div>
        
        <div>
            <input type="text" id="messageInput" placeholder="Type your message..." onkeypress="handleKeyPress(event)">
            <button id="sendButton" onclick="sendMessage()">Send</button>
        </div>
        
        <div>
            <button onclick="requestStats()">Get Stats</button>
            <button onclick="pingServer()">Ping</button>
        </div>

        <script>
            let ws = null;
            let currentRoom = 'general';
            
            function connect() {
                ws = new WebSocket(`ws://localhost:8000/ws/${currentRoom}`);
                
                ws.onopen = function(event) {
                    addMessage('Connected to room: ' + currentRoom, 'system');
                };
                
                ws.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    addMessage(JSON.stringify(data, null, 2), 'user');
                };
                
                ws.onclose = function(event) {
                    addMessage('Disconnected from server', 'system');
                };
                
                ws.onerror = function(error) {
                    addMessage('WebSocket error: ' + error, 'error');
                };
            }
            
            function addMessage(message, type = 'user') {
                const messages = document.getElementById('messages');
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${type}-message`;
                messageDiv.innerHTML = `<pre>${message}</pre>`;
                messages.appendChild(messageDiv);
                messages.scrollTop = messages.scrollHeight;
            }
            
            function sendMessage() {
                const input = document.getElementById('messageInput');
                const message = input.value.trim();
                
                if (message && ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({
                        type: 'chat',
                        message: message,
                        timestamp: new Date().toISOString()
                    }));
                    input.value = '';
                }
            }
            
            function handleKeyPress(event) {
                if (event.key === 'Enter') {
                    sendMessage();
                }
            }
            
            function changeRoom() {
                const roomSelect = document.getElementById('roomSelect');
                const newRoom = roomSelect.value;
                
                if (newRoom !== currentRoom) {
                    if (ws) {
                        ws.close();
                    }
                    currentRoom = newRoom;
                    connect();
                }
            }
            
            function requestStats() {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({
                        type: 'get_stats'
                    }));
                }
            }
            
            function pingServer() {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({
                        type: 'ping',
                        timestamp: new Date().toISOString()
                    }));
                }
            }
            
            // Connect on page load
            connect();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/stats")
async def get_stats():
    """Get WebSocket connection statistics."""
    return manager.get_stats()


@app.get("/rooms/{room}/info")
async def get_room_info(room: str):
    """Get information about a specific room."""
    return manager.get_room_info(room)


# WebSocket endpoints
@app.websocket("/ws/{room}")
async def websocket_endpoint(websocket: WebSocket, room: str):
    """Main WebSocket endpoint for chat rooms."""
    await manager.connect(websocket, room)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            message_type = data.get("type", "unknown")
            
            if message_type == "chat":
                # Broadcast chat message to room
                chat_message = {
                    "type": "chat",
                    "message": data.get("message", ""),
                    "timestamp": data.get("timestamp", datetime.now().isoformat()),
                    "room": room
                }
                await manager.broadcast_to_room(room, chat_message)
            
            elif message_type == "ping":
                # Respond to ping
                pong_message = {
                    "type": "pong",
                    "timestamp": datetime.now().isoformat(),
                    "original_timestamp": data.get("timestamp")
                }
                await manager.send_personal_message(pong_message, websocket)
            
            elif message_type == "get_stats":
                # Send statistics
                stats = manager.get_stats()
                stats["type"] = "stats"
                await manager.send_personal_message(stats, websocket)
            
            elif message_type == "broadcast":
                # Admin broadcast to all rooms (if authorized)
                if data.get("admin_key") == "admin123":  # Simple auth
                    broadcast_message = {
                        "type": "admin_broadcast",
                        "message": data.get("message", ""),
                        "timestamp": datetime.now().isoformat()
                    }
                    await manager.broadcast_to_all(broadcast_message)
                else:
                    error_message = {
                        "type": "error",
                        "message": "Unauthorized broadcast attempt",
                        "timestamp": datetime.now().isoformat()
                    }
                    await manager.send_personal_message(error_message, websocket)
            
            else:
                # Unknown message type
                error_message = {
                    "type": "error",
                    "message": f"Unknown message type: {message_type}",
                    "timestamp": datetime.now().isoformat()
                }
                await manager.send_personal_message(error_message, websocket)
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@app.websocket("/ws/echo")
async def echo_websocket(websocket: WebSocket):
    """Simple echo WebSocket for testing."""
    await websocket.accept()
    
    try:
        while True:
            # Echo back whatever is received
            data = await websocket.receive_text()
            echo_response = {
                "type": "echo",
                "original": data,
                "timestamp": datetime.now().isoformat()
            }
            await websocket.send_json(echo_response)
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"Echo WebSocket error: {e}")


@app.websocket("/ws/notifications")
async def notifications_websocket(websocket: WebSocket):
    """WebSocket for sending periodic notifications."""
    await websocket.accept()
    
    try:
        # Send welcome message
        welcome = {
            "type": "notification",
            "message": "Connected to notifications stream",
            "timestamp": datetime.now().isoformat()
        }
        await websocket.send_json(welcome)
        
        # Send periodic notifications
        counter = 0
        while True:
            await asyncio.sleep(10)  # Wait 10 seconds
            counter += 1
            
            notification = {
                "type": "notification",
                "message": f"Periodic notification #{counter}",
                "timestamp": datetime.now().isoformat(),
                "counter": counter
            }
            await websocket.send_json(notification)
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"Notifications WebSocket error: {e}")


if __name__ == "__main__":
    print("Starting WebSocket Example Server...")
    print("Open http://127.0.0.1:8000 in your browser to test the chat")
    print("WebSocket endpoints:")
    print("  - /ws/{room} - Chat rooms")
    print("  - /ws/echo - Echo server")
    print("  - /ws/notifications - Notification stream")
    
    app.run(host="127.0.0.1", port=8000, debug=True)
