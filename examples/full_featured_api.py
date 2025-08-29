"""
Full-featured API example using Agni API framework.
Demonstrates all major features in a comprehensive application.
"""

import asyncio
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

from agniapi import AgniAPI, Blueprint, HTTPException, Depends, mcp_tool, mcp_resource
from agniapi.security import HTTPBearer, JWTManager
from agniapi.middleware import CORSMiddleware, RequestLoggingMiddleware
from agniapi.websockets import WebSocket, WebSocketDisconnect
from agniapi.response import JSONResponse, HTMLResponse
from agniapi.testing import TestClient


# Pydantic models
class User(BaseModel):
    id: int
    username: str
    email: str  # Using str instead of EmailStr to avoid email-validator dependency
    is_active: bool = True


class Post(BaseModel):
    id: int
    title: str
    content: str
    author_id: int
    created_at: datetime
    published: bool = False


class Comment(BaseModel):
    id: int
    content: str
    post_id: int
    author_id: int
    created_at: datetime


class CreatePost(BaseModel):
    title: str
    content: str


class CreateComment(BaseModel):
    content: str


# Create the main application
app = AgniAPI(
    title="Full-Featured API",
    description="Comprehensive demonstration of Agni API features",
    version="2.0.0",
    mcp_enabled=True,
    mcp_server_name="full-featured-server"
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestLoggingMiddleware)

# Security setup
security = HTTPBearer()
jwt_manager = JWTManager("super-secret-key")

# Mock data
users_db = [
    User(id=1, username="alice", email="alice@aimldev726.com"),
    User(id=2, username="bob", email="bob@aimldev726.com"),
    User(id=3, username="charlie", email="charlie@aimldev726.com"),
]

posts_db = [
    Post(
        id=1,
        title="Welcome to Agni API",
        content="This is the first post on our new API platform!",
        author_id=1,
        created_at=datetime.now(),
        published=True
    ),
    Post(
        id=2,
        title="Building Modern APIs",
        content="Learn how to build APIs with Agni API framework.",
        author_id=2,
        created_at=datetime.now(),
        published=True
    ),
]

comments_db = [
    Comment(
        id=1,
        content="Great introduction!",
        post_id=1,
        author_id=2,
        created_at=datetime.now()
    ),
    Comment(
        id=2,
        content="Looking forward to more content.",
        post_id=1,
        author_id=3,
        created_at=datetime.now()
    ),
]

# WebSocket connections
websocket_connections = []


