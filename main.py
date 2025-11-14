import os
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

# --- Config ---
MONGO_URL = os.getenv("MONGO_URL", "mongodb+srv://husen20ab_db_user:hOWWOtRx1cEg8jBw@cluster0.neidmqo.mongodb.net/")
DB_NAME = os.getenv("MONGO_DB", "school")

# --- Lifespan (connect once) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.mongo_client = AsyncIOMotorClient(MONGO_URL)
    app.state.db = app.state.mongo_client[DB_NAME]
    print("Mongo connected")
    try:
        yield
    finally:
        app.state.mongo_client.close()
        print("Mongo connection closed")

app = FastAPI(title="School App", lifespan=lifespan)


def _cors_origins() -> List[str]:
    env_value = os.getenv("CORS_ORIGINS", "")
    if env_value:
        origins = [origin.strip() for origin in env_value.split(",") if origin.strip()]
        if origins:
            return origins
    return [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


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

@app.get("/health")
async def health():
    return {"status": "ok"}

# ---------- List students ----------
@app.get("/api/students", response_model=List[StudentOut])
async def list_students(request: Request):
    coll = request.app.state.db["students"]
    docs = await coll.find({}).to_list(length=None)
    return [doc_to_out(d) for d in docs]

# ---------- GET one student ----------
@app.get("/api/students/{id}", response_model=StudentOut)
async def get_student(request: Request, id: str):
    coll = request.app.state.db["students"]
    doc = await coll.find_one({"_id": oid(id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Student not found")
    return doc_to_out(doc)

# ---------- Create student ----------
@app.post("/api/students", response_model=StudentOut, status_code=status.HTTP_201_CREATED)
async def create_student(request: Request, s: StudentIn):
    coll = request.app.state.db["students"]
    data = {"name": s.name, "age": s.age, "courses": s.courses or []}
    res = await coll.insert_one(data)
    doc = await coll.find_one({"_id": res.inserted_id})
    return doc_to_out(doc)

# ---------- Delete student ----------
@app.delete("/api/students/{id}", status_code=status.HTTP_200_OK)
async def delete_student(request: Request, id: str):
    coll = request.app.state.db["students"]
    result = await coll.delete_one({"_id": oid(id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Student not found")
    return {"message": f"Student {id} deleted"}

# Update a student
@app.put("/api/students/{id}", response_model=StudentOut)
async def update_student(request: Request, id: str, s: StudentIn):
    coll = request.app.state.db["students"]
    # Build update payload from the provided model
    update_data = {k: v for k, v in s.model_dump().items() if v is not None}
    result = await coll.update_one({"_id": oid(id)}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # fetch and return the updated doc
    doc = await coll.find_one({"_id": oid(id)})
    return doc_to_out(doc)