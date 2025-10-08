#!/usr/bin/env python3
"""
MongoDB Collections Initialization Script
Creates all necessary collections based on the models in the system
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

# All collections that should exist based on your models
COLLECTIONS_TO_CREATE = [
    "activity_logs",
    "academic_years", 
    "channels",
    "chatusers",
    "class_groups",
    "committees",
    "communications",
    "complaints",
    "course_registrations",
    "courses",
    "deferments",
    "deliverables",
    "exam_timetables",
    "fypcheckins",
    "fyps",
    "groups",
    "lecturer_project_areas",
    "lecturers",
    "levels",
    "messages",
    "modules",
    "non_teachings",
    "noticeboards",
    "program_courses",
    "programs",
    "project_areas",
    "projects",
    "recent_activities",
    "reminders",
    "students",
    "submission_files",
    "submissions",
    "supervisors",
    "timetables",
    "userchannels",
    "vector_stores"
]

async def init_collections():
    """Initialize all MongoDB collections"""
    client = AsyncIOMotorClient(settings.MONGO_URL)
    db = client[settings.DB_NAME]
    
    print("🚀 Starting MongoDB Collections Initialization...")
    print(f"📊 Database: {settings.DB_NAME}")
    print(f"🔗 Connection: {settings.MONGO_URL}")
    
    # Get existing collections
    existing_collections = await db.list_collection_names()
    print(f"\n📋 Existing collections: {existing_collections}")
    
    created_count = 0
    skipped_count = 0
    
    for collection_name in COLLECTIONS_TO_CREATE:
        if collection_name in existing_collections:
            print(f"⏭️  Skipping '{collection_name}' - already exists")
            skipped_count += 1
        else:
            # Create collection by inserting and immediately deleting a document
            # This ensures the collection is created with proper indexes
            try:
                await db[collection_name].insert_one({"__init__": True})
                await db[collection_name].delete_one({"__init__": True})
                print(f"✅ Created collection: '{collection_name}'")
                created_count += 1
            except Exception as e:
                print(f"❌ Failed to create '{collection_name}': {e}")
    
    # Create indexes for important collections
    print(f"\n🔍 Creating indexes...")
    
    # Indexes for logins collection
    try:
        await db.logins.create_index("academicId", unique=True)
        print("✅ Created index on logins.academicId")
    except Exception as e:
        print(f"⚠️  Index creation warning: {e}")
    
    # Indexes for students collection
    try:
        await db.students.create_index("academicId", unique=True)
        await db.students.create_index("email", unique=True)
        print("✅ Created indexes on students collection")
    except Exception as e:
        print(f"⚠️  Index creation warning: {e}")
    
    # Indexes for lecturers collection
    try:
        await db.lecturers.create_index("staffId", unique=True)
        await db.lecturers.create_index("email", unique=True)
        print("✅ Created indexes on lecturers collection")
    except Exception as e:
        print(f"⚠️  Index creation warning: {e}")
    
    # Indexes for programs collection
    try:
        await db.programs.create_index("code", unique=True)
        print("✅ Created index on programs.code")
    except Exception as e:
        print(f"⚠️  Index creation warning: {e}")
    
    # Indexes for academic_years collection
    try:
        await db.academic_years.create_index("year", unique=True)
        print("✅ Created index on academic_years.year")
    except Exception as e:
        print(f"⚠️  Index creation warning: {e}")
    
    # Final summary
    print(f"\n🎉 Initialization Complete!")
    print(f"📊 Summary:")
    print(f"   • Collections created: {created_count}")
    print(f"   • Collections skipped: {skipped_count}")
    print(f"   • Total collections: {len(COLLECTIONS_TO_CREATE)}")
    
    # List all collections after initialization
    final_collections = await db.list_collection_names()
    print(f"\n📋 All collections in database:")
    for collection in sorted(final_collections):
        count = await db[collection].count_documents({})
        print(f"   • {collection}: {count} documents")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(init_collections())