import os
import secrets
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

USERS: Dict[str, Dict[str, str]] = {
    "admin": {"password": "admin", "role": "admin"},
    "john": {"password": "john", "role": "user"},
}
SESSIONS: Dict[str, Dict[str, str]] = {}

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


class LoginRequest(BaseModel):
    username: str
    password: str


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
    user_record = USERS.get(credentials.username)
    if not user_record or user_record["password"] != credentials.password:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = secrets.token_hex(32)
    session = {"username": credentials.username, "role": user_record["role"], "token": token}
    SESSIONS[token] = session
    return LoginResponse(token=token, username=credentials.username, role=user_record["role"])


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
    coll = db["students"]
    data = {"name": s.name, "age": s.age, "courses": s.courses or []}
    res = await coll.insert_one(data)
    doc = await coll.find_one({"_id": res.inserted_id})
    return doc_to_out(doc)

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
    coll = db["students"]
    # Build update payload from the provided model
    update_data = {k: v for k, v in s.model_dump().items() if v is not None}
    result = await coll.update_one({"_id": oid(id)}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # fetch and return the updated doc
    doc = await coll.find_one({"_id": oid(id)})
    return doc_to_out(doc)