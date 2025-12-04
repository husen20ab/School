import os
import secrets
import hashlib
from contextlib import asynccontextmanager
from typing import Dict, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

# --- MongoDB Connection ---
MONGODB_URI = os.environ.get("MONGODB_URI")
if not MONGODB_URI:
    raise ValueError("MONGODB_URI environment variable is not set")

client = AsyncIOMotorClient(MONGODB_URI)
db = client["school"]

SESSIONS: Dict[str, Dict[str, str]] = {}

def hash_password(password: str) -> str:
    """Hash password using SHA-256 (simple hashing for this app)"""
    return hashlib.sha256(password.encode()).hexdigest()

# --- Lifespan (connect once) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db = db
    try:
        # Test connection
        await client.admin.command('ping')
        print(f"Mongo connected to database: {db.name}")
    except Exception as e:
        print(f"MongoDB connection error: {e}")
        raise
    try:
        yield
    finally:
        client.close()
        print("Mongo connection closed")

app = FastAPI(
    title="School App",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
)


def _cors_origins() -> List[str]:
    # Default origins (always include Netlify domain)
    default_origins = [
        "https://school-logistics.netlify.app",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    
    env_value = os.getenv("CORS_ORIGINS", "")
    if env_value:
        origins = [origin.strip() for origin in env_value.split(",") if origin.strip()]
        if origins:
            # Merge with defaults, avoiding duplicates
            combined = list(set(default_origins + origins))
            print(f"CORS origins configured: {combined}")
            return combined
    
    print(f"CORS origins (defaults): {default_origins}")
    return default_origins


# CORS for local dev + configurable production domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Models ---
class StudentIn(BaseModel):
    name: str = Field(..., min_length=1)
    age: int = Field(..., ge=0)
    courses: Optional[List[str]] = Field(default_factory=list)

class StudentOut(BaseModel):
    id: str
    name: str
    age: int
    courses: Optional[List[str]] = Field(default_factory=list)
    owner_id: Optional[str] = None  # User ID who created this student
    owner_username: Optional[str] = None  # Username of owner (for admin view)


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1)


class SignupRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_]+$")
    password: str = Field(..., min_length=3, max_length=100)


class LoginResponse(BaseModel):
    token: str
    username: str
    role: str
    user_id: str  # MongoDB user _id


class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_]+$")
    password: str = Field(..., min_length=3, max_length=100)
    role: str = Field(..., pattern="^(admin|user)$")


class UserOut(BaseModel):
    id: str
    username: str
    role: str


class UpdateUserRequest(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50, pattern="^[a-zA-Z0-9_]+$")
    password: Optional[str] = Field(None, min_length=3, max_length=100)
    role: Optional[str] = Field(None, pattern="^(admin|user)$")


