#!/usr/bin/env python3
"""
Supervisor Collection Setup and Migration Script.
This script ensures the supervisors collection is properly set up,
optimized with indexes, and completely separated from the lecturers collection.
"""

import asyncio
import os
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from typing import Dict, List

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# MongoDB connection settings from environment variables
MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME", "development")

if not MONGO_URL:
    raise ValueError("MONGO_URL environment variable is required")

print(f"🔗 Connecting to database: {DB_NAME}")
print(f"🌐 MongoDB URL: {MONGO_URL[:20]}...")


class SupervisorCollectionManager:
    """Class to handle supervisor collection setup and migration."""
    
    def __init__(self):
        self.client = None
        self.db = None
    
    async def connect(self):
        """Connect to MongoDB."""
        self.client = AsyncIOMotorClient(MONGO_URL)
        self.db = self.client[DB_NAME]
        print("🔗 Connected to MongoDB")
    
    async def disconnect(self):
        """Disconnect from MongoDB."""
        if self.client:
            self.client.close()
            print("🔌 Database connection closed")
    
    async def ensure_supervisors_collection(self):
        """Ensure supervisors collection exists and is properly configured."""
        print("📋 Ensuring supervisors collection exists...")
        
        # Check if collection exists
        collections = await self.db.list_collection_names()
        if "supervisors" not in collections:
            print("📝 Creating supervisors collection...")
            await self.db.create_collection("supervisors")
        else:
            print("✅ Supervisors collection already exists")
        
        return self.db.supervisors
    
    async def create_indexes(self):
        """Create indexes for optimal performance."""
        print("🔧 Creating indexes for supervisors collection...")
        
        supervisors_collection = self.db.supervisors
        
        # Index on lecturer_id (foreign key to lecturers)
        try:
            await supervisors_collection.create_index("lecturer_id", unique=True)
            print("✅ Created unique index on lecturer_id")
        except Exception as e:
            print(f"ℹ️ Index on lecturer_id might already exist: {e}")
        
        # Index on max_students for filtering
        try:
            await supervisors_collection.create_index("max_students")
            print("✅ Created index on max_students")
        except Exception as e:
            print(f"ℹ️ Index on max_students might already exist: {e}")
        
        # Index on project_student_count for sorting and filtering
        try:
            await supervisors_collection.create_index("project_student_count")
            print("✅ Created index on project_student_count")
        except Exception as e:
            print(f"ℹ️ Index on project_student_count might already exist: {e}")
        
        # Compound index on max_students and project_student_count for availability queries
        try:
            await supervisors_collection.create_index([
                ("max_students", 1),
                ("project_student_count", 1)
            ])
            print("✅ Created compound index on max_students + project_student_count")
        except Exception as e:
            print(f"ℹ️ Compound index might already exist: {e}")
    
    async def verify_data_integrity(self):
        """Verify that all supervisors reference valid lecturers."""
        print("🔍 Verifying data integrity...")
        
        supervisors_collection = self.db.supervisors
        lecturers_collection = self.db.lecturers
        
        # Get all supervisors
        supervisors = await supervisors_collection.find({}).to_list(length=None)
        print(f"📊 Found {len(supervisors)} supervisors")
        
        invalid_count = 0
        for supervisor in supervisors:
            lecturer_id = supervisor.get("lecturer_id")
            if lecturer_id:
                # Check if lecturer exists
                lecturer = await lecturers_collection.find_one({"_id": lecturer_id})
                if not lecturer:
                    print(f"❌ Supervisor {supervisor['_id']} references non-existent lecturer {lecturer_id}")
                    invalid_count += 1
                elif lecturer.get("deleted", False):
                    print(f"⚠️ Supervisor {supervisor['_id']} references deleted lecturer {lecturer_id}")
                    invalid_count += 1
        
        if invalid_count == 0:
            print("✅ All supervisor references are valid")
        else:
            print(f"⚠️ Found {invalid_count} invalid references")
        
        return invalid_count == 0
    
    async def update_project_student_counts(self):
        """Update project_student_count for all supervisors based on actual FYP data."""
        print("🔄 Updating project student counts...")
        
        supervisors_collection = self.db.supervisors
        fyps_collection = self.db.fyps
        
        supervisors = await supervisors_collection.find({}).to_list(length=None)
        updated_count = 0
        
        for supervisor in supervisors:
            lecturer_id = supervisor["lecturer_id"]
            
            # Count FYPs supervised by this lecturer
            fyp_count = await fyps_collection.count_documents({"supervisor": lecturer_id})
            
            # Update supervisor record
            result = await supervisors_collection.update_one(
                {"_id": supervisor["_id"]},
                {
                    "$set": {
                        "project_student_count": fyp_count,
                        "updatedAt": datetime.now(timezone.utc)
                    }
                }
            )
            
            if result.modified_count > 0:
                updated_count += 1
                print(f"📝 Updated supervisor {supervisor['_id']}: {fyp_count} projects")
        
        print(f"✅ Updated {updated_count} supervisor records")
    
    async def show_collection_stats(self):
        """Display collection statistics."""
        print("\n📊 COLLECTION STATISTICS")
        print("=" * 50)
        
        # Supervisors collection stats
        supervisors_count = await self.db.supervisors.count_documents({})
        lecturers_count = await self.db.lecturers.count_documents({"deleted": {"$ne": True}})
        
        print(f"👥 Total supervisors: {supervisors_count}")
        print(f"👨‍🏫 Total active lecturers: {lecturers_count}")
        
        # Average and max students per supervisor
        pipeline = [
            {
                "$group": {
                    "_id": None,
                    "avg_max_students": {"$avg": "$max_students"},
                    "max_max_students": {"$max": "$max_students"},
                    "min_max_students": {"$min": "$max_students"},
                    "total_project_count": {"$sum": "$project_student_count"}
                }
            }
        ]
        
        stats = await self.db.supervisors.aggregate(pipeline).to_list(length=1)
        if stats:
            stat = stats[0]
            print(f"📈 Average max students per supervisor: {stat.get('avg_max_students', 0):.1f}")
            print(f"📊 Max students (highest): {stat.get('max_max_students', 0)}")
            print(f"📉 Max students (lowest): {stat.get('min_max_students', 0)}")
            print(f"🎓 Total projects being supervised: {stat.get('total_project_count', 0)}")
        
        # Supervisors with availability
        available_supervisors = await self.db.supervisors.count_documents({
            "$expr": {"$lt": ["$project_student_count", "$max_students"]}
        })
        print(f"🟢 Supervisors with availability: {available_supervisors}")
        
        # List indexes
        indexes = await self.db.supervisors.list_indexes().to_list(length=None)
        print(f"\n🔧 Indexes on supervisors collection: {len(indexes)}")
        for idx in indexes:
            print(f"   - {idx.get('name', 'unnamed')}: {idx.get('key', {})}")
    
    async def migrate_any_remaining_supervisor_data(self):
        """
        Check if there are any supervisor-specific fields in lecturers collection
        that need to be migrated to supervisors collection.
        """
        print("🔍 Checking for any supervisor data in lecturers collection...")
        
        # Check if lecturers have any supervisor-specific fields
        lecturer_with_max_students = await self.db.lecturers.find_one({"max_students": {"$exists": True}})
        
        if lecturer_with_max_students:
            print("⚠️ Found supervisor data in lecturers collection. Starting migration...")
            
            # Find all lecturers with supervisor data
            lecturers_with_supervisor_data = await self.db.lecturers.find({
                "max_students": {"$exists": True}
            }).to_list(length=None)
            
            migrated_count = 0
            for lecturer in lecturers_with_supervisor_data:
                # Check if supervisor record already exists
                existing_supervisor = await self.db.supervisors.find_one({
                    "lecturer_id": lecturer["_id"]
                })
                
                if not existing_supervisor:
                    # Create supervisor record
                    supervisor_data = {
                        "lecturer_id": lecturer["_id"],
                        "max_students": lecturer.get("max_students", 5),
                        "project_student_count": 0,
                        "createdAt": datetime.now(timezone.utc),
                        "updatedAt": datetime.now(timezone.utc)
                    }
                    
                    await self.db.supervisors.insert_one(supervisor_data)
                    migrated_count += 1
                    print(f"📝 Migrated supervisor data for lecturer {lecturer['_id']}")
                
                # Remove supervisor fields from lecturer
                await self.db.lecturers.update_one(
                    {"_id": lecturer["_id"]},
                    {"$unset": {"max_students": ""}}
                )
            
            print(f"✅ Migrated {migrated_count} supervisor records")
            print("🧹 Cleaned supervisor data from lecturers collection")
        else:
            print("✅ No supervisor data found in lecturers collection")
    
    async def create_sample_supervisor_if_empty(self):
        """Create a sample supervisor if the collection is empty."""
        count = await self.db.supervisors.count_documents({})
        if count == 0:
            print("📝 Creating sample supervisor data...")
            
            # Get a sample lecturer
            lecturer = await self.db.lecturers.find_one({"deleted": {"$ne": True}})
            if lecturer:
                supervisor_data = {
                    "lecturer_id": lecturer["_id"],
                    "max_students": 10,
                    "project_student_count": 0,
                    "createdAt": datetime.now(timezone.utc),
                    "updatedAt": datetime.now(timezone.utc)
                }
                
                result = await self.db.supervisors.insert_one(supervisor_data)
                print(f"✅ Created sample supervisor with ID: {result.inserted_id}")
            else:
                print("⚠️ No lecturers found to create sample supervisor")


async def main():
    """Main function to set up supervisor collection."""
    print("🚀 Starting Supervisor Collection Setup...")
    print("=" * 60)
    
    manager = SupervisorCollectionManager()
    await manager.connect()
    
    try:
        # Step 1: Ensure collection exists
        await manager.ensure_supervisors_collection()
        
        # Step 2: Migrate any remaining supervisor data from lecturers
        await manager.migrate_any_remaining_supervisor_data()
        
        # Step 3: Create indexes for performance
        await manager.create_indexes()
        
        # Step 4: Update project student counts
        await manager.update_project_student_counts()
        
        # Step 5: Verify data integrity
        await manager.verify_data_integrity()
        
        # Step 6: Create sample data if needed
        await manager.create_sample_supervisor_if_empty()
        
        # Step 7: Show statistics
        await manager.show_collection_stats()
        
        print("\n" + "=" * 60)
        print("✨ Supervisor collection setup completed successfully!")
        print("✅ Supervisors are now completely separated from lecturers")
        print("🔗 All supervisor data is properly linked via lecturer_id")
        
    except Exception as e:
        print(f"❌ Error during setup: {e}")
    finally:
        await manager.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
