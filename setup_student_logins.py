#!/usr/bin/env python3
"""
Student Login Setup Script.
Creates login records for all students with a default PIN (12345) 
so they can access their unique dashboards.
"""

import asyncio
import os
import bcrypt
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

# Default PIN for all students
DEFAULT_PIN = "12345"


class StudentLoginManager:
    """Class to handle student login setup."""
    
    def __init__(self):
        self.client = None
        self.db = None
        self.students_collection = None
        self.logins_collection = None
        self.roles_collection = None
    
    async def connect(self):
        """Connect to MongoDB."""
        self.client = AsyncIOMotorClient(MONGO_URL)
        self.db = self.client[DB_NAME]
        self.students_collection = self.db.students
        self.logins_collection = self.db.logins
        self.roles_collection = self.db.roles
        print("🔗 Connected to MongoDB")
    
    async def disconnect(self):
        """Disconnect from MongoDB."""
        if self.client:
            self.client.close()
            print("🔌 Database connection closed")
    
    def hash_pin(self, pin: str) -> str:
        """Hash a PIN using bcrypt."""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(pin.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    async def get_student_role_id(self) -> str:
        """Get the student role ID, create if it doesn't exist."""
        # Look for an existing student role
        student_role = await self.roles_collection.find_one({
            "slug": {"$in": ["student", "students"]},
            "deleted": {"$ne": True}
        })
        
        if student_role:
            print(f"✅ Found existing student role: {student_role['_id']}")
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
    
    async def get_all_students(self) -> List[Dict]:
        """Get all active students."""
        try:
            students = await self.students_collection.find({
                "deleted": {"$ne": True}
            }).to_list(length=None)
            return students
        except Exception as e:
            print(f"❌ Error getting students: {e}")
            return []
    
    async def check_existing_login(self, academic_id: str) -> bool:
        """Check if a student already has a login record."""
        try:
            existing = await self.logins_collection.find_one({"academicId": academic_id})
            return existing is not None
        except Exception as e:
            print(f"❌ Error checking existing login: {e}")
            return False
    
    async def create_student_login(self, student: Dict, student_role_id: str) -> bool:
        """Create a login record for a student."""
        try:
            academic_id = student.get("academicId")
            if not academic_id:
                print(f"⚠️ Student {student['_id']} has no academic ID")
                return False
            
            # Check if login already exists
            if await self.check_existing_login(academic_id):
                print(f"ℹ️ Login already exists for student {academic_id}")
                return True
            
            # Hash the default PIN
            hashed_pin = self.hash_pin(DEFAULT_PIN)
            
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
            
            # Get student name for display
            student_name = f"{student.get('title', '')} {student.get('surname', '')} {student.get('otherNames', '')}".strip()
            
            print(f"✅ Created login for {student_name} (ID: {academic_id})")
            return True
            
        except Exception as e:
            print(f"❌ Error creating login for student {student.get('_id')}: {e}")
            return False
    
    async def update_existing_student_login(self, academic_id: str, student_role_id: str) -> bool:
        """Update existing login to ensure it has student role and correct PIN."""
        try:
            # Hash the default PIN
            hashed_pin = self.hash_pin(DEFAULT_PIN)
            
            # Update the login record
            result = await self.logins_collection.update_one(
                {"academicId": academic_id},
                {
                    "$set": {
                        "pin": hashed_pin,
                        "updatedAt": datetime.now(timezone.utc)
                    },
                    "$addToSet": {
                        "roles": ObjectId(student_role_id)
                    }
                }
            )
            
            if result.modified_count > 0:
                print(f"📝 Updated login for student {academic_id}")
                return True
            else:
                print(f"ℹ️ No changes needed for student {academic_id}")
                return True
                
        except Exception as e:
            print(f"❌ Error updating login for student {academic_id}: {e}")
            return False
    
    async def setup_all_student_logins(self):
        """Set up login records for all students."""
        print("🚀 Setting up student logins...")
        print("=" * 50)
        
        # Get student role ID
        student_role_id = await self.get_student_role_id()
        
        # Get all students
        students = await self.get_all_students()
        print(f"👥 Found {len(students)} students")
        
        if not students:
            print("⚠️ No students found in database")
            return
        
        # Process each student
        created_count = 0
        updated_count = 0
        skipped_count = 0
        
        for i, student in enumerate(students, 1):
            academic_id = student.get("academicId")
            student_name = f"{student.get('title', '')} {student.get('surname', '')} {student.get('otherNames', '')}".strip()
            
            print(f"\n{i}. Processing: {student_name}")
            print(f"   📧 Email: {student.get('email', 'N/A')}")
            print(f"   🆔 Academic ID: {academic_id}")
            
            if not academic_id:
                print(f"   ⚠️ Skipped: No academic ID")
                skipped_count += 1
                continue
            
            # Check if login exists
            if await self.check_existing_login(academic_id):
                # Update existing login
                if await self.update_existing_student_login(academic_id, student_role_id):
                    updated_count += 1
                    print(f"   🔄 Updated existing login")
                else:
                    skipped_count += 1
                    print(f"   ❌ Failed to update")
            else:
                # Create new login
                if await self.create_student_login(student, student_role_id):
                    created_count += 1
                    print(f"   ✅ Created new login")
                else:
                    skipped_count += 1
                    print(f"   ❌ Failed to create")
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 SUMMARY")
        print(f"✅ New logins created: {created_count}")
        print(f"🔄 Existing logins updated: {updated_count}")
        print(f"⚠️ Skipped: {skipped_count}")
        print(f"👥 Total students processed: {len(students)}")
        print(f"🔑 Default PIN for all students: {DEFAULT_PIN}")
        
        # Verify the setup
        await self.verify_student_logins()
    
    async def verify_student_logins(self):
        """Verify that all students have login records."""
        print("\n🔍 VERIFICATION")
        print("-" * 30)
        
        # Get all students
        students = await self.get_all_students()
        
        # Check each student's login
        login_count = 0
        missing_count = 0
        
        for student in students:
            academic_id = student.get("academicId")
            if academic_id:
                has_login = await self.check_existing_login(academic_id)
                if has_login:
                    login_count += 1
                else:
                    missing_count += 1
                    student_name = f"{student.get('surname', '')} {student.get('otherNames', '')}".strip()
                    print(f"❌ Missing login: {student_name} ({academic_id})")
        
        print(f"✅ Students with logins: {login_count}")
        print(f"❌ Students missing logins: {missing_count}")
        
        if missing_count == 0:
            print("🎉 All students have login records!")
        
        # Show sample login verification
        if login_count > 0:
            print("\n📋 Sample Login Records:")
            sample_logins = await self.logins_collection.find({
                "roles": {"$exists": True}
            }).limit(3).to_list(length=3)
            
            for login in sample_logins:
                print(f"   🆔 {login['academicId']} | Roles: {len(login.get('roles', []))}")


async def main():
    """Main function to set up student logins."""
    print("🚀 Starting Student Login Setup...")
    print("=" * 60)
    
    manager = StudentLoginManager()
    await manager.connect()
    
    try:
        await manager.setup_all_student_logins()
        
        print("\n" + "=" * 60)
        print("✨ Student login setup completed!")
        print("🔑 All students can now login with PIN: 12345")
        print("🎯 Students can access their unique dashboards")
        
    except Exception as e:
        print(f"❌ Error during setup: {e}")
    finally:
        await manager.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
