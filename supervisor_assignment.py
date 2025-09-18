#!/usr/bin/env python3
"""
Supervisor Assignment System for Students.
Handles assigning supervisors to students and manages FYP (Final Year Project) records.
Updates supervisor project counts and validates assignment constraints.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from typing import Dict, List, Optional, Union

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


class SupervisorAssignmentManager:
    """Class to handle supervisor assignments for students."""
    
    def __init__(self):
        self.client = None
        self.db = None
        self.students_collection = None
        self.supervisors_collection = None
        self.lecturers_collection = None
        self.fyps_collection = None
        self.fypcheckins_collection = None
        self.academic_years_collection = None
    
    async def connect(self):
        """Connect to MongoDB."""
        self.client = AsyncIOMotorClient(MONGO_URL)
        self.db = self.client[DB_NAME]
        self.students_collection = self.db.students
        self.supervisors_collection = self.db.supervisors
        self.lecturers_collection = self.db.lecturers
        self.fyps_collection = self.db.fyps
        self.fypcheckins_collection = self.db.fypcheckins
        self.academic_years_collection = self.db.academic_years
        print("🔗 Connected to MongoDB")
    
    async def disconnect(self):
        """Disconnect from MongoDB."""
        if self.client:
            self.client.close()
            print("🔌 Database connection closed")
    
    async def get_available_supervisors(self) -> List[Dict]:
        """Get supervisors who have capacity for more students."""
        try:
            # Use aggregation to get supervisors with lecturer details and availability
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
                        "lecturer.deleted": {"$ne": True},
                        "$expr": {"$lt": ["$project_student_count", "$max_students"]}
                    }
                },
                {
                    "$project": {
                        "_id": 1,
                        "lecturer_id": 1,
                        "max_students": 1,
                        "project_student_count": 1,
                        "available_slots": {"$subtract": ["$max_students", "$project_student_count"]},
                        "lecturer_name": {
                            "$concat": [
                                "$lecturer.title", " ",
                                "$lecturer.surname", " ",
                                "$lecturer.otherNames"
                            ]
                        },
                        "lecturer_email": "$lecturer.email",
                        "lecturer_academic_id": "$lecturer.academicId"
                    }
                },
                {"$sort": {"available_slots": -1}}  # Sort by most available slots first
            ]
            
            supervisors = await self.supervisors_collection.aggregate(pipeline).to_list(length=None)
            return supervisors
        except Exception as e:
            print(f"❌ Error getting available supervisors: {e}")
            return []
    
    async def get_student_by_id(self, student_id: str) -> Optional[Dict]:
        """Get student details by ID."""
        try:
            student = await self.students_collection.find_one({"_id": ObjectId(student_id)})
            return student
        except Exception as e:
            print(f"❌ Error getting student: {e}")
            return None
    
    async def get_supervisor_by_id(self, supervisor_id: str) -> Optional[Dict]:
        """Get supervisor details by ID."""
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
                        "lecturer_name": {
                            "$concat": [
                                "$lecturer.title", " ",
                                "$lecturer.surname", " ",
                                "$lecturer.otherNames"
                            ]
                        },
                        "lecturer_email": "$lecturer.email"
                    }
                }
            ]
            
            result = await self.supervisors_collection.aggregate(pipeline).to_list(length=1)
            return result[0] if result else None
        except Exception as e:
            print(f"❌ Error getting supervisor: {e}")
            return None
    
    async def get_current_fyp_checkin(self) -> Optional[Dict]:
        """Get the current active FYP checkin period."""
        try:
            # Find the most recent checkin or create a default one
            checkin = await self.fypcheckins_collection.find_one(
                {},
                sort=[("createdAt", -1)]
            )
            
            if not checkin:
                # Create a default checkin if none exists
                current_academic_year = await self.academic_years_collection.find_one(
                    {"deleted": {"$ne": True}},
                    sort=[("createdAt", -1)]
                )
                
                if current_academic_year:
                    checkin_data = {
                        "academicYear": current_academic_year["_id"],
                        "term": 1,
                        "status": "active",
                        "createdAt": datetime.now(timezone.utc),
                        "updatedAt": datetime.now(timezone.utc)
                    }
                    
                    result = await self.fypcheckins_collection.insert_one(checkin_data)
                    checkin = await self.fypcheckins_collection.find_one({"_id": result.inserted_id})
                    print(f"📝 Created new FYP checkin: {result.inserted_id}")
            
            return checkin
        except Exception as e:
            print(f"❌ Error getting FYP checkin: {e}")
            return None
    
    async def check_existing_assignment(self, student_id: str, checkin_id: str) -> Optional[Dict]:
        """Check if student already has a supervisor assignment."""
        try:
            existing_fyp = await self.fyps_collection.find_one({
                "student": ObjectId(student_id),
                "checkin": ObjectId(checkin_id)
            })
            return existing_fyp
        except Exception as e:
            print(f"❌ Error checking existing assignment: {e}")
            return None
    
    async def assign_supervisor_to_student(
        self, 
        student_id: str, 
        supervisor_id: str, 
        project_area_id: Optional[str] = None
    ) -> Dict:
        """Assign a supervisor to a student."""
        try:
            # Validate student exists
            student = await self.get_student_by_id(student_id)
            if not student:
                return {"success": False, "error": "Student not found"}
            
            # Validate supervisor exists and has capacity
            supervisor = await self.get_supervisor_by_id(supervisor_id)
            if not supervisor:
                return {"success": False, "error": "Supervisor not found"}
            
            if supervisor["project_student_count"] >= supervisor["max_students"]:
                return {
                    "success": False, 
                    "error": f"Supervisor has reached maximum capacity ({supervisor['max_students']} students)"
                }
            
            # Get current FYP checkin
            checkin = await self.get_current_fyp_checkin()
            if not checkin:
                return {"success": False, "error": "No active FYP checkin period found"}
            
            # Check if student already has assignment for this checkin
            existing_assignment = await self.check_existing_assignment(student_id, str(checkin["_id"]))
            
            if existing_assignment:
                # Update existing assignment
                update_data = {
                    "supervisor": supervisor["lecturer_id"],
                    "updatedAt": datetime.now(timezone.utc)
                }
                
                if project_area_id:
                    update_data["projectArea"] = ObjectId(project_area_id)
                
                await self.fyps_collection.update_one(
                    {"_id": existing_assignment["_id"]},
                    {"$set": update_data}
                )
                
                action = "updated"
                fyp_id = existing_assignment["_id"]
            else:
                # Create new assignment
                fyp_data = {
                    "student": ObjectId(student_id),
                    "supervisor": supervisor["lecturer_id"],
                    "checkin": checkin["_id"],
                    "projectArea": ObjectId(project_area_id) if project_area_id else None,
                    "createdAt": datetime.now(timezone.utc),
                    "updatedAt": datetime.now(timezone.utc)
                }
                
                result = await self.fyps_collection.insert_one(fyp_data)
                action = "created"
                fyp_id = result.inserted_id
            
            # Update supervisor project count
            await self.update_supervisor_project_count(supervisor_id)
            
            return {
                "success": True,
                "action": action,
                "fyp_id": str(fyp_id),
                "message": f"Successfully {action} supervisor assignment",
                "assignment": {
                    "student_name": f"{student.get('title', '')} {student.get('surname', '')} {student.get('otherNames', '')}".strip(),
                    "student_email": student.get("email"),
                    "supervisor_name": supervisor["lecturer_name"],
                    "supervisor_email": supervisor["lecturer_email"]
                }
            }
            
        except Exception as e:
            print(f"❌ Error assigning supervisor: {e}")
            return {"success": False, "error": str(e)}
    
    async def update_supervisor_project_count(self, supervisor_id: str):
        """Update the project count for a supervisor based on actual FYP records."""
        try:
            # Get supervisor details
            supervisor = await self.supervisors_collection.find_one({"_id": ObjectId(supervisor_id)})
            if not supervisor:
                return
            
            # Count FYPs supervised by this lecturer
            count = await self.fyps_collection.count_documents({
                "supervisor": supervisor["lecturer_id"]
            })
            
            # Update supervisor record
            await self.supervisors_collection.update_one(
                {"_id": ObjectId(supervisor_id)},
                {
                    "$set": {
                        "project_student_count": count,
                        "updatedAt": datetime.now(timezone.utc)
                    }
                }
            )
            
            print(f"📊 Updated supervisor {supervisor_id} project count to {count}")
            
        except Exception as e:
            print(f"❌ Error updating supervisor project count: {e}")
    
    async def remove_supervisor_assignment(self, student_id: str) -> Dict:
        """Remove supervisor assignment for a student."""
        try:
            # Get current checkin
            checkin = await self.get_current_fyp_checkin()
            if not checkin:
                return {"success": False, "error": "No active FYP checkin period found"}
            
            # Find and remove the assignment
            existing_assignment = await self.check_existing_assignment(student_id, str(checkin["_id"]))
            if not existing_assignment:
                return {"success": False, "error": "No supervisor assignment found for this student"}
            
            # Get supervisor ID before deletion
            supervisor_lecturer_id = existing_assignment.get("supervisor")
            
            # Delete the FYP record
            result = await self.fyps_collection.delete_one({"_id": existing_assignment["_id"]})
            
            if result.deleted_count > 0:
                # Update supervisor project count if supervisor was assigned
                if supervisor_lecturer_id:
                    supervisor = await self.supervisors_collection.find_one({
                        "lecturer_id": supervisor_lecturer_id
                    })
                    if supervisor:
                        await self.update_supervisor_project_count(str(supervisor["_id"]))
                
                return {
                    "success": True,
                    "message": "Successfully removed supervisor assignment"
                }
            else:
                return {"success": False, "error": "Failed to remove assignment"}
                
        except Exception as e:
            print(f"❌ Error removing supervisor assignment: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_student_assignments(self, limit: int = 20) -> List[Dict]:
        """Get current student-supervisor assignments."""
        try:
            # Get current checkin
            checkin = await self.get_current_fyp_checkin()
            if not checkin:
                return []
            
            pipeline = [
                {"$match": {"checkin": checkin["_id"]}},
                {
                    "$lookup": {
                        "from": "students",
                        "localField": "student",
                        "foreignField": "_id",
                        "as": "student_info"
                    }
                },
                {"$unwind": "$student_info"},
                {
                    "$lookup": {
                        "from": "lecturers",
                        "localField": "supervisor",
                        "foreignField": "_id",
                        "as": "supervisor_info"
                    }
                },
                {"$unwind": "$supervisor_info"},
                {
                    "$project": {
                        "_id": 1,
                        "student_id": "$student",
                        "student_name": {
                            "$concat": [
                                "$student_info.title", " ",
                                "$student_info.surname", " ",
                                "$student_info.otherNames"
                            ]
                        },
                        "student_email": "$student_info.email",
                        "student_academic_id": "$student_info.academicId",
                        "supervisor_id": "$supervisor",
                        "supervisor_name": {
                            "$concat": [
                                "$supervisor_info.title", " ",
                                "$supervisor_info.surname", " ",
                                "$supervisor_info.otherNames"
                            ]
                        },
                        "supervisor_email": "$supervisor_info.email",
                        "supervisor_academic_id": "$supervisor_info.academicId",
                        "project_area": "$projectArea",
                        "assigned_at": "$createdAt",
                        "updated_at": "$updatedAt"
                    }
                },
                {"$limit": limit}
            ]
            
            assignments = await self.fyps_collection.aggregate(pipeline).to_list(length=limit)
            return assignments
            
        except Exception as e:
            print(f"❌ Error getting student assignments: {e}")
            return []
    
    async def get_unassigned_students(self, limit: int = 20) -> List[Dict]:
        """Get students who don't have supervisor assignments."""
        try:
            # Get current checkin
            checkin = await self.get_current_fyp_checkin()
            if not checkin:
                return []
            
            # Get students who don't have FYP records for current checkin
            pipeline = [
                {
                    "$lookup": {
                        "from": "fyps",
                        "let": {"student_id": "$_id"},
                        "pipeline": [
                            {
                                "$match": {
                                    "$expr": {
                                        "$and": [
                                            {"$eq": ["$student", "$$student_id"]},
                                            {"$eq": ["$checkin", checkin["_id"]]}
                                        ]
                                    }
                                }
                            }
                        ],
                        "as": "fyp_assignment"
                    }
                },
                {
                    "$match": {
                        "deleted": {"$ne": True},
                        "fyp_assignment": {"$eq": []}
                    }
                },
                {
                    "$project": {
                        "_id": 1,
                        "student_name": {
                            "$concat": [
                                "$title", " ",
                                "$surname", " ",
                                "$otherNames"
                            ]
                        },
                        "email": 1,
                        "academicId": 1,
                        "program": 1,
                        "level": 1
                    }
                },
                {"$limit": limit}
            ]
            
            unassigned = await self.students_collection.aggregate(pipeline).to_list(length=limit)
            return unassigned
            
        except Exception as e:
            print(f"❌ Error getting unassigned students: {e}")
            return []


