#!/usr/bin/env python3
"""
Migration script to add owner_id to existing students.
Run this once to migrate existing student records to include owner_id.

If a student doesn't have an owner_id, it will be assigned to the first admin user found,
or if no admin exists, to the first user found.
"""

import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

async def migrate_students():
    """Add owner_id to existing students that don't have one"""
    # Get MongoDB connection string from environment
    mongodb_uri = os.environ.get("MONGODB_URI")
    if not mongodb_uri:
        print("Error: MONGODB_URI environment variable is not set")
        sys.exit(1)
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(mongodb_uri)
    db = client["school"]
    students_coll = db["students"]
    users_coll = db["users"]
    
    try:
        # Test connection
        await client.admin.command('ping')
        print(f"Connected to MongoDB database: {db.name}")
        
        # Find students without owner_id
        students_without_owner = await students_coll.find({"owner_id": {"$exists": False}}).to_list(length=None)
        
        if not students_without_owner:
            print("All students already have owner_id. No migration needed.")
            return
        
        print(f"\nFound {len(students_without_owner)} student(s) without owner_id")
        
        # Find a default owner (prefer admin, otherwise first user)
        admin_user = await users_coll.find_one({"role": "admin"})
        if admin_user:
            default_owner_id = str(admin_user["_id"])
            default_owner_username = admin_user["username"]
            print(f"Using admin user '{default_owner_username}' as default owner")
        else:
            first_user = await users_coll.find_one({})
            if not first_user:
                print("Error: No users found in database. Please create users first.")
                sys.exit(1)
            default_owner_id = str(first_user["_id"])
            default_owner_username = first_user["username"]
            print(f"Using user '{default_owner_username}' as default owner")
        
        # Update students
        updated_count = 0
        for student in students_without_owner:
            result = await students_coll.update_one(
                {"_id": student["_id"]},
                {"$set": {"owner_id": default_owner_id}}
            )
            if result.modified_count > 0:
                updated_count += 1
                print(f"  ✓ Added owner_id to student: {student.get('name', 'Unknown')} (ID: {student['_id']})")
        
        print(f"\nMigration complete: {updated_count} student(s) updated with owner_id")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(migrate_students())

