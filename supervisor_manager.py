#!/usr/bin/env python3
"""
Supervisor Management Script with CRUD functionality.
Supports Create, Read, Update, Delete operations for supervisors.
Uses actual database configuration from the main application.
"""

import asyncio
import os
import random
import sys
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from typing import Dict, List, Optional

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


class SupervisorManager:
    """Class to handle CRUD operations for supervisors using real database."""
    
    def __init__(self):
        self.client = None
        self.db = None
        self.supervisors_collection = None
        self.lecturers_collection = None
    
    async def connect(self):
        """Connect to MongoDB using environment configuration."""
        self.client = AsyncIOMotorClient(MONGO_URL)
        self.db = self.client[DB_NAME]
        self.supervisors_collection = self.db.supervisors
        self.lecturers_collection = self.db.lecturers
        print("🔗 Connected to MongoDB")
        
        # Verify connection by checking collections
        collections = await self.db.list_collection_names()
        print(f"📂 Available collections: {len(collections)}")
    
    async def disconnect(self):
        """Disconnect from MongoDB."""
        if self.client:
            self.client.close()
            print("🔌 Database connection closed")
    
    async def get_available_lecturers(self) -> List[Dict]:
        """Get lecturers who are not already supervisors and not deleted."""
        try:
            # Get all supervisor lecturer IDs
            supervisor_lecturers = await self.supervisors_collection.distinct("lecturer_id")
            
            # Find lecturers not in supervisor list and not deleted
            available_lecturers = await self.lecturers_collection.find({
                "_id": {"$nin": supervisor_lecturers},
                "$or": [{"deleted": {"$exists": False}}, {"deleted": False}]
            }).to_list(length=100)
            
            return available_lecturers
        except Exception as e:
            print(f"❌ Error getting available lecturers: {e}")
            return []
    
    async def create_supervisor(self, supervisor_data: Dict) -> str:
        """Create a new supervisor."""
        try:
            # Check if lecturer exists and is not deleted
            lecturer = await self.lecturers_collection.find_one({
                "_id": supervisor_data["lecturer_id"],
                "$or": [{"deleted": {"$exists": False}}, {"deleted": False}]
            })
            
            if not lecturer:
                print("❌ Lecturer not found or is deleted")
                return None
            
            # Check if supervisor already exists for this lecturer
            existing = await self.supervisors_collection.find_one({
                "lecturer_id": supervisor_data["lecturer_id"]
            })
            
            if existing:
                lecturer_name = f"{lecturer.get('title', '')} {lecturer.get('surname', '')} {lecturer.get('otherNames', '')}".strip()
                print(f"⚠️ Supervisor already exists for lecturer: {lecturer_name}")
                return None
            
            # Add timestamps
            supervisor_data["createdAt"] = datetime.now(timezone.utc)
            supervisor_data["updatedAt"] = datetime.now(timezone.utc)
            
            result = await self.supervisors_collection.insert_one(supervisor_data)
            print(f"✅ Created supervisor with ID: {result.inserted_id}")
            return str(result.inserted_id)
        except Exception as e:
            print(f"❌ Error creating supervisor: {e}")
            return None
    
    async def read_supervisors(self, limit: int = 10, skip: int = 0) -> List[Dict]:
        """Read supervisors with pagination and lecturer details."""
        try:
            pipeline = [
                {"$skip": skip},
                {"$limit": limit},
                {
                    "$lookup": {
                        "from": "lecturers",
                        "localField": "lecturer_id",
                        "foreignField": "_id",
                        "as": "lecturer"
                    }
                },
                {"$unwind": "$lecturer"},
                {
                    "$project": {
                        "_id": 1,
                        "lecturer_id": 1,
                        "max_students": 1,
                        "project_student_count": 1,
                        "createdAt": 1,
                        "updatedAt": 1,
                        "lecturer_name": {
                            "$concat": [
                                {"$ifNull": ["$lecturer.title", ""]},
                                " ",
                                {"$ifNull": ["$lecturer.surname", ""]},
                                " ",
                                {"$ifNull": ["$lecturer.otherNames", ""]}
                            ]
                        },
                        "lecturer_email": "$lecturer.email",
                        "lecturer_phone": "$lecturer.phone",
                        "lecturer_academic_id": "$lecturer.academicId"
                    }
                }
            ]
            
            cursor = self.supervisors_collection.aggregate(pipeline)
            supervisors = await cursor.to_list(length=limit)
            return supervisors
        except Exception as e:
            print(f"❌ Error reading supervisors: {e}")
            return []
    
    async def read_supervisor_by_id(self, supervisor_id: str) -> Optional[Dict]:
        """Read a specific supervisor by ID with lecturer details."""
        try:
            pipeline = [
                {"$match": {"_id": ObjectId(supervisor_id)}},
                {
                    "$lookup": {
                        "from": "lecturers",
                        "localField": "lecturer_id",
                        "foreignField": "_id",
                        "as": "lecturer"
                    }
                },
                {"$unwind": "$lecturer"},
                {
                    "$project": {
                        "_id": 1,
                        "lecturer_id": 1,
                        "max_students": 1,
                        "project_student_count": 1,
                        "createdAt": 1,
                        "updatedAt": 1,
                        "lecturer_name": {
                            "$concat": [
                                {"$ifNull": ["$lecturer.title", ""]},
                                " ",
                                {"$ifNull": ["$lecturer.surname", ""]},
                                " ",
                                {"$ifNull": ["$lecturer.otherNames", ""]}
                            ]
                        },
                        "lecturer_email": "$lecturer.email",
                        "lecturer_phone": "$lecturer.phone",
                        "lecturer_academic_id": "$lecturer.academicId"
                    }
                }
            ]
            
            cursor = self.supervisors_collection.aggregate(pipeline)
            result = await cursor.to_list(length=1)
            return result[0] if result else None
        except Exception as e:
            print(f"❌ Error reading supervisor: {e}")
            return None
    
    async def update_supervisor(self, supervisor_id: str, update_data: Dict) -> bool:
        """Update a supervisor by ID."""
        try:
            # Add update timestamp
            update_data["updatedAt"] = datetime.now(timezone.utc)
            
            # If lecturer_id is being updated, validate it
            if "lecturer_id" in update_data:
                lecturer = await self.lecturers_collection.find_one({
                    "_id": update_data["lecturer_id"],
                    "$or": [{"deleted": {"$exists": False}}, {"deleted": False}]
                })
                
                if not lecturer:
                    print("❌ Lecturer not found or is deleted")
                    return False
                
                # Check if another supervisor already exists for this lecturer
                existing = await self.supervisors_collection.find_one({
                    "lecturer_id": update_data["lecturer_id"],
                    "_id": {"$ne": ObjectId(supervisor_id)}
                })
                
                if existing:
                    print("⚠️ Another supervisor already exists for this lecturer")
                    return False
            
            result = await self.supervisors_collection.update_one(
                {"_id": ObjectId(supervisor_id)},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                print(f"✅ Updated supervisor with ID: {supervisor_id}")
                return True
            else:
                print(f"⚠️ No supervisor found with ID: {supervisor_id}")
                return False
        except Exception as e:
            print(f"❌ Error updating supervisor: {e}")
            return False
    
    async def delete_supervisor(self, supervisor_id: str) -> bool:
        """Delete a supervisor by ID."""
        try:
            result = await self.supervisors_collection.delete_one({"_id": ObjectId(supervisor_id)})
            
            if result.deleted_count > 0:
                print(f"✅ Deleted supervisor with ID: {supervisor_id}")
                return True
            else:
                print(f"⚠️ No supervisor found with ID: {supervisor_id}")
                return False
        except Exception as e:
            print(f"❌ Error deleting supervisor: {e}")
            return False
    
    async def search_supervisors(self, query: str) -> List[Dict]:
        """Search supervisors by lecturer name or email."""
        try:
            pipeline = [
                {
                    "$lookup": {
                        "from": "lecturers",
                        "localField": "lecturer_id",
                        "foreignField": "_id",
                        "as": "lecturer"
                    }
                },
                {"$unwind": "$lecturer"},
                {
                    "$match": {
                        "$or": [
                            {"lecturer.surname": {"$regex": query, "$options": "i"}},
                            {"lecturer.otherNames": {"$regex": query, "$options": "i"}},
                            {"lecturer.email": {"$regex": query, "$options": "i"}},
                            {"lecturer.academicId": {"$regex": query, "$options": "i"}}
                        ]
                    }
                },
                {
                    "$project": {
                        "_id": 1,
                        "lecturer_id": 1,
                        "max_students": 1,
                        "project_student_count": 1,
                        "createdAt": 1,
                        "updatedAt": 1,
                        "lecturer_name": {
                            "$concat": [
                                {"$ifNull": ["$lecturer.title", ""]},
                                " ",
                                {"$ifNull": ["$lecturer.surname", ""]},
                                " ",
                                {"$ifNull": ["$lecturer.otherNames", ""]}
                            ]
                        },
                        "lecturer_email": "$lecturer.email",
                        "lecturer_phone": "$lecturer.phone",
                        "lecturer_academic_id": "$lecturer.academicId"
                    }
                },
                {"$limit": 50}
            ]
            
            cursor = self.supervisors_collection.aggregate(pipeline)
            supervisors = await cursor.to_list(length=50)
            return supervisors
        except Exception as e:
            print(f"❌ Error searching supervisors: {e}")
            return []
    
    async def get_supervisor_count(self) -> int:
        """Get total number of supervisors."""
        try:
            count = await self.supervisors_collection.count_documents({})
            return count
        except Exception as e:
            print(f"❌ Error counting supervisors: {e}")
            return 0
    
    async def clear_all_supervisors(self) -> int:
        """Clear all supervisors from the database."""
        try:
            result = await self.supervisors_collection.delete_many({})
            print(f"✅ Deleted {result.deleted_count} supervisor records")
            return result.deleted_count
        except Exception as e:
            print(f"❌ Error clearing supervisors: {e}")
            return 0


async def clear_and_populate_supervisors(manager: SupervisorManager, count: int = 10):
    """Clear existing supervisors and populate with random supervisors using real database data."""
    try:
        # Count existing supervisors
        existing_count = await manager.get_supervisor_count()
        print(f"📊 Found {existing_count} existing supervisors")
        
        # Clear existing supervisors
        if existing_count > 0:
            print("🗑️  Clearing existing supervisor data...")
            deleted_count = await manager.clear_all_supervisors()
        
        # Get available lecturers from database
        print("👨‍🎓 Loading available lecturers from database...")
        available_lecturers = await manager.get_available_lecturers()
        
        if len(available_lecturers) < count:
            print(f"⚠️ Only {len(available_lecturers)} lecturers available. Creating {len(available_lecturers)} supervisors.")
            count = len(available_lecturers)
        
        if count == 0:
            print("❌ No available lecturers to create supervisors.")
            return
        
        # Generate supervisors for available lecturers
        print(f"👥 Generating {count} supervisors using real lecturer data...")
        created_count = 0
        
        # Shuffle to get random selection
        random.shuffle(available_lecturers)
        
        for i in range(count):
            lecturer = available_lecturers[i]
            supervisor_data = {
                "lecturer_id": lecturer["_id"],
                "max_students": random.randint(3, 15),
                "project_student_count": 0
            }
            
            lecturer_name = f"{lecturer.get('title', '')} {lecturer.get('surname', '')} {lecturer.get('otherNames', '')}".strip()
            print(f"   {i+1}. {lecturer_name} (Max: {supervisor_data['max_students']} students)")
            
            supervisor_id = await manager.create_supervisor(supervisor_data)
            if supervisor_id:
                created_count += 1
        
        # Verify the operation
        new_count = await manager.get_supervisor_count()
        print(f"📊 Database now contains {new_count} supervisors")
        print(f"🎉 Successfully created {created_count} supervisors using real database data!")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def display_supervisor(supervisor: Dict, show_id: bool = True):
    """Display a supervisor in a formatted way."""
    if show_id:
        print(f"ID: {supervisor['_id']}")
    print(f"Lecturer: {supervisor.get('lecturer_name', 'N/A')}")
    print(f"Email: {supervisor.get('lecturer_email', 'N/A')}")
    print(f"Phone: {supervisor.get('lecturer_phone', 'N/A')}")
    print(f"Academic ID: {supervisor.get('lecturer_academic_id', 'N/A')}")
    print(f"Max Students: {supervisor.get('max_students', 'N/A')}")
    print(f"Current Students: {supervisor.get('project_student_count', 0)}")
    print(f"Created: {supervisor.get('createdAt', 'N/A')}")
    print("-" * 50)


async def interactive_menu():
    """Interactive menu for CRUD operations."""
    manager = SupervisorManager()
    await manager.connect()
    
    try:
        while True:
            print("\n" + "="*60)
            print("👨‍🏫 SUPERVISOR MANAGEMENT SYSTEM")
            print("="*60)
            print("1. 📋 List all supervisors")
            print("2. 🔍 Search supervisors")
            print("3. 👤 View supervisor by ID")
            print("4. 📊 Show supervisor count")
            print("5. 🗑️ Clear all supervisors")
            print("6. 🔄 Populate with random supervisors")
            print("7. 👨‍🎓 Show available lecturers")
            print("8. 🚪 Exit")
            print("="*60)
            
            choice = input("Enter your choice (1-8): ").strip()
            
            if choice == "1":
                # List all supervisors
                print("\n📋 Listing all supervisors...")
                supervisors = await manager.read_supervisors(limit=50)
                if supervisors:
                    for i, supervisor in enumerate(supervisors, 1):
                        print(f"\n{i}.")
                        display_supervisor(supervisor)
                else:
                    print("No supervisors found.")
            
            elif choice == "2":
                # Search supervisors
                query = input("\n🔍 Enter search term (lecturer name, email, or academic ID): ").strip()
                if query:
                    supervisors = await manager.search_supervisors(query)
                    if supervisors:
                        print(f"\n🔍 Found {len(supervisors)} supervisors:")
                        for i, supervisor in enumerate(supervisors, 1):
                            print(f"\n{i}.")
                            display_supervisor(supervisor)
                    else:
                        print("No supervisors found matching your search.")
                else:
                    print("Search term cannot be empty.")
            
            elif choice == "3":
                # View supervisor by ID
                supervisor_id = input("\n👤 Enter supervisor ID: ").strip()
                if supervisor_id:
                    supervisor = await manager.read_supervisor_by_id(supervisor_id)
                    if supervisor:
                        print("\n👤 Supervisor details:")
                        display_supervisor(supervisor)
                    else:
                        print("Supervisor not found.")
                else:
                    print("Supervisor ID cannot be empty.")
            
            elif choice == "4":
                # Show supervisor count
                count = await manager.get_supervisor_count()
                print(f"\n📊 Total supervisors in database: {count}")
            
            elif choice == "5":
                # Clear all supervisors
                count = await manager.get_supervisor_count()
                if count > 0:
                    confirm = input(f"\n⚠️ This will delete all {count} supervisors. Are you sure? (yes/no): ").strip().lower()
                    if confirm in ['yes', 'y']:
                        deleted = await manager.clear_all_supervisors()
                        print(f"✅ Cleared {deleted} supervisors from database.")
                    else:
                        print("Clear operation cancelled.")
                else:
                    print("Database is already empty.")
            
            elif choice == "6":
                # Populate with random supervisors
                try:
                    count = int(input("\n🔄 How many supervisors to create? (default 8): ").strip() or "8")
                    await clear_and_populate_supervisors(manager, count)
                except ValueError:
                    print("Invalid number. Using default of 8.")
                    await clear_and_populate_supervisors(manager, 8)
            
            elif choice == "7":
                # Show available lecturers
                print("\n👨‍🎓 Available lecturers (not yet supervisors):")
                available_lecturers = await manager.get_available_lecturers()
                if available_lecturers:
                    for i, lecturer in enumerate(available_lecturers, 1):
                        lecturer_name = f"{lecturer.get('title', '')} {lecturer.get('surname', '')} {lecturer.get('otherNames', '')}".strip()
                        print(f"{i}. {lecturer_name} ({lecturer.get('email', '')}) - ID: {lecturer.get('academicId', '')}")
                else:
                    print("No available lecturers found.")
            
            elif choice == "8":
                # Exit
                print("\n👋 Goodbye!")
                break
            
            else:
                print("\n❌ Invalid choice. Please select 1-8.")
                
            input("\nPress Enter to continue...")
    
    finally:
        await manager.disconnect()


async def main():
    """Main function to run the script."""
    if len(sys.argv) > 1 and sys.argv[1] == "--populate":
        # Command line mode for population
        print("🚀 Starting supervisor data clearing and population process...")
        print("=" * 60)
        
        manager = SupervisorManager()
        await manager.connect()
        try:
            count = int(sys.argv[2]) if len(sys.argv) > 2 else 8
            await clear_and_populate_supervisors(manager, count)
        finally:
            await manager.disconnect()
        
        print("=" * 60)
        print("✨ Process completed!")
    else:
        # Interactive mode
        await interactive_menu()


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
