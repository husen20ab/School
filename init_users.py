#!/usr/bin/env python3
"""
Initialize users collection in MongoDB.
Run this script once to create the users collection with default users.
"""

import os
import sys
import hashlib
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

def hash_password(password: str) -> str:
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

async def init_users():
    """Initialize users collection in MongoDB"""
    # Get MongoDB connection string from environment
    mongodb_uri = os.environ.get("MONGODB_URI")
    if not mongodb_uri:
        print("Error: MONGODB_URI environment variable is not set")
        sys.exit(1)
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(mongodb_uri)
    db = client["school"]
    users_coll = db["users"]
    
    try:
        # Test connection
        await client.admin.command('ping')
        print(f"Connected to MongoDB database: {db.name}")
        
        # Default users to create
        default_users = [
            {"username": "admin", "password": hash_password("admin"), "role": "admin"},
            {"username": "john", "password": hash_password("john"), "role": "user"},
        ]
        
        print("\nInitializing users collection...")
        created_count = 0
        skipped_count = 0
        
        for user in default_users:
            # Ensure username is lowercase for consistency
            username = user["username"].lower()
            existing = await users_coll.find_one({"username": username})
            
            if existing:
                print(f"  User '{username}' already exists, skipping...")
                skipped_count += 1
            else:
                user["username"] = username
                await users_coll.insert_one(user)
                print(f"  ✓ Created user: {username} (role: {user['role']})")
                created_count += 1
        
        print(f"\nSummary: {created_count} user(s) created, {skipped_count} user(s) already existed")
        print("Users collection initialized successfully!")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(init_users())

