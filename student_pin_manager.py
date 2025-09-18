#!/usr/bin/env python3
"""
Student PIN Management Tool.
Allows updating student PINs and verifying login functionality.
"""

import asyncio
import os
import sys
import bcrypt
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from datetime import datetime, timezone

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME", "development")

class StudentPINManager:
    """Manage student PINs and login verification."""
    
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
    
    def hash_pin(self, pin: str) -> str:
        """Hash a PIN using bcrypt."""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(pin.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_pin(self, pin: str, hashed_pin: str) -> bool:
        """Verify a PIN against its hash."""
        try:
            return bcrypt.checkpw(pin.encode('utf-8'), hashed_pin.encode('utf-8'))
        except Exception:
            return False
    
    async def find_student_by_academic_id(self, academic_id: str):
        """Find a student by their academic ID."""
        try:
            student = await self.db.students.find_one({"academicId": academic_id})
            return student
        except Exception as e:
            print(f"❌ Error finding student: {e}")
            return None
    
    async def get_student_login(self, academic_id: str):
        """Get login record for a student."""
        try:
            login = await self.db.logins.find_one({"academicId": academic_id})
            return login
        except Exception as e:
            print(f"❌ Error getting login: {e}")
            return None
    
    async def update_student_pin(self, academic_id: str, new_pin: str) -> bool:
        """Update a student's PIN."""
        try:
            # Verify student exists
            student = await self.find_student_by_academic_id(academic_id)
            if not student:
                print(f"❌ Student with academic ID {academic_id} not found")
                return False
            
            # Hash the new PIN
            hashed_pin = self.hash_pin(new_pin)
            
            # Update the login record
            result = await self.db.logins.update_one(
                {"academicId": academic_id},
                {
                    "$set": {
                        "pin": hashed_pin,
                        "updatedAt": datetime.now(timezone.utc)
                    }
                }
            )
            
            if result.modified_count > 0:
                student_name = f"{student.get('title', '')} {student.get('surname', '')} {student.get('otherNames', '')}".strip()
                print(f"✅ Updated PIN for {student_name} (ID: {academic_id})")
                return True
            else:
                print(f"⚠️ No login record found for student {academic_id}")
                return False
                
        except Exception as e:
            print(f"❌ Error updating PIN: {e}")
            return False
    
    async def verify_student_login(self, academic_id: str, pin: str) -> bool:
        """Verify a student's login credentials."""
        try:
            # Get student info
            student = await self.find_student_by_academic_id(academic_id)
            if not student:
                print(f"❌ Student with academic ID {academic_id} not found")
                return False
            
            # Get login record
            login = await self.get_student_login(academic_id)
            if not login:
                print(f"❌ No login record found for student {academic_id}")
                return False
            
            # Verify PIN
            stored_pin = login.get("pin")
            if not stored_pin:
                print(f"❌ No PIN set for student {academic_id}")
                return False
            
            pin_matches = self.verify_pin(pin, stored_pin)
            
            student_name = f"{student.get('title', '')} {student.get('surname', '')} {student.get('otherNames', '')}".strip()
            
            if pin_matches:
                print(f"✅ Login successful for {student_name} (ID: {academic_id})")
                
                # Update last login time
                await self.db.logins.update_one(
                    {"academicId": academic_id},
                    {"$set": {"lastLogin": datetime.now(timezone.utc)}}
                )
                return True
            else:
                print(f"❌ Invalid PIN for {student_name} (ID: {academic_id})")
                return False
                
        except Exception as e:
            print(f"❌ Error verifying login: {e}")
            return False
    
    async def list_all_students(self):
        """List all students with their login status."""
        try:
            students = await self.db.students.find({"deleted": {"$ne": True}}).to_list(length=None)
            
            print(f"\n👥 ALL STUDENTS ({len(students)} total)")
            print("-" * 80)
            
            for i, student in enumerate(students, 1):
                academic_id = student.get("academicId")
                student_name = f"{student.get('title', '')} {student.get('surname', '')} {student.get('otherNames', '')}".strip()
                email = student.get("email", "N/A")
                
                # Check login status
                login = await self.get_student_login(academic_id) if academic_id else None
                has_login = "✅" if login else "❌"
                
                print(f"{i:2d}. {student_name}")
                print(f"    📧 Email: {email}")
                print(f"    🆔 Academic ID: {academic_id}")
                print(f"    🔐 Has Login: {has_login}")
                print()
                
        except Exception as e:
            print(f"❌ Error listing students: {e}")


async def interactive_menu():
    """Interactive menu for PIN management."""
    manager = StudentPINManager()
    await manager.connect()
    
    try:
        while True:
            print("\n" + "="*60)
            print("🔐 STUDENT PIN MANAGEMENT SYSTEM")
            print("="*60)
            print("1. 👥 List all students")
            print("2. 🔑 Change student PIN")
            print("3. ✅ Test student login")
            print("4. 🔄 Reset PIN to default (12345)")
            print("5. 🚪 Exit")
            print("="*60)
            
            choice = input("Enter your choice (1-5): ").strip()
            
            if choice == "1":
                # List all students
                await manager.list_all_students()
            
            elif choice == "2":
                # Change student PIN
                academic_id = input("\n🆔 Enter student academic ID: ").strip()
                new_pin = input("🔑 Enter new PIN: ").strip()
                
                if academic_id and new_pin:
                    success = await manager.update_student_pin(academic_id, new_pin)
                    if success:
                        print(f"🎉 PIN updated successfully!")
                    else:
                        print("❌ Failed to update PIN")
                else:
                    print("❌ Please provide both academic ID and new PIN")
            
            elif choice == "3":
                # Test student login
                academic_id = input("\n🆔 Enter student academic ID: ").strip()
                pin = input("🔑 Enter PIN: ").strip()
                
                if academic_id and pin:
                    success = await manager.verify_student_login(academic_id, pin)
                    if success:
                        print("🎉 Login test successful!")
                    else:
                        print("❌ Login test failed")
                else:
                    print("❌ Please provide both academic ID and PIN")
            
            elif choice == "4":
                # Reset PIN to default
                academic_id = input("\n🆔 Enter student academic ID: ").strip()
                
                if academic_id:
                    success = await manager.update_student_pin(academic_id, "12345")
                    if success:
                        print(f"🎉 PIN reset to default (12345)!")
                    else:
                        print("❌ Failed to reset PIN")
                else:
                    print("❌ Please provide academic ID")
            
            elif choice == "5":
                # Exit
                print("\n👋 Goodbye!")
                break
            
            else:
                print("\n❌ Invalid choice. Please select 1-5.")
                
            input("\nPress Enter to continue...")
    
    finally:
        await manager.disconnect()


async def main():
    """Main function."""
    if len(sys.argv) > 1:
        # Command line usage
        if sys.argv[1] == "--change-pin" and len(sys.argv) >= 4:
            academic_id = sys.argv[2]
            new_pin = sys.argv[3]
            
            manager = StudentPINManager()
            await manager.connect()
            
            try:
                success = await manager.update_student_pin(academic_id, new_pin)
                if success:
                    print("✅ PIN updated successfully!")
                else:
                    print("❌ Failed to update PIN")
            finally:
                await manager.disconnect()
        
        elif sys.argv[1] == "--test-login" and len(sys.argv) >= 4:
            academic_id = sys.argv[2]
            pin = sys.argv[3]
            
            manager = StudentPINManager()
            await manager.connect()
            
            try:
                success = await manager.verify_student_login(academic_id, pin)
                if success:
                    print("✅ Login successful!")
                else:
                    print("❌ Login failed")
            finally:
                await manager.disconnect()
        
        else:
            print("Usage:")
            print("  python student_pin_manager.py --change-pin <academic_id> <new_pin>")
            print("  python student_pin_manager.py --test-login <academic_id> <pin>")
            print("  python student_pin_manager.py (for interactive mode)")
    else:
        # Interactive mode
        await interactive_menu()


if __name__ == "__main__":
    asyncio.run(main())