# Dependencies
async def get_current_user(token: str = Depends(security)) -> User:
    """Get current user from JWT token."""
    try:
        payload = jwt_manager.verify_token(token)
        user_id = payload.get("user_id")
        user = next((u for u in users_db if u.id == user_id), None)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_user_by_id(user_id: int) -> User:
    """Get user by ID."""
    user = next((u for u in users_db if u.id == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def get_post_by_id(post_id: int) -> Post:
    """Get post by ID."""
    post = next((p for p in posts_db if p.id == post_id), None)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


# MCP Tools
@mcp_tool("get_user_stats", "Get user statistics")
async def get_user_stats(user_id: int = None) -> dict:
    """Get statistics for a user or all users."""
    if user_id:
        user = next((u for u in users_db if u.id == user_id), None)
        if not user:
            return {"error": "User not found"}
        
        user_posts = [p for p in posts_db if p.author_id == user_id]
        user_comments = [c for c in comments_db if c.author_id == user_id]
        
        return {
            "user": user.model_dump(),
            "posts_count": len(user_posts),
            "comments_count": len(user_comments),
            "published_posts": len([p for p in user_posts if p.published])
        }
    else:
        return {
            "total_users": len(users_db),
            "total_posts": len(posts_db),
            "total_comments": len(comments_db),
            "published_posts": len([p for p in posts_db if p.published])
        }


@mcp_tool("search_content", "Search posts and comments")
async def search_content(query: str, content_type: str = "all") -> dict:
    """Search through posts and comments."""
    results = {"posts": [], "comments": []}
    
    if content_type in ["all", "posts"]:
        for post in posts_db:
            if query.lower() in post.title.lower() or query.lower() in post.content.lower():
                results["posts"].append(post.model_dump())
    
    if content_type in ["all", "comments"]:
        for comment in comments_db:
            if query.lower() in comment.content.lower():
                results["comments"].append(comment.model_dump())
    
    return {
        "query": query,
        "results": results,
        "total_found": len(results["posts"]) + len(results["comments"])
    }


# MCP Resources
@mcp_resource("database://users", "User Database", "Complete user database")
async def users_resource() -> str:
    """Provide access to user database."""
    return JSONResponse([user.model_dump() for user in users_db]).body.decode()


@mcp_resource("database://posts", "Posts Database", "All posts and metadata")
async def posts_resource() -> str:
    """Provide access to posts database."""
    return JSONResponse([post.model_dump() for post in posts_db]).body.decode()


# Main app routes
@app.get("/")
async def root():
    """Root endpoint with API overview."""
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Full-Featured API</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .feature { margin: 20px 0; padding: 15px; border-left: 4px solid #007acc; }
            .endpoint { background: #f5f5f5; padding: 10px; margin: 5px 0; }
        </style>
    </head>
    <body>
        <h1>Full-Featured API</h1>
        <p>Comprehensive demonstration of Agni API framework capabilities.</p>
        
        <div class="feature">
            <h3>🔥 Core Features</h3>
            <ul>
                <li>Flask-style blueprints with async support</li>
                <li>FastAPI-style type validation</li>
                <li>Dependency injection system</li>
                <li>WebSocket real-time communication</li>
                <li>Built-in MCP server capabilities</li>
            </ul>
        </div>
        
        <div class="feature">
            <h3>📚 API Endpoints</h3>
            <div class="endpoint">GET /docs - Interactive API documentation</div>
            <div class="endpoint">GET /users - List all users</div>
            <div class="endpoint">GET /posts - List all posts</div>
            <div class="endpoint">POST /auth/login - User authentication</div>
            <div class="endpoint">WS /ws/chat - Real-time chat</div>
        </div>
        
        <div class="feature">
            <h3>🤖 MCP Integration</h3>
            <div class="endpoint">Tool: get_user_stats - User analytics</div>
            <div class="endpoint">Tool: search_content - Content search</div>
            <div class="endpoint">Resource: database://users - User data</div>
            <div class="endpoint">Resource: database://posts - Posts data</div>
        </div>
        
        <div class="feature">
            <h3>🔗 Quick Links</h3>
            <a href="/docs">API Documentation</a> |
            <a href="/users">Users API</a> |
            <a href="/posts">Posts API</a> |
            <a href="/ws-demo">WebSocket Demo</a>
        </div>
    </body>
    </html>
    """)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "features": {
            "mcp_enabled": app.mcp_enabled,
            "websockets": True,
            "authentication": True,
            "blueprints": True
        }
    }


# Authentication
@app.post("/auth/login")
async def login(username: str, password: str):
    """Simple login endpoint."""
    user = next((u for u in users_db if u.username == username), None)
    if not user or password != "password123":  # Simple auth for demo
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = jwt_manager.create_token({"user_id": user.id, "username": user.username})
    return {"access_token": token, "token_type": "bearer", "user": user}


# Users Blueprint
users_bp = Blueprint("users", __name__, url_prefix="/users", tags=["Users"])

@users_bp.get("/", response_model=List[User])
async def list_users(skip: int = 0, limit: int = 10):
    """List all users with pagination."""
    return users_db[skip:skip + limit]

@users_bp.get("/{user_id}", response_model=User)
async def get_user(user_id: int):
    """Get a specific user."""
    return get_user_by_id(user_id)

@users_bp.get("/{user_id}/posts", response_model=List[Post])
async def get_user_posts(user_id: int):
    """Get posts by a specific user."""
    user = get_user_by_id(user_id)
    return [p for p in posts_db if p.author_id == user.id]

app.register_blueprint(users_bp)


# Posts Blueprint
posts_bp = Blueprint("posts", __name__, url_prefix="/posts", tags=["Posts"])

@posts_bp.get("/", response_model=List[Post])
async def list_posts(published_only: bool = True):
    """List all posts."""
    if published_only:
        return [p for p in posts_db if p.published]
    return posts_db

@posts_bp.get("/{post_id}", response_model=Post)
async def get_post(post_id: int):
    """Get a specific post."""
    return get_post_by_id(post_id)

@posts_bp.post("/", response_model=Post, status_code=201)
async def create_post(post_data: CreatePost, current_user: User = Depends(get_current_user)):
    """Create a new post."""
    new_id = max([p.id for p in posts_db], default=0) + 1
    new_post = Post(
        id=new_id,
        title=post_data.title,
        content=post_data.content,
        author_id=current_user.id,
        created_at=datetime.now()
    )
    posts_db.append(new_post)
    return new_post

@posts_bp.get("/{post_id}/comments", response_model=List[Comment])
async def get_post_comments(post_id: int):
    """Get comments for a post."""
    post = get_post_by_id(post_id)
    return [c for c in comments_db if c.post_id == post.id]

@posts_bp.post("/{post_id}/comments", response_model=Comment, status_code=201)
async def create_comment(
    post_id: int,
    comment_data: CreateComment,
    current_user: User = Depends(get_current_user)
):
    """Create a comment on a post."""
    post = get_post_by_id(post_id)
    new_id = max([c.id for c in comments_db], default=0) + 1
    new_comment = Comment(
        id=new_id,
        content=comment_data.content,
        post_id=post.id,
        author_id=current_user.id,
        created_at=datetime.now()
    )
    comments_db.append(new_comment)
    return new_comment

app.register_blueprint(posts_bp)


# WebSocket endpoints
@app.get("/ws-demo")
async def websocket_demo():
    """WebSocket demo page."""
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>WebSocket Demo</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            #messages { border: 1px solid #ccc; height: 300px; overflow-y: scroll; padding: 10px; }
            #messageInput { width: 70%; padding: 10px; }
            button { padding: 10px 20px; }
        </style>
    </head>
    <body>
        <h1>WebSocket Chat Demo</h1>
        <div id="messages"></div>
        <input type="text" id="messageInput" placeholder="Type a message...">
        <button onclick="sendMessage()">Send</button>
        <button onclick="disconnect()">Disconnect</button>
        
        <script>
            const ws = new WebSocket('ws://localhost:8000/ws/chat');
            const messages = document.getElementById('messages');
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                messages.innerHTML += '<div>' + JSON.stringify(data, null, 2) + '</div>';
                messages.scrollTop = messages.scrollHeight;
            };
            
            function sendMessage() {
                const input = document.getElementById('messageInput');
                ws.send(JSON.stringify({type: 'message', content: input.value}));
                input.value = '';
            }
            
            function disconnect() {
                ws.close();
            }
        </script>
    </body>
    </html>
    """)


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket chat endpoint."""
    await websocket.accept()
    websocket_connections.append(websocket)
    
    # Send welcome message
    await websocket.send_json({
        "type": "system",
        "message": "Connected to chat",
        "timestamp": datetime.now().isoformat(),
        "connections": len(websocket_connections)
    })
    
    try:
        while True:
            data = await websocket.receive_json()
            
            # Broadcast message to all connections
            message = {
                "type": "chat",
                "content": data.get("content", ""),
                "timestamp": datetime.now().isoformat(),
                "connections": len(websocket_connections)
            }
            
            # Send to all connected clients
            for connection in websocket_connections[:]:
                try:
                    await connection.send_json(message)
                except:
                    websocket_connections.remove(connection)
    
    except WebSocketDisconnect:
        websocket_connections.remove(websocket)


# Analytics endpoints
@app.get("/analytics/overview")
async def analytics_overview():
    """Get analytics overview."""
    return {
        "users": len(users_db),
        "posts": len(posts_db),
        "comments": len(comments_db),
        "published_posts": len([p for p in posts_db if p.published]),
        "active_websockets": len(websocket_connections),
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    print("🔥 Starting Full-Featured API Server...")
    print("📊 Features enabled:")
    print("  ✅ REST API with type validation")
    print("  ✅ Blueprint-based organization")
    print("  ✅ JWT Authentication")
    print("  ✅ WebSocket real-time chat")
    print("  ✅ MCP server integration")
    print("  ✅ CORS middleware")
    print("  ✅ Request logging")
    print("  ✅ OpenAPI documentation")
    print("\n🌐 Access points:")
    print("  📖 Documentation: http://127.0.0.1:8000/docs")
    print("  🏠 Homepage: http://127.0.0.1:8000")
    print("  💬 WebSocket Demo: http://127.0.0.1:8000/ws-demo")
    print("  📊 Analytics: http://127.0.0.1:8000/analytics/overview")
    
    app.run(host="127.0.0.1", port=8000, debug=True)
