#!/usr/bin/env python3
"""
Student Management Script with CRUD functionality.
Supports Create, Read, Update, Delete operations for students.
"""

import asyncio
import os
import random
import sys
from datetime import datetime
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

# Known IDs from the database
PROGRAM_IDS = [
    "667891f4b56bb702c91d00f9",  # BSc. Information Technology
    "667b2945b56bb702c91d8b85",  # BSc. Computer Science
]

LEVEL_IDS = [
    "6658bec5ffc9143d8f09125e",  # 200
]

ACADEMIC_YEAR_IDS = [
    "665b3dc030aaee8906b3cd2e",  # 2011/2012
    "665b3dc930aaee8906b3cd36",  # 2012/2013
    "665b3dd430aaee8906b3cd3e",  # 2013/2014
]

CLASS_GROUP_IDS = [
    "667a82d9e8096f1935dbd201",  # SHORT COURSE STUDENT
    "667a82f2e8096f1935dbd202",  # MATURED STUDENT
    "667ddeb5c4c3dc6c25b02723",  # VISITING STUDENT
]

TITLES = ["Mr", "Mrs", "Miss", "Dr", "Prof"]
STUDENT_TYPES = ["UNDERGRADUATE", "DEFERRED"]

# Sample names for random generation
FIRST_NAMES = [
    "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
    "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Christopher", "Karen", "Charles", "Nancy", "Daniel", "Lisa",
    "Matthew", "Betty", "Anthony", "Helen", "Mark", "Sandra", "Donald", "Donna"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas",
    "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White",
    "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker", "Young"
]

EMAIL_DOMAINS = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "st.ug.edu.gh"]


def generate_academic_id():
    """Generate a random academic ID."""
    return str(random.randint(10000000, 19999999))


def generate_phone_number():
    """Generate a random phone number."""
    return f"0{random.randint(200000000, 599999999)}"


def generate_email(first_name, last_name):
    """Generate a random email address."""
    username = f"{first_name.lower()}.{last_name.lower()}{random.randint(1, 999)}"
    domain = random.choice(EMAIL_DOMAINS)
    return f"{username}@{domain}"


def generate_random_student():
    """Generate a random student document."""
    title = random.choice(TITLES)
    first_name = random.choice(FIRST_NAMES)
    last_name = random.choice(LAST_NAMES)
    
    # Select random IDs from available options
    program_id = ObjectId(random.choice(PROGRAM_IDS))
    level_id = ObjectId(random.choice(LEVEL_IDS))
    admission_year = ObjectId(random.choice(ACADEMIC_YEAR_IDS))
    current_academic_year = ObjectId(random.choice(ACADEMIC_YEAR_IDS))
    class_group = ObjectId(random.choice(CLASS_GROUP_IDS))
    
    # Generate academic years list (admission year + current year)
    academic_years = [admission_year]
    if current_academic_year != admission_year:
        academic_years.append(current_academic_year)
    
    student = {
        "title": title,
        "surname": last_name,
        "otherNames": first_name,
        "email": generate_email(first_name, last_name),
        "phone": generate_phone_number(),
        "program": program_id,
        "level": level_id,
        "academicId": generate_academic_id(),
        "academicYears": academic_years,
        "deleted": False,
        "type": random.choice(STUDENT_TYPES),
        "admissionYear": admission_year,
        "currentAcademicYear": current_academic_year,
        "classGroup": class_group,
        "image": "",
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow()
    }
    
    return student


class StudentManager:
    """Class to handle CRUD operations for students."""
    
    def __init__(self):
        self.client = None
        self.db = None
        self.students_collection = None
    
    async def connect(self):
        """Connect to MongoDB."""
        self.client = AsyncIOMotorClient(MONGO_URL)
        self.db = self.client[DB_NAME]
        self.students_collection = self.db.students
        print("🔗 Connected to MongoDB")
    
    async def disconnect(self):
        """Disconnect from MongoDB."""
        if self.client:
            self.client.close()
            print("🔌 Database connection closed")
    
    async def create_student(self, student_data: Dict) -> str:
        """Create a new student."""
        try:
            # Add timestamps
            student_data["createdAt"] = datetime.utcnow()
            student_data["updatedAt"] = datetime.utcnow()
            
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
            update_data["updatedAt"] = datetime.utcnow()
            
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


async def main():
    """Main function to run the script."""
    print("🚀 Starting student data clearing and population process...")
    print("=" * 60)
    
    await clear_and_populate_students()
    
    print("=" * 60)
    print("✨ Process completed!")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
