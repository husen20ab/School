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

async def init_users():
    """Initialize default users in MongoDB if they don't exist"""
    users_coll = db["users"]
    
    default_users = [
        {"username": "admin", "password": hash_password("admin"), "role": "admin"},
        {"username": "john", "password": hash_password("john"), "role": "user"},
    ]
    
    for user in default_users:
        # Ensure username is lowercase for consistency
        username = user["username"].lower()
        existing = await users_coll.find_one({"username": username})
        if not existing:
            user["username"] = username
            await users_coll.insert_one(user)
            print(f"Created default user: {username}")

# --- Lifespan (connect once) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db = db
    try:
        # Test connection
        await client.admin.command('ping')
        print(f"Mongo connected to database: {db.name}")
        # Initialize default users
        await init_users()
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


def require_user(authorization: Optional[str] = Header(default=None)) -> Dict[str, str]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    token = authorization.split(" ", 1)[1].strip()
    session = SESSIONS.get(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return session


def require_admin(user: Dict[str, str] = Depends(require_user)) -> Dict[str, str]:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return user

# --- Helpers ---
def oid(id_str: str) -> ObjectId:
    if not ObjectId.is_valid(id_str):
        raise HTTPException(status_code=404, detail="Student not found")
    return ObjectId(id_str)

def doc_to_out(doc: dict) -> StudentOut:
    return StudentOut(
        id=str(doc["_id"]),
        name=doc.get("name", ""),
        age=doc.get("age", 0),
        courses=doc.get("courses", []),
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
    session = {"username": username, "role": user_doc["role"], "token": token}
    SESSIONS[token] = session
    return LoginResponse(token=token, username=username, role=user_doc["role"])


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
    session = {"username": username, "role": "user", "token": token}
    SESSIONS[token] = session
    
    return LoginResponse(token=token, username=username, role="user")


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

# ---------- List students ----------
@app.get("/api/students", response_model=List[StudentOut])
async def list_students(_: Dict[str, str] = Depends(require_user)):
    try:
        coll = db["students"]
        docs = await coll.find({}).to_list(length=None)
        return [doc_to_out(d) for d in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# ---------- GET one student ----------
@app.get("/api/students/{id}", response_model=StudentOut)
async def get_student(id: str, _: Dict[str, str] = Depends(require_user)):
    coll = db["students"]
    doc = await coll.find_one({"_id": oid(id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Student not found")
    return doc_to_out(doc)

# ---------- Create student ----------
@app.post("/api/students", response_model=StudentOut, status_code=status.HTTP_201_CREATED)
async def create_student(s: StudentIn, _: Dict[str, str] = Depends(require_user)):
    try:
        coll = db["students"]
        data = {"name": s.name.strip(), "age": s.age, "courses": [c.strip() for c in (s.courses or []) if c.strip()]}
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
async def delete_student(id: str, _: Dict[str, str] = Depends(require_user)):
    coll = db["students"]
    result = await coll.delete_one({"_id": oid(id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Student not found")
    return {"message": f"Student {id} deleted"}

# Update a student
@app.put("/api/students/{id}", response_model=StudentOut)
async def update_student(id: str, s: StudentIn, _: Dict[str, str] = Depends(require_user)):
    try:
        coll = db["students"]
        # Build update payload from the provided model, cleaning data
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
        return doc_to_out(doc)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")