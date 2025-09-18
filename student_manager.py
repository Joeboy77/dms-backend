#!/usr/bin/env python3
"""
Student Management Script with CRUD functionality.
Supports Create, Read, Update, Delete operations for students.
Uses actual database configuration from the main application.
"""

import asyncio
import os
import random
import sys
import bcrypt
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
    raise Value            print("6. 🔄 Populate with random students")
            print("7. 🔐 Setup student logins (PIN: 12345)")
            print("8. 📊 Check login status")
            print("9. 🔑 Change student PIN")
            print("10. 👨‍🏫 Assign supervisor to student")
            print("11. 🔍 View student's supervisor")
            print("12. 🚪 Exit")
            print("="*60)
            
            choice = input("Enter your choice (1-12): ").strip()MONGO_URL environment variable is required")

print(f"🔗 Connecting to database: {DB_NAME}")
print(f"🌐 MongoDB URL: {MONGO_URL[:20]}...")


class StudentManager:
    """Class to handle CRUD operations for students using real database."""
    
    def __init__(self):
        self.client = None
        self.db = None
        self.students_collection = None
        self.programs_collection = None
        self.levels_collection = None
        self.academic_years_collection = None
        self.class_groups_collection = None
        self.supervisors_collection = None
        self.fyps_collection = None
        self.logins_collection = None
        self.roles_collection = None
    
    async def connect(self):
        """Connect to MongoDB using environment configuration."""
        self.client = AsyncIOMotorClient(MONGO_URL)
        self.db = self.client[DB_NAME]
        self.students_collection = self.db.students
        self.programs_collection = self.db.programs
        self.levels_collection = self.db.levels
        self.academic_years_collection = self.db.academic_years
        self.class_groups_collection = self.db.class_groups
        self.supervisors_collection = self.db.supervisors
        self.fyps_collection = self.db.fyps
        self.logins_collection = self.db.logins
        self.roles_collection = self.db.roles
        print("🔗 Connected to MongoDB")
        
        # Verify connection by checking collections
        collections = await self.db.list_collection_names()
        print(f"📂 Available collections: {len(collections)}")
    
    async def disconnect(self):
        """Disconnect from MongoDB."""
        if self.client:
            self.client.close()
            print("🔌 Database connection closed")
    
    async def get_available_references(self):
        """Get available reference data from database."""
        try:
            # Get non-deleted programs
            programs = await self.programs_collection.find(
                {"$or": [{"deleted": {"$exists": False}}, {"deleted": False}]}
            ).to_list(length=None)
            
            # Get non-deleted levels  
            levels = await self.levels_collection.find(
                {"$or": [{"deleted": {"$exists": False}}, {"deleted": False}]}
            ).to_list(length=None)
            
            # Get non-deleted academic years
            academic_years = await self.academic_years_collection.find(
                {"$or": [{"deleted": {"$exists": False}}, {"deleted": False}]}
            ).to_list(length=None)
            
            # Get class groups
            class_groups = await self.class_groups_collection.find({}).to_list(length=None)
            
            return {
                "programs": [str(p["_id"]) for p in programs],
                "levels": [str(l["_id"]) for l in levels], 
                "academic_years": [str(a["_id"]) for a in academic_years],
                "class_groups": [str(c["_id"]) for c in class_groups]
            }
        except Exception as e:
            print(f"❌ Error getting reference data: {e}")
            return {"programs": [], "levels": [], "academic_years": [], "class_groups": []}
    
    async def generate_random_student(self, refs: Dict):
        """Generate a random student using actual database references."""
        titles = ["Mr", "Mrs", "Miss", "Dr", "Prof"]
        first_names = [
            "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
            "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica"
        ]
        last_names = [
            "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
            "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson"
        ]
        email_domains = ["gmail.com", "yahoo.com", "st.ug.edu.gh", "outlook.com"]
        student_types = ["UNDERGRADUATE", "DEFERRED"]
        
        title = random.choice(titles)
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        
        # Generate unique academic ID
        academic_id = str(random.randint(10000000, 19999999))
        
        # Use actual reference IDs from database
        program_id = ObjectId(random.choice(refs["programs"])) if refs["programs"] else None
        level_id = ObjectId(random.choice(refs["levels"])) if refs["levels"] else None
        admission_year = ObjectId(random.choice(refs["academic_years"])) if refs["academic_years"] else None
        current_academic_year = ObjectId(random.choice(refs["academic_years"])) if refs["academic_years"] else None
        class_group = ObjectId(random.choice(refs["class_groups"])) if refs["class_groups"] else None
        
        # Generate academic years list
        academic_years = []
        if admission_year:
            academic_years.append(admission_year)
        if current_academic_year and current_academic_year != admission_year:
            academic_years.append(current_academic_year)
        
        # Generate email
        username = f"{first_name.lower()}.{last_name.lower()}{random.randint(1, 999)}"
        email = f"{username}@{random.choice(email_domains)}"
        
        # Generate phone
        phone = f"0{random.randint(200000000, 599999999)}"
        
        student = {
            "title": title,
            "surname": last_name,
            "otherNames": first_name,
            "email": email,
            "phone": phone,
            "program": program_id,
            "level": level_id,
            "academicId": academic_id,
            "academicYears": academic_years,
            "deleted": False,
            "type": random.choice(student_types),
            "admissionYear": admission_year,
            "currentAcademicYear": current_academic_year,
            "classGroup": class_group,
            "image": "",
            "createdAt": datetime.now(timezone.utc),
            "updatedAt": datetime.now(timezone.utc)
        }
        
        return student
    
    async def create_student(self, student_data: Dict) -> str:
        """Create a new student."""
        try:
            # Add timestamps
            student_data["createdAt"] = datetime.now(timezone.utc)
            student_data["updatedAt"] = datetime.now(timezone.utc)
            
            result = await self.students_collection.insert_one(student_data)
            print(f"✅ Created student with ID: {result.inserted_id}")
            return str(result.inserted_id)
        except Exception as e:
            print(f"❌ Error creating student: {e}")
            return None
    
    async def read_students(self, limit: int = 10, skip: int = 0) -> List[Dict]:
        """Read students with pagination."""
        try:
            cursor = self.students_collection.find({}).skip(skip).limit(limit)
            students = await cursor.to_list(length=limit)
            return students
        except Exception as e:
            print(f"❌ Error reading students: {e}")
            return []
    
    async def read_student_by_id(self, student_id: str) -> Optional[Dict]:
        """Read a specific student by ID."""
        try:
            student = await self.students_collection.find_one({"_id": ObjectId(student_id)})
            return student
        except Exception as e:
            print(f"❌ Error reading student: {e}")
            return None
    
    async def update_student(self, student_id: str, update_data: Dict) -> bool:
        """Update a student by ID."""
        try:
            # Add update timestamp
            update_data["updatedAt"] = datetime.now(timezone.utc)
            
            result = await self.students_collection.update_one(
                {"_id": ObjectId(student_id)},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                print(f"✅ Updated student with ID: {student_id}")
                return True
            else:
                print(f"⚠️ No student found with ID: {student_id}")
                return False
        except Exception as e:
            print(f"❌ Error updating student: {e}")
            return False
    
    async def delete_student(self, student_id: str) -> bool:
        """Delete a student by ID."""
        try:
            result = await self.students_collection.delete_one({"_id": ObjectId(student_id)})
            
            if result.deleted_count > 0:
                print(f"✅ Deleted student with ID: {student_id}")
                return True
            else:
                print(f"⚠️ No student found with ID: {student_id}")
                return False
        except Exception as e:
            print(f"❌ Error deleting student: {e}")
            return False
    
    async def search_students(self, query: str) -> List[Dict]:
        """Search students by name or email."""
        try:
            search_filter = {
                "$or": [
                    {"surname": {"$regex": query, "$options": "i"}},
                    {"otherNames": {"$regex": query, "$options": "i"}},
                    {"email": {"$regex": query, "$options": "i"}},
                    {"academicId": {"$regex": query, "$options": "i"}}
                ]
            }
            cursor = self.students_collection.find(search_filter)
            students = await cursor.to_list(length=50)
            return students
        except Exception as e:
            print(f"❌ Error searching students: {e}")
            return []
    
    async def get_student_count(self) -> int:
        """Get total number of students."""
        try:
            count = await self.students_collection.count_documents({})
            return count
        except Exception as e:
            print(f"❌ Error counting students: {e}")
            return 0
    
    async def clear_all_students(self) -> int:
        """Clear all students from the database."""
        try:
            result = await self.students_collection.delete_many({})
            print(f"✅ Deleted {result.deleted_count} student records")
            return result.deleted_count
        except Exception as e:
            print(f"❌ Error clearing students: {e}")
            return 0
    
    # PIN and Login Management Methods
    
    def hash_pin(self, pin: str) -> str:
        """Hash a PIN using bcrypt."""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(pin.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    async def get_student_role_id(self) -> str:
        """Get the student role ID, create if it doesn't exist."""
        try:
            # Look for an existing student role
            student_role = await self.roles_collection.find_one({
                "slug": {"$in": ["student", "students"]},
                "deleted": {"$ne": True}
            })
            
            if student_role:
                return str(student_role["_id"])
            
            # Create a new student role if none exists
            role_data = {
                "title": "Student",
                "slug": "student", 
                "status": "active",
                "description": "Student role for dashboard access",
                "deleted": False,
                "createdAt": datetime.now(timezone.utc),
                "updatedAt": datetime.now(timezone.utc)
            }
            
            result = await self.roles_collection.insert_one(role_data)
            print(f"📝 Created new student role: {result.inserted_id}")
            return str(result.inserted_id)
        except Exception as e:
            print(f"❌ Error getting student role: {e}")
            return ""
    
    async def check_student_login_exists(self, academic_id: str) -> bool:
        """Check if a student already has a login record."""
        try:
            existing = await self.logins_collection.find_one({"academicId": academic_id})
            return existing is not None
        except Exception as e:
            print(f"❌ Error checking login: {e}")
            return False
    
    async def create_student_login(self, student: Dict, pin: str = "12345") -> bool:
        """Create a login record for a student."""
        try:
            academic_id = student.get("academicId")
            if not academic_id:
                print(f"⚠️ Student {student['_id']} has no academic ID")
                return False
            
            # Check if login already exists
            if await self.check_student_login_exists(academic_id):
                print(f"ℹ️ Login already exists for student {academic_id}")
                return True
            
            # Get student role ID
            student_role_id = await self.get_student_role_id()
            if not student_role_id:
                print("❌ Could not get student role ID")
                return False
            
            # Hash the PIN
            hashed_pin = self.hash_pin(pin)
            
            # Create login record
            login_data = {
                "academicId": academic_id,
                "pin": hashed_pin,
                "roles": [ObjectId(student_role_id)],
                "createdAt": datetime.now(timezone.utc),
                "updatedAt": datetime.now(timezone.utc),
                "lastLogin": None,
                "token": None
            }
            
            result = await self.logins_collection.insert_one(login_data)
            student_name = f"{student.get('title', '')} {student.get('surname', '')} {student.get('otherNames', '')}".strip()
            print(f"✅ Created login for {student_name} (ID: {academic_id})")
            return True
            
        except Exception as e:
            print(f"❌ Error creating login for student {student.get('_id')}: {e}")
            return False
    
    async def update_student_pin(self, academic_id: str, new_pin: str) -> bool:
        """Update a student's PIN."""
        try:
            # Hash the new PIN
            hashed_pin = self.hash_pin(new_pin)
            
            # Update the login record
            result = await self.logins_collection.update_one(
                {"academicId": academic_id},
                {
                    "$set": {
                        "pin": hashed_pin,
                        "updatedAt": datetime.now(timezone.utc)
                    }
                }
            )
            
            if result.modified_count > 0:
                print(f"✅ Updated PIN for student {academic_id}")
                return True
            else:
                print(f"⚠️ No login found for student {academic_id}")
                return False
                
        except Exception as e:
            print(f"❌ Error updating PIN for student {academic_id}: {e}")
            return False
    
    async def setup_login_for_student(self, student_id: str, pin: str = "12345") -> bool:
        """Set up login for a specific student."""
        try:
            student = await self.read_student_by_id(student_id)
            if not student:
                print(f"❌ Student {student_id} not found")
                return False
            
            return await self.create_student_login(student, pin)
        except Exception as e:
            print(f"❌ Error setting up login for student {student_id}: {e}")
            return False
    
    async def setup_logins_for_all_students(self, default_pin: str = "12345") -> Dict:
        """Set up login records for all students."""
        try:
            students = await self.read_students(limit=1000)  # Get all students
            
            created_count = 0
            existing_count = 0
            error_count = 0
            
            for student in students:
                academic_id = student.get("academicId")
                if not academic_id:
                    error_count += 1
                    continue
                
                if await self.check_student_login_exists(academic_id):
                    existing_count += 1
                else:
                    if await self.create_student_login(student, default_pin):
                        created_count += 1
                    else:
                        error_count += 1
            
            return {
                "total_students": len(students),
                "created": created_count,
                "existing": existing_count,
                "errors": error_count,
                "default_pin": default_pin
            }
        except Exception as e:
            print(f"❌ Error setting up logins: {e}")
            return {"error": str(e)}
    
    async def get_student_login_status(self) -> List[Dict]:
        """Get login status for all students."""
        try:
            students = await self.read_students(limit=1000)
            status_list = []
            
            for student in students:
                academic_id = student.get("academicId")
                student_name = f"{student.get('title', '')} {student.get('surname', '')} {student.get('otherNames', '')}".strip()
                
                has_login = await self.check_student_login_exists(academic_id) if academic_id else False
                
                status_list.append({
                    "student_id": str(student["_id"]),
                    "student_name": student_name,
                    "academic_id": academic_id,
                    "email": student.get("email"),
                    "has_login": has_login
                })
            
            return status_list
        except Exception as e:
            print(f"❌ Error getting login status: {e}")
            return []


    async def assign_supervisor_to_student(self, student_id: str, supervisor_id: str) -> Dict:
        """Assign a supervisor to a student."""
        try:
            # Validate student exists
            student = await self.read_student_by_id(student_id)
            if not student:
                return {"success": False, "error": "Student not found"}
            
            # Validate supervisor exists
            supervisor = await self.supervisors_collection.find_one({"_id": ObjectId(supervisor_id)})
            if not supervisor:
                return {"success": False, "error": "Supervisor not found"}
            
            # Check supervisor capacity
            if supervisor.get("project_student_count", 0) >= supervisor.get("max_students", 0):
                return {"success": False, "error": "Supervisor has reached maximum capacity"}
            
            # Get current FYP checkin (create one if none exists)
            checkin = await self.fyps_collection.find_one({}, sort=[("createdAt", -1)])
            if not checkin:
                # Create a default checkin
                checkin_data = {
                    "academicYear": student.get("currentAcademicYear"),
                    "term": 1,
                    "status": "active",
                    "createdAt": datetime.now(timezone.utc),
                    "updatedAt": datetime.now(timezone.utc)
                }
                result = await self.db.fypcheckins.insert_one(checkin_data)
                checkin_id = result.inserted_id
            else:
                checkin_id = checkin.get("checkin")
                if not checkin_id:
                    # Create new checkin
                    checkin_data = {
                        "academicYear": student.get("currentAcademicYear"),
                        "term": 1,
                        "status": "active", 
                        "createdAt": datetime.now(timezone.utc),
                        "updatedAt": datetime.now(timezone.utc)
                    }
                    result = await self.db.fypcheckins.insert_one(checkin_data)
                    checkin_id = result.inserted_id
            
            # Check if assignment already exists
            existing_fyp = await self.fyps_collection.find_one({
                "student": ObjectId(student_id),
                "checkin": checkin_id
            })
            
            if existing_fyp:
                # Update existing assignment
                await self.fyps_collection.update_one(
                    {"_id": existing_fyp["_id"]},
                    {
                        "$set": {
                            "supervisor": supervisor["lecturer_id"],
                            "updatedAt": datetime.now(timezone.utc)
                        }
                    }
                )
                action = "updated"
            else:
                # Create new assignment
                fyp_data = {
                    "student": ObjectId(student_id),
                    "supervisor": supervisor["lecturer_id"],
                    "checkin": checkin_id,
                    "projectArea": None,
                    "createdAt": datetime.now(timezone.utc),
                    "updatedAt": datetime.now(timezone.utc)
                }
                await self.fyps_collection.insert_one(fyp_data)
                action = "created"
            
            # Update supervisor project count
            new_count = await self.fyps_collection.count_documents({
                "supervisor": supervisor["lecturer_id"]
            })
            
            await self.supervisors_collection.update_one(
                {"_id": ObjectId(supervisor_id)},
                {
                    "$set": {
                        "project_student_count": new_count,
                        "updatedAt": datetime.now(timezone.utc)
                    }
                }
            )
            
            return {
                "success": True,
                "action": action,
                "message": f"Successfully {action} supervisor assignment"
            }
            
        except Exception as e:
            print(f"❌ Error assigning supervisor: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_student_supervisor(self, student_id: str) -> Optional[Dict]:
        """Get the current supervisor for a student."""
        try:
            # Find the student's FYP record
            fyp = await self.fyps_collection.find_one(
                {"student": ObjectId(student_id)},
                sort=[("createdAt", -1)]
            )
            
            if not fyp or not fyp.get("supervisor"):
                return None
            
            # Get supervisor details
            supervisor = await self.supervisors_collection.find_one({
                "lecturer_id": fyp["supervisor"]
            })
            
            if not supervisor:
                return None
            
            # Get lecturer details
            lecturer = await self.db.lecturers.find_one({
                "_id": supervisor["lecturer_id"]
            })
            
            if not lecturer:
                return None
            
            return {
                "supervisor_id": str(supervisor["_id"]),
                "lecturer_id": str(lecturer["_id"]),
                "lecturer_name": f"{lecturer.get('title', '')} {lecturer.get('surname', '')} {lecturer.get('otherNames', '')}".strip(),
                "lecturer_email": lecturer.get("email"),
                "assigned_at": fyp.get("createdAt")
            }
            
        except Exception as e:
            print(f"❌ Error getting student supervisor: {e}")
            return None


async def clear_and_populate_students(manager: StudentManager, count: int = 10):
    """Clear existing students and populate with random students using real database references."""
    try:
        # Get available reference data from database
        print("📚 Loading reference data from database...")
        refs = await manager.get_available_references()
        
        print(f"📊 Found {len(refs['programs'])} programs, {len(refs['levels'])} levels, "
              f"{len(refs['academic_years'])} academic years, {len(refs['class_groups'])} class groups")
        
        if not refs["programs"] or not refs["levels"]:
            print("❌ Missing required reference data (programs or levels). Cannot create students.")
            return
        
        # Count existing students
        existing_count = await manager.get_student_count()
        print(f"📊 Found {existing_count} existing students")
        
        # Clear existing students
        if existing_count > 0:
            print("🗑️  Clearing existing student data...")
            deleted_count = await manager.clear_all_students()
        
        # Generate random students using real database references
        print(f"👥 Generating {count} random students with real database references...")
        created_count = 0
        
        for i in range(count):
            student = await manager.generate_random_student(refs)
            print(f"   {i+1}. {student['title']} {student['surname']}, {student['otherNames']} ({student['email']})")
            
            student_id = await manager.create_student(student)
            if student_id:
                created_count += 1
        
        # Verify the operation
        new_count = await manager.get_student_count()
        print(f"📊 Database now contains {new_count} students")
        print(f"🎉 Successfully created {created_count} students with real database references!")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def display_student(student: Dict, show_id: bool = True):
    """Display a student in a formatted way."""
    if show_id:
        print(f"ID: {student['_id']}")
    print(f"Name: {student.get('title', '')} {student.get('surname', '')} {student.get('otherNames', '')}")
    print(f"Email: {student.get('email', '')}")
    print(f"Phone: {student.get('phone', '')}")
    print(f"Academic ID: {student.get('academicId', '')}")
    print(f"Type: {student.get('type', '')}")
    print(f"Created: {student.get('createdAt', '')}")
    print("-" * 50)


async def interactive_menu():
    """Interactive menu for CRUD operations."""
    manager = StudentManager()
    await manager.connect()
    
    try:
        while True:
            print("\n" + "="*60)
            print("🎓 STUDENT MANAGEMENT SYSTEM")
            print("="*60)
            print("1. 📋 List all students")
            print("2. 🔍 Search students")
            print("3. 👤 View student by ID")
            print("4. 📊 Show student count")
            print("5. 🗑️ Clear all students")
            print("6. 🔄 Populate with random students")
            print("7. �‍🏫 Assign supervisor to student")
            print("8. 🔍 View student's supervisor")
            print("9. �🚪 Exit")
            print("="*60)
            
            choice = input("Enter your choice (1-9): ").strip()
            
            if choice == "1":
                # List all students
                print("\n📋 Listing all students...")
                students = await manager.read_students(limit=50)
                if students:
                    for i, student in enumerate(students, 1):
                        print(f"\n{i}.")
                        display_student(student)
                else:
                    print("No students found.")
            
            elif choice == "2":
                # Search students
                query = input("\n🔍 Enter search term (name, email, or academic ID): ").strip()
                if query:
                    students = await manager.search_students(query)
                    if students:
                        print(f"\n🔍 Found {len(students)} students:")
                        for i, student in enumerate(students, 1):
                            print(f"\n{i}.")
                            display_student(student)
                    else:
                        print("No students found matching your search.")
                else:
                    print("Search term cannot be empty.")
            
            elif choice == "3":
                # View student by ID
                student_id = input("\n👤 Enter student ID: ").strip()
                if student_id:
                    student = await manager.read_student_by_id(student_id)
                    if student:
                        print("\n👤 Student details:")
                        display_student(student)
                    else:
                        print("Student not found.")
                else:
                    print("Student ID cannot be empty.")
            
            elif choice == "4":
                # Show student count
                count = await manager.get_student_count()
                print(f"\n📊 Total students in database: {count}")
            
            elif choice == "5":
                # Clear all students
                count = await manager.get_student_count()
                if count > 0:
                    confirm = input(f"\n⚠️ This will delete all {count} students. Are you sure? (yes/no): ").strip().lower()
                    if confirm in ['yes', 'y']:
                        deleted = await manager.clear_all_students()
                        print(f"✅ Cleared {deleted} students from database.")
                    else:
                        print("Clear operation cancelled.")
                else:
                    print("Database is already empty.")
            
            elif choice == "6":
                # Populate with random students
                try:
                    count = int(input("\n🔄 How many random students to create? (default 10): ").strip() or "10")
                    await clear_and_populate_students(manager, count)
                except ValueError:
                    print("Invalid number. Using default of 10.")
                    await clear_and_populate_students(manager, 10)
            
            elif choice == "7":
                # Assign supervisor to student
                student_id = input("\n👤 Enter student ID: ").strip()
                supervisor_id = input("👨‍🏫 Enter supervisor ID: ").strip()
                
                if student_id and supervisor_id:
                    print("\n🔄 Processing assignment...")
                    result = await manager.assign_supervisor_to_student(student_id, supervisor_id)
                    
                    if result["success"]:
                        print(f"✅ {result['message']}")
                    else:
                        print(f"❌ Assignment failed: {result['error']}")
                else:
                    print("❌ Please provide both student ID and supervisor ID.")
            
            elif choice == "8":
                # View student's supervisor
                student_id = input("\n👤 Enter student ID: ").strip()
                
                if student_id:
                    supervisor = await manager.get_student_supervisor(student_id)
                    if supervisor:
                        print(f"\n👨‍🏫 Current Supervisor:")
                        print(f"   Name: {supervisor['lecturer_name']}")
                        print(f"   Email: {supervisor['lecturer_email']}")
                        print(f"   Assigned: {supervisor['assigned_at']}")
                    else:
                        print("\n⚠️ No supervisor assigned to this student.")
                else:
                    print("❌ Please provide student ID.")
            
            elif choice == "9":
                # Exit
                print("\n👋 Goodbye!")
                break
            
            else:
                print("\n❌ Invalid choice. Please select 1-9.")
                
            input("\nPress Enter to continue...")
    
    finally:
        await manager.disconnect()


async def main():
    """Main function to run the script."""
    if len(sys.argv) > 1 and sys.argv[1] == "--populate":
        # Command line mode for population
        print("🚀 Starting student data clearing and population process...")
        print("=" * 60)
        
        manager = StudentManager()
        await manager.connect()
        try:
            count = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            await clear_and_populate_students(manager, count)
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
