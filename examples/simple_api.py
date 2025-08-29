"""
Simple AgniAPI Example - Common REST API Endpoints

This example demonstrates:
- Basic CRUD operations
- Request/Response models with Pydantic
- OpenAPI documentation
- Error handling
- Common API patterns
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

from agniapi import AgniAPI, HTTPException, JSONResponse

# Create the AgniAPI application
app = AgniAPI(
    title="Simple API Example",
    description="A simple REST API demonstrating common endpoints",
    version="1.0.0",
    docs_url="/docs",  # OpenAPI documentation URL
    redoc_url="/redoc"  # ReDoc documentation URL
)

# Pydantic models for request/response
class User(BaseModel):
    id: Optional[int] = None
    name: str
    email: str
    age: Optional[int] = None
    created_at: Optional[datetime] = None

class UserCreate(BaseModel):
    name: str
    email: str
    age: Optional[int] = None

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    age: Optional[int] = None

class Message(BaseModel):
    message: str
    timestamp: datetime = datetime.utcnow()

# In-memory storage (replace with database in production)
users_db: List[User] = []
next_id = 1

# Root endpoint
@app.get("/", response_model=Message)
async def root():
    """Welcome endpoint"""
    return Message(message="Welcome to AgniAPI Simple Example!")

# Health check endpoint
@app.get("/health", response_model=Message)
async def health_check():
    """Health check endpoint"""
    return Message(message="API is healthy")

# Get all users
@app.get("/users", response_model=List[User])
async def get_users(skip: int = 0, limit: int = 10):
    """Get all users with pagination"""
    return users_db[skip:skip + limit]

# Get user by ID
@app.get("/users/{user_id}", response_model=User)
async def get_user(user_id: int):
    """Get a specific user by ID"""
    for user in users_db:
        if user.id == user_id:
            return user
    raise HTTPException(status_code=404, detail="User not found")

# Create new user
@app.post("/users", response_model=User, status_code=201)
async def create_user(user_data: UserCreate):
    """Create a new user"""
    global next_id
    
    # Check if email already exists
    for existing_user in users_db:
        if existing_user.email == user_data.email:
            raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    new_user = User(
        id=next_id,
        name=user_data.name,
        email=user_data.email,
        age=user_data.age,
        created_at=datetime.utcnow()
    )
    
    users_db.append(new_user)
    next_id += 1
    
    return new_user

# Update user
@app.put("/users/{user_id}", response_model=User)
async def update_user(user_id: int, user_data: UserUpdate):
    """Update an existing user"""
    for i, user in enumerate(users_db):
        if user.id == user_id:
            # Update only provided fields
            update_data = user_data.dict(exclude_unset=True)
            updated_user = user.copy(update=update_data)
            users_db[i] = updated_user
            return updated_user
    
    raise HTTPException(status_code=404, detail="User not found")

# Delete user
@app.delete("/users/{user_id}", response_model=Message)
async def delete_user(user_id: int):
    """Delete a user"""
    for i, user in enumerate(users_db):
        if user.id == user_id:
            users_db.pop(i)
            return Message(message=f"User {user_id} deleted successfully")
    
    raise HTTPException(status_code=404, detail="User not found")

# Search users
@app.get("/users/search", response_model=List[User])
async def search_users(q: str, limit: int = 10):
    """Search users by name or email"""
    results = []
    for user in users_db:
        if (q.lower() in user.name.lower() or 
            q.lower() in user.email.lower()):
            results.append(user)
            if len(results) >= limit:
                break
    return results

# Get user statistics
@app.get("/stats")
async def get_stats():
    """Get API statistics"""
    total_users = len(users_db)
    users_with_age = [u for u in users_db if u.age is not None]

    if users_with_age:
        avg_age = sum(user.age for user in users_with_age) / len(users_with_age)
    else:
        avg_age = 0

    return {
        "total_users": total_users,
        "average_age": round(avg_age, 2),
        "users_with_age": len(users_with_age),
        "timestamp": datetime.utcnow().isoformat()
    }

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Not found", "detail": str(exc.detail)}
    )

@app.exception_handler(400)
async def bad_request_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"error": "Bad request", "detail": str(exc.detail)}
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )

# Startup event to add sample data
@app.on_event("startup")
async def startup():
    """Add sample data on startup"""
    global next_id
    
    sample_users = [
        UserCreate(name="John Doe", email="john.doe@aimldev726.com", age=30),
        UserCreate(name="Jane Smith", email="jane.smith@aimldev726.com", age=25),
        UserCreate(name="Bob Johnson", email="bob.johnson@aimldev726.com", age=35),
    ]
    
    for user_data in sample_users:
        new_user = User(
            id=next_id,
            name=user_data.name,
            email=user_data.email,
            age=user_data.age,
            created_at=datetime.utcnow()
        )
        users_db.append(new_user)
        next_id += 1

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "simple_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