async def interactive_supervisor_assignment():
    """Interactive menu for supervisor assignment operations."""
    manager = SupervisorAssignmentManager()
    await manager.connect()
    
    try:
        while True:
            print("\n" + "="*70)
            print("👨‍🏫 SUPERVISOR ASSIGNMENT SYSTEM")
            print("="*70)
            print("1. 📋 View available supervisors")
            print("2. 👥 View current assignments")
            print("3. 🎓 View unassigned students")
            print("4. ➕ Assign supervisor to student")
            print("5. ➖ Remove supervisor assignment")
            print("6. 🔄 Update supervisor project counts")
            print("7. 🚪 Exit")
            print("="*70)
            
            choice = input("Enter your choice (1-7): ").strip()
            
            if choice == "1":
                # View available supervisors
                print("\n📋 Available Supervisors:")
                supervisors = await manager.get_available_supervisors()
                if supervisors:
                    for i, supervisor in enumerate(supervisors, 1):
                        print(f"\n{i}. {supervisor['lecturer_name']}")
                        print(f"   📧 Email: {supervisor['lecturer_email']}")
                        print(f"   🆔 ID: {supervisor['_id']}")
                        print(f"   👥 Capacity: {supervisor['project_student_count']}/{supervisor['max_students']}")
                        print(f"   🟢 Available slots: {supervisor['available_slots']}")
                else:
                    print("No available supervisors found.")
            
            elif choice == "2":
                # View current assignments
                print("\n👥 Current Assignments:")
                assignments = await manager.get_student_assignments()
                if assignments:
                    for i, assignment in enumerate(assignments, 1):
                        print(f"\n{i}. {assignment['student_name']} → {assignment['supervisor_name']}")
                        print(f"   📧 Student: {assignment['student_email']}")
                        print(f"   👨‍🏫 Supervisor: {assignment['supervisor_email']}")
                        print(f"   📅 Assigned: {assignment['assigned_at']}")
                else:
                    print("No assignments found.")
            
            elif choice == "3":
                # View unassigned students
                print("\n🎓 Unassigned Students:")
                unassigned = await manager.get_unassigned_students()
                if unassigned:
                    for i, student in enumerate(unassigned, 1):
                        print(f"\n{i}. {student['student_name']}")
                        print(f"   📧 Email: {student['email']}")
                        print(f"   🆔 ID: {student['_id']}")
                        print(f"   🎓 Academic ID: {student['academicId']}")
                else:
                    print("No unassigned students found.")
            
            elif choice == "4":
                # Assign supervisor to student
                student_id = input("\n👤 Enter student ID: ").strip()
                supervisor_id = input("👨‍🏫 Enter supervisor ID: ").strip()
                
                if student_id and supervisor_id:
                    print("\n🔄 Processing assignment...")
                    result = await manager.assign_supervisor_to_student(student_id, supervisor_id)
                    
                    if result["success"]:
                        print(f"✅ {result['message']}")
                        print(f"📝 Student: {result['assignment']['student_name']}")
                        print(f"👨‍🏫 Supervisor: {result['assignment']['supervisor_name']}")
                    else:
                        print(f"❌ Assignment failed: {result['error']}")
                else:
                    print("❌ Please provide both student ID and supervisor ID.")
            
            elif choice == "5":
                # Remove supervisor assignment
                student_id = input("\n👤 Enter student ID to remove assignment: ").strip()
                
                if student_id:
                    print("\n🔄 Removing assignment...")
                    result = await manager.remove_supervisor_assignment(student_id)
                    
                    if result["success"]:
                        print(f"✅ {result['message']}")
                    else:
                        print(f"❌ Removal failed: {result['error']}")
                else:
                    print("❌ Please provide student ID.")
            
            elif choice == "6":
                # Update all supervisor project counts
                print("\n🔄 Updating all supervisor project counts...")
                supervisors = await manager.supervisors_collection.find({}).to_list(length=None)
                
                for supervisor in supervisors:
                    await manager.update_supervisor_project_count(str(supervisor["_id"]))
                
                print(f"✅ Updated project counts for {len(supervisors)} supervisors.")
            
            elif choice == "7":
                # Exit
                print("\n👋 Goodbye!")
                break
            
            else:
                print("\n❌ Invalid choice. Please select 1-7.")
                
            input("\nPress Enter to continue...")
    
    finally:
        await manager.disconnect()


async def main():
    """Main function."""
    if len(sys.argv) > 1:
        if sys.argv[1] == "--assign" and len(sys.argv) >= 4:
            # Command line assignment
            student_id = sys.argv[2]
            supervisor_id = sys.argv[3]
            
            manager = SupervisorAssignmentManager()
            await manager.connect()
            
            try:
                result = await manager.assign_supervisor_to_student(student_id, supervisor_id)
                if result["success"]:
                    print(f"✅ {result['message']}")
                else:
                    print(f"❌ Assignment failed: {result['error']}")
            finally:
                await manager.disconnect()
        else:
            print("Usage: python supervisor_assignment.py --assign <student_id> <supervisor_id>")
            print("   or: python supervisor_assignment.py (for interactive mode)")
    else:
        # Interactive mode
        await interactive_supervisor_assignment()


if __name__ == "__main__":
    asyncio.run(main())
