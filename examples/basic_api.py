"""
Basic REST API example using Agni API framework.
Demonstrates CRUD operations with type validation.
"""

from typing import List, Optional
from pydantic import BaseModel

from agniapi import AgniAPI, HTTPException, Depends
from agniapi.response import JSONResponse


# Pydantic models
class UserBase(BaseModel):
    name: str
    email: str
    age: int


class UserCreate(UserBase):
    pass


class User(UserBase):
    id: int
    
    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    age: Optional[int] = None


# Create the application
app = AgniAPI(
    title="Basic API Example",
    description="A simple CRUD API demonstrating Agni API features",
    version="1.0.0"
)

# In-memory database
users_db: List[User] = [
    User(id=1, name="Alice", email="alice@aimldev726.com", age=30),
    User(id=2, name="Bob", email="bob@aimldev726.com", age=25),
]
next_id = 3


# Dependency functions

def get_database():
    return {"connected": True, "users": users_db}

def get_user_by_id(user_id: int) -> User:
    """Get user by ID or raise 404."""
    for user in users_db:
        if user.id == user_id:
            return user
    raise HTTPException(status_code=404, detail="User not found")


# Routes
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to Basic API Example",
        "docs": "/docs",
        "users_count": len(users_db)
    }


@app.get("/health", tags=["Health"])
async def health_check(db=Depends(get_database)):
    """Health check endpoint."""
    return {
        "status": "healthy",
        "database": db["connected"],
        "timestamp": "2024-01-01T00:00:00Z"
    }


@app.get("/users", response_model=List[User], tags=["Users"])
async def list_users(
    skip: int = 0,
    limit: int = 10,
    db=Depends(get_database)
):
    """List all users with pagination."""
    return users_db[skip:skip + limit]


@app.get("/users/{user_id}", response_model=User, tags=["Users"])
async def get_user(user_id: int):
    """Get a specific user by ID."""
    return get_user_by_id(user_id)


@app.post("/users", response_model=User, status_code=201, tags=["Users"])
async def create_user(user: UserCreate, db=Depends(get_database)):
    """Create a new user."""
    global next_id
    
    # Check if email already exists
    for existing_user in users_db:
        if existing_user.email == user.email:
            raise HTTPException(
                status_code=400,
                detail="Email already registered"
            )
    
    # Create new user
    new_user = User(id=next_id, **user.model_dump())
    users_db.append(new_user)
    next_id += 1
    
    return new_user


@app.put("/users/{user_id}", response_model=User, tags=["Users"])
async def update_user(user_id: int, user_update: UserUpdate):
    """Update an existing user."""
    user = get_user_by_id(user_id)
    
    # Update fields
    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    return user


@app.delete("/users/{user_id}", tags=["Users"])
async def delete_user(user_id: int):
    """Delete a user."""
    user = get_user_by_id(user_id)
    users_db.remove(user)
    
    return {"message": f"User {user_id} deleted successfully"}


@app.get("/users/{user_id}/profile", tags=["Users"])
async def get_user_profile(user_id: int):
    """Get user profile with additional information."""
    user = get_user_by_id(user_id)
    
    return {
        "user": user,
        "profile": {
            "member_since": "2024-01-01",
            "posts_count": 42,
            "followers": 123
        }
    }


@app.exception_handler(404)
def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": "The requested resource was not found",
            "path": request.path
        }
    )

@app.exception_handler(400)
def bad_request_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={
            "error": "Bad Request",
            "message": str(exc.detail) if hasattr(exc, 'detail') else "Invalid request",
            "path": request.path
        }
    )




if __name__ == "__main__":
    # Run the development server
    app.run(host="127.0.0.1", port=8000, debug=True)
