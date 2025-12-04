#!/usr/bin/env python3
"""
Script to set all existing users to admin role.
Run this to grant admin privileges to all users in the database.
"""

import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

async def make_all_users_admin():
    """Set all users to admin role"""
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
        
        # Find all users
        users = await users_coll.find({}).to_list(length=None)
        
        if not users:
            print("No users found in database.")
            return
        
        print(f"\nFound {len(users)} user(s)")
        
        # Update all users to admin role
        updated_count = 0
        for user in users:
            username = user.get("username", "Unknown")
            current_role = user.get("role", "user")
            
            if current_role != "admin":
                result = await users_coll.update_one(
                    {"_id": user["_id"]},
                    {"$set": {"role": "admin"}}
                )
                if result.modified_count > 0:
                    updated_count += 1
                    print(f"  ✓ Updated user '{username}' to admin role")
                else:
                    print(f"  - User '{username}' already has admin role or update failed")
            else:
                print(f"  - User '{username}' already has admin role")
        
        print(f"\nUpdate complete: {updated_count} user(s) updated to admin role")
        print(f"Total users with admin role: {len(users)}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(make_all_users_admin())

