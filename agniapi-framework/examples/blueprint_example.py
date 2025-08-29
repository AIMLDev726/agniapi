"""
Blueprint example using Agni API framework.
Demonstrates modular application organization with Flask-style blueprints.
"""

from typing import List, Optional
from pydantic import BaseModel

from agniapi import AgniAPI, Blueprint, HTTPException, Depends
from agniapi.security import HTTPBearer, JWTManager
from agniapi.response import JSONResponse


# Pydantic models
class User(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool = True


class Post(BaseModel):
    id: int
    title: str
    content: str
    author_id: int
    published: bool = False


class Comment(BaseModel):
    id: int
    content: str
    post_id: int
    author_id: int


# Create the main application
app = AgniAPI(
    title="Blueprint Example",
    description="Modular API using blueprints",
    version="1.0.0"
)

# Security setup
security = HTTPBearer()
jwt_manager = JWTManager("your-secret-key-here")

# Mock data
users_db = [
    User(id=1, username="alice", email="alice@example.com"),
    User(id=2, username="bob", email="bob@example.com"),
    User(id=3, username="charlie", email="charlie@example.com", is_active=False),
]

posts_db = [
    Post(id=1, title="First Post", content="Hello World!", author_id=1, published=True),
    Post(id=2, title="Second Post", content="Another post", author_id=2, published=True),
    Post(id=3, title="Draft Post", content="Work in progress", author_id=1, published=False),
]

comments_db = [
    Comment(id=1, content="Great post!", post_id=1, author_id=2),
    Comment(id=2, content="Thanks for sharing", post_id=1, author_id=3),
    Comment(id=3, content="Interesting perspective", post_id=2, author_id=1),
]


# Dependency functions
async def get_current_user(token: str = Depends(security)) -> User:
    """Get current user from JWT token."""
    try:
        payload = jwt_manager.verify_token(token)
        user_id = payload.get("user_id")
        
        user = next((u for u in users_db if u.id == user_id), None)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        if not user.is_active:
            raise HTTPException(status_code=401, detail="User is inactive")
        
        return user
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_user_by_id(user_id: int) -> User:
    """Get user by ID or raise 404."""
    user = next((u for u in users_db if u.id == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def get_post_by_id(post_id: int) -> Post:
    """Get post by ID or raise 404."""
    post = next((p for p in posts_db if p.id == post_id), None)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


# Auth Blueprint
auth_bp = Blueprint(
    "auth",
    __name__,
    url_prefix="/auth",
    tags=["Authentication"]
)


@auth_bp.post("/login")
async def login(username: str, password: str):
    """Login endpoint."""
    # Simple authentication (in real app, check password hash)
    user = next((u for u in users_db if u.username == username), None)
    
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create JWT token
    token = jwt_manager.create_token({"user_id": user.id, "username": user.username})
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user
    }


@auth_bp.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """Logout endpoint."""
    return {"message": f"User {current_user.username} logged out successfully"}


@auth_bp.get("/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return current_user


# Users Blueprint
users_bp = Blueprint(
    "users",
    __name__,
    url_prefix="/users",
    tags=["Users"]
)


@users_bp.get("/", response_model=List[User])
async def list_users(skip: int = 0, limit: int = 10):
    """List all users."""
    return users_db[skip:skip + limit]


@users_bp.get("/{user_id}", response_model=User)
async def get_user(user_id: int):
    """Get a specific user."""
    return get_user_by_id(user_id)


@users_bp.get("/{user_id}/posts", response_model=List[Post])
async def get_user_posts(user_id: int, published_only: bool = True):
    """Get posts by a specific user."""
    user = get_user_by_id(user_id)
    
    user_posts = [p for p in posts_db if p.author_id == user.id]
    
    if published_only:
        user_posts = [p for p in user_posts if p.published]
    
    return user_posts


@users_bp.put("/{user_id}/activate")
async def activate_user(user_id: int, current_user: User = Depends(get_current_user)):
    """Activate a user (admin only)."""
    # Simple admin check (in real app, check user roles)
    if current_user.id != 1:  # Assume user 1 is admin
        raise HTTPException(status_code=403, detail="Admin access required")
    
    user = get_user_by_id(user_id)
    user.is_active = True
    
    return {"message": f"User {user.username} activated"}


# Posts Blueprint
posts_bp = Blueprint(
    "posts",
    __name__,
    url_prefix="/posts",
    tags=["Posts"]
)


@posts_bp.get("/", response_model=List[Post])
async def list_posts(published_only: bool = True, skip: int = 0, limit: int = 10):
    """List all posts."""
    filtered_posts = posts_db
    
    if published_only:
        filtered_posts = [p for p in posts_db if p.published]
    
    return filtered_posts[skip:skip + limit]


@posts_bp.get("/{post_id}", response_model=Post)
async def get_post(post_id: int):
    """Get a specific post."""
    return get_post_by_id(post_id)


@posts_bp.post("/", response_model=Post, status_code=201)
async def create_post(
    title: str,
    content: str,
    current_user: User = Depends(get_current_user)
):
    """Create a new post."""
    new_id = max([p.id for p in posts_db], default=0) + 1
    
    new_post = Post(
        id=new_id,
        title=title,
        content=content,
        author_id=current_user.id
    )
    
    posts_db.append(new_post)
    return new_post


@posts_bp.put("/{post_id}", response_model=Post)
async def update_post(
    post_id: int,
    title: Optional[str] = None,
    content: Optional[str] = None,
    published: Optional[bool] = None,
    current_user: User = Depends(get_current_user)
):
    """Update a post."""
    post = get_post_by_id(post_id)
    
    # Check if user owns the post
    if post.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this post")
    
    # Update fields
    if title is not None:
        post.title = title
    if content is not None:
        post.content = content
    if published is not None:
        post.published = published
    
    return post


@posts_bp.delete("/{post_id}")
async def delete_post(post_id: int, current_user: User = Depends(get_current_user)):
    """Delete a post."""
    post = get_post_by_id(post_id)
    
    # Check if user owns the post or is admin
    if post.author_id != current_user.id and current_user.id != 1:
        raise HTTPException(status_code=403, detail="Not authorized to delete this post")
    
    posts_db.remove(post)
    
    # Also remove associated comments
    global comments_db
    comments_db = [c for c in comments_db if c.post_id != post_id]
    
    return {"message": f"Post {post_id} deleted successfully"}


# Comments Blueprint
comments_bp = Blueprint(
    "comments",
    __name__,
    url_prefix="/posts/{post_id}/comments",
    tags=["Comments"]
)


@comments_bp.get("/", response_model=List[Comment])
async def list_comments(post_id: int):
    """List comments for a post."""
    # Verify post exists
    get_post_by_id(post_id)
    
    post_comments = [c for c in comments_db if c.post_id == post_id]
    return post_comments


@comments_bp.post("/", response_model=Comment, status_code=201)
async def create_comment(
    post_id: int,
    content: str,
    current_user: User = Depends(get_current_user)
):
    """Create a comment on a post."""
    # Verify post exists
    get_post_by_id(post_id)
    
    new_id = max([c.id for c in comments_db], default=0) + 1
    
    new_comment = Comment(
        id=new_id,
        content=content,
        post_id=post_id,
        author_id=current_user.id
    )
    
    comments_db.append(new_comment)
    return new_comment


@comments_bp.delete("/{comment_id}")
async def delete_comment(
    post_id: int,
    comment_id: int,
    current_user: User = Depends(get_current_user)
):
    """Delete a comment."""
    # Verify post exists
    get_post_by_id(post_id)
    
    comment = next((c for c in comments_db if c.id == comment_id and c.post_id == post_id), None)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    # Check if user owns the comment or is admin
    if comment.author_id != current_user.id and current_user.id != 1:
        raise HTTPException(status_code=403, detail="Not authorized to delete this comment")
    
    comments_db.remove(comment)
    return {"message": f"Comment {comment_id} deleted successfully"}


# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(users_bp)
app.register_blueprint(posts_bp)
app.register_blueprint(comments_bp)


# Main app routes
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Blueprint Example API",
        "blueprints": ["auth", "users", "posts", "comments"],
        "endpoints": {
            "auth": "/auth",
            "users": "/users",
            "posts": "/posts",
            "docs": "/docs"
        }
    }


@app.get("/stats")
async def get_stats():
    """Get API statistics."""
    return {
        "users": len(users_db),
        "active_users": len([u for u in users_db if u.is_active]),
        "posts": len(posts_db),
        "published_posts": len([p for p in posts_db if p.published]),
        "comments": len(comments_db)
    }


if __name__ == "__main__":
    print("Starting Blueprint Example Server...")
    print("Available endpoints:")
    print("  - POST /auth/login - Login")
    print("  - GET /auth/me - Current user info")
    print("  - GET /users - List users")
    print("  - GET /posts - List posts")
    print("  - POST /posts - Create post (requires auth)")
    print("  - GET /docs - API documentation")
    
    app.run(host="127.0.0.1", port=8000, debug=True)
