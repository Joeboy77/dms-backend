#!/usr/bin/env python3
"""
Simple test to verify student logins are working correctly.
"""

import asyncio
import os
import bcrypt
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME", "development")

async def test_student_logins():
    """Test that student logins are working correctly."""
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    print("🔍 STUDENT LOGIN VERIFICATION TEST")
    print("=" * 50)
    
    # Get all students
    students = await db.students.find({"deleted": {"$ne": True}}).to_list(length=None)
    print(f"👥 Found {len(students)} students")
    
    # Check login records
    login_count = 0
    working_logins = 0
    
    for student in students:
        academic_id = student.get("academicId")
        student_name = f"{student.get('title', '')} {student.get('surname', '')} {student.get('otherNames', '')}".strip()
        
        if academic_id:
            # Check if login exists
            login = await db.logins.find_one({"academicId": academic_id})
            
            if login:
                login_count += 1
                
                # Test PIN verification (PIN should be "12345")
                stored_pin = login.get("pin")
                if stored_pin:
                    # Verify the default PIN
                    pin_matches = bcrypt.checkpw("12345".encode('utf-8'), stored_pin.encode('utf-8'))
                    if pin_matches:
                        working_logins += 1
                        print(f"✅ {student_name} (ID: {academic_id}) - Login works with PIN 12345")
                    else:
                        print(f"❌ {student_name} (ID: {academic_id}) - PIN verification failed")
                else:
                    print(f"⚠️ {student_name} (ID: {academic_id}) - No PIN set")
            else:
                print(f"❌ {student_name} (ID: {academic_id}) - No login record")
    
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS")
    print(f"👥 Total students: {len(students)}")
    print(f"🔐 Students with logins: {login_count}")
    print(f"✅ Working logins (PIN 12345): {working_logins}")
    print(f"❌ Failed/Missing logins: {len(students) - working_logins}")
    
    if working_logins == len(students):
        print("🎉 All students can login with PIN 12345!")
    else:
        print(f"⚠️ {len(students) - working_logins} students need login setup")
    
    # Show some sample login data
    print("\n📋 Sample Login Records:")
    sample_logins = await db.logins.find({}).limit(3).to_list(length=3)
    
    for login in sample_logins:
        roles_count = len(login.get("roles", []))
        last_login = login.get("lastLogin", "Never")
        print(f"   🆔 {login['academicId']} | {roles_count} roles | Last: {last_login}")
    
    client.close()

if __name__ == "__main__":
    print("🚀 Testing student login functionality...")
    asyncio.run(test_student_logins())
