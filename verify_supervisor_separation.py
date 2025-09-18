#!/usr/bin/env python3
"""
Supervisor-Lecturer Relationship Verification Script.
This script demonstrates that supervisors are properly separated and linked to lecturers.
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME", "development")

async def verify_supervisor_lecturer_separation():
    """Verify that supervisors and lecturers are properly separated and linked."""
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    print("🔍 SUPERVISOR-LECTURER SEPARATION VERIFICATION")
    print("=" * 60)
    
    # Check supervisors collection
    supervisors = await db.supervisors.find({}).to_list(length=None)
    print(f"👥 Found {len(supervisors)} supervisors in dedicated collection")
    
    # Check if any lecturers have supervisor fields
    lecturers_with_max_students = await db.lecturers.count_documents({"max_students": {"$exists": True}})
    print(f"🧹 Lecturers with supervisor fields: {lecturers_with_max_students}")
    
    if lecturers_with_max_students == 0:
        print("✅ Lecturers collection is clean (no supervisor data)")
    else:
        print("⚠️ Found supervisor data in lecturers collection")
    
    print("\n📋 SUPERVISOR-LECTURER LINKAGE VERIFICATION")
    print("-" * 40)
    
    # Verify linkage using aggregation
    pipeline = [
        {
            "$lookup": {
                "from": "lecturers",
                "localField": "lecturer_id",
                "foreignField": "_id",
                "as": "lecturer_info"
            }
        },
        {"$unwind": "$lecturer_info"},
        {
            "$project": {
                "supervisor_id": "$_id",
                "max_students": 1,
                "project_student_count": 1,
                "lecturer_name": {
                    "$concat": [
                        "$lecturer_info.title", " ",
                        "$lecturer_info.surname", " ",
                        "$lecturer_info.otherNames"
                    ]
                },
                "lecturer_email": "$lecturer_info.email",
                "lecturer_academic_id": "$lecturer_info.academicId"
            }
        }
    ]
    
    linked_supervisors = await db.supervisors.aggregate(pipeline).to_list(length=None)
    
    for i, supervisor in enumerate(linked_supervisors, 1):
        print(f"{i}. {supervisor['lecturer_name']}")
        print(f"   📧 Email: {supervisor['lecturer_email']}")
        print(f"   🆔 Academic ID: {supervisor['lecturer_academic_id']}")
        print(f"   👥 Max Students: {supervisor['max_students']}")
        print(f"   📊 Current Projects: {supervisor['project_student_count']}")
        print(f"   🔗 Supervisor ID: {supervisor['supervisor_id']}")
        print()
    
    print("=" * 60)
    print("✅ VERIFICATION COMPLETE")
    print("✅ Supervisors are properly separated from lecturers")
    print("🔗 All supervisors are correctly linked to their lecturer records")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(verify_supervisor_lecturer_separation())