async def get_current_user(authorization: Optional[str] = Header(default=None)) -> Dict[str, str]:
    """
    Get current authenticated user from session token.
    Returns user info including user_id, username, and role from MongoDB.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    token = authorization.split(" ", 1)[1].strip()
    session = SESSIONS.get(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    # Fetch full user data from MongoDB to ensure we have user_id
    users_coll = db["users"]
    username = session.get("username")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    user_doc = await users_coll.find_one({"username": username})
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")
    
    return {
        "user_id": str(user_doc["_id"]),
        "username": user_doc["username"],
        "role": user_doc["role"],
        "token": token
    }

# Keep require_user as alias for backward compatibility
require_user = get_current_user


async def require_admin(user: Dict[str, str] = Depends(get_current_user)) -> Dict[str, str]:
    """Require admin role"""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return user

# --- Helpers ---
def oid(id_str: str) -> ObjectId:
    if not ObjectId.is_valid(id_str):
        raise HTTPException(status_code=404, detail="Student not found")
    return ObjectId(id_str)

def doc_to_out(doc: dict, owner_username: Optional[str] = None) -> StudentOut:
    """Convert MongoDB document to StudentOut model"""
    return StudentOut(
        id=str(doc["_id"]),
        name=doc.get("name", ""),
        age=doc.get("age", 0),
        courses=doc.get("courses", []),
        owner_id=str(doc.get("owner_id", "")) if doc.get("owner_id") else None,
        owner_username=owner_username,
    )


@app.post("/api/login", response_model=LoginResponse)
async def login(credentials: LoginRequest):
    users_coll = db["users"]
    # Normalize username (lowercase for consistency)
    username = credentials.username.strip().lower()
    user_doc = await users_coll.find_one({"username": username})
    
    if not user_doc:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    hashed_password = hash_password(credentials.password)
    if user_doc["password"] != hashed_password:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = secrets.token_hex(32)
    user_id = str(user_doc["_id"])
    session = {"username": username, "role": user_doc["role"], "user_id": user_id, "token": token}
    SESSIONS[token] = session
    return LoginResponse(token=token, username=username, role=user_doc["role"], user_id=user_id)


@app.post("/api/signup", response_model=LoginResponse)
async def signup(user_data: SignupRequest):
    users_coll = db["users"]
    
    # Normalize username (lowercase for consistency)
    username = user_data.username.strip().lower()
    
    # Check if username already exists
    existing = await users_coll.find_one({"username": username})
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Create new user with 'user' role by default
    hashed_password = hash_password(user_data.password)
    new_user = {
        "username": username,
        "password": hashed_password,
        "role": "user"
    }
    
    try:
        result = await users_coll.insert_one(new_user)
        if not result.inserted_id:
            raise HTTPException(status_code=500, detail="Failed to create user")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    # Auto-login after signup
    token = secrets.token_hex(32)
    user_id = str(result.inserted_id)
    session = {"username": username, "role": "user", "user_id": user_id, "token": token}
    SESSIONS[token] = session
    
    return LoginResponse(token=token, username=username, role="user", user_id=user_id)


@app.get("/health")
async def health(_: Dict[str, str] = Depends(require_admin)):
    try:
        # Test database connection
        await client.admin.command('ping')
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "error", "database": "disconnected", "error": str(e)}, 503


@app.get("/docs", include_in_schema=False)
async def custom_swagger(_: Dict[str, str] = Depends(require_admin)):
    return get_swagger_ui_html(openapi_url="/openapi.json", title="School App Docs")


@app.get("/redoc", include_in_schema=False)
async def custom_redoc(_: Dict[str, str] = Depends(require_admin)):
    return get_redoc_html(openapi_url="/openapi.json", title="School App ReDoc")


@app.post("/api/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(user_data: CreateUserRequest, _: Dict[str, str] = Depends(require_admin)):
    """Create a new user (admin only)"""
    users_coll = db["users"]
    
    # Normalize username (lowercase for consistency)
    username = user_data.username.strip().lower()
    
    # Check if username already exists
    existing = await users_coll.find_one({"username": username})
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Create new user with specified role
    hashed_password = hash_password(user_data.password)
    new_user = {
        "username": username,
        "password": hashed_password,
        "role": user_data.role
    }
    
    try:
        result = await users_coll.insert_one(new_user)
        if not result.inserted_id:
            raise HTTPException(status_code=500, detail="Failed to create user")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    return UserOut(id=str(result.inserted_id), username=username, role=user_data.role)


@app.get("/api/users", response_model=List[UserOut])
async def list_users(_: Dict[str, str] = Depends(require_admin)):
    """List all users (admin only)"""
    try:
        users_coll = db["users"]
        docs = await users_coll.find({}, {"password": 0}).to_list(length=None)
        return [UserOut(id=str(doc["_id"]), username=doc["username"], role=doc["role"]) for doc in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.put("/api/users/{user_id}", response_model=UserOut)
async def update_user(user_id: str, user_data: UpdateUserRequest, current_user: Dict[str, str] = Depends(require_admin)):
    """Update a user (admin only)"""
    users_coll = db["users"]
    
    # Check if user exists
    user_doc = await users_coll.find_one({"_id": ObjectId(user_id)})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Build update data
    update_data = {}
    if user_data.username is not None:
        new_username = user_data.username.strip().lower()
        # Check if new username is already taken (by another user)
        existing = await users_coll.find_one({"username": new_username, "_id": {"$ne": ObjectId(user_id)}})
        if existing:
            raise HTTPException(status_code=400, detail="Username already exists")
        update_data["username"] = new_username
    
    if user_data.password is not None:
        update_data["password"] = hash_password(user_data.password)
    
    if user_data.role is not None:
        update_data["role"] = user_data.role
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    try:
        result = await users_coll.update_one({"_id": ObjectId(user_id)}, {"$set": update_data})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Fetch updated user
        updated_doc = await users_coll.find_one({"_id": ObjectId(user_id)}, {"password": 0})
        return UserOut(id=str(updated_doc["_id"]), username=updated_doc["username"], role=updated_doc["role"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.delete("/api/users/{user_id}", status_code=status.HTTP_200_OK)
async def delete_user(user_id: str, current_user: Dict[str, str] = Depends(require_admin)):
    """Delete a user (admin only, cannot delete self)"""
    # Prevent admin from deleting themselves
    if user_id == current_user["user_id"]:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    try:
        users_coll = db["users"]
        result = await users_coll.delete_one({"_id": ObjectId(user_id)})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        return {"message": f"User deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# ---------- List students ----------
@app.get("/api/students", response_model=List[StudentOut])
async def list_students(current_user: Dict[str, str] = Depends(get_current_user)):
    """
    List students:
    - Admin: sees ALL students with owner_username
    - Normal user: sees ONLY their own students
    """
    try:
        coll = db["students"]
        users_coll = db["users"]
        user_id = current_user["user_id"]
        role = current_user["role"]
        
        # Build query based on role
        if role == "admin":
            # Admin sees all students
            query = {}
        else:
            # Normal user sees only their own students
            query = {"owner_id": user_id}
        
        docs = await coll.find(query).to_list(length=None)
        
        # For admin, fetch owner usernames
        if role == "admin":
            result = []
            for doc in docs:
                owner_username = None
                if doc.get("owner_id"):
                    owner_doc = await users_coll.find_one({"_id": ObjectId(doc["owner_id"])})
                    if owner_doc:
                        owner_username = owner_doc.get("username")
                result.append(doc_to_out(doc, owner_username))
            return result
        else:
            # Normal users don't need owner_username
            return [doc_to_out(d) for d in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# ---------- GET one student ----------
@app.get("/api/students/{id}", response_model=StudentOut)
async def get_student(id: str, current_user: Dict[str, str] = Depends(get_current_user)):
    """Get a single student - users can only access their own, admins can access any"""
    coll = db["students"]
    users_coll = db["users"]
    doc = await coll.find_one({"_id": oid(id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Check access: admin can access any, normal user only their own
    role = current_user["role"]
    user_id = current_user["user_id"]
    if role != "admin" and doc.get("owner_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied: You can only view your own students")
    
    # Fetch owner username if admin
    owner_username = None
    if role == "admin":
        owner_id = doc.get("owner_id")
        if owner_id:
            try:
                if isinstance(owner_id, str):
                    owner_doc = await users_coll.find_one({"_id": ObjectId(owner_id)})
                else:
                    owner_doc = await users_coll.find_one({"_id": owner_id})
                if owner_doc:
                    owner_username = owner_doc.get("username")
            except Exception:
                pass  # Skip if owner_id is invalid
    
    return doc_to_out(doc, owner_username)

# ---------- Create student ----------
@app.post("/api/students", response_model=StudentOut, status_code=status.HTTP_201_CREATED)
async def create_student(s: StudentIn, current_user: Dict[str, str] = Depends(get_current_user)):
    """Create a new student - automatically linked to current user"""
    try:
        coll = db["students"]
        user_id = current_user["user_id"]
        # Automatically set owner_id to current user
        data = {
            "name": s.name.strip(),
            "age": s.age,
            "courses": [c.strip() for c in (s.courses or []) if c.strip()],
            "owner_id": user_id  # Link student to user who created it
        }
        res = await coll.insert_one(data)
        doc = await coll.find_one({"_id": res.inserted_id})
        if not doc:
            raise HTTPException(status_code=500, detail="Failed to retrieve created student")
        return doc_to_out(doc)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# ---------- Delete student ----------
@app.delete("/api/students/{id}", status_code=status.HTTP_200_OK)
async def delete_student(id: str, current_user: Dict[str, str] = Depends(get_current_user)):
    """Delete a student - users can only delete their own, admins can delete any"""
    coll = db["students"]
    user_id = current_user["user_id"]
    role = current_user["role"]
    
    # Check if student exists and user has permission
    doc = await coll.find_one({"_id": oid(id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Check access: admin can delete any, normal user only their own
    if role != "admin" and doc.get("owner_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied: You can only delete your own students")
    
    result = await coll.delete_one({"_id": oid(id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Student not found")
    return {"message": f"Student {id} deleted"}

# Update a student
@app.put("/api/students/{id}", response_model=StudentOut)
async def update_student(id: str, s: StudentIn, current_user: Dict[str, str] = Depends(get_current_user)):
    """Update a student - users can only update their own, admins can update any"""
    try:
        coll = db["students"]
        users_coll = db["users"]
        user_id = current_user["user_id"]
        role = current_user["role"]
        
        # Check if student exists and user has permission
        doc = await coll.find_one({"_id": oid(id)})
        if not doc:
            raise HTTPException(status_code=404, detail="Student not found")
        
        # Check access: admin can update any, normal user only their own
        if role != "admin" and doc.get("owner_id") != user_id:
            raise HTTPException(status_code=403, detail="Access denied: You can only update your own students")
        
        # Build update payload (don't update owner_id)
        update_data = {
            "name": s.name.strip(),
            "age": s.age,
            "courses": [c.strip() for c in (s.courses or []) if c.strip()]
        }
        result = await coll.update_one({"_id": oid(id)}, {"$set": update_data})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Student not found")
        
        # Fetch and return the updated doc
        doc = await coll.find_one({"_id": oid(id)})
        if not doc:
            raise HTTPException(status_code=500, detail="Failed to retrieve updated student")
        
        # Fetch owner username if admin
        owner_username = None
        if role == "admin":
            owner_id = doc.get("owner_id")
            if owner_id:
                try:
                    if isinstance(owner_id, str):
                        owner_doc = await users_coll.find_one({"_id": ObjectId(owner_id)})
                    else:
                        owner_doc = await users_coll.find_one({"_id": owner_id})
                    if owner_doc:
                        owner_username = owner_doc.get("username")
                except Exception:
                    pass  # Skip if owner_id is invalid
        
        return doc_to_out(doc, owner_username)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")