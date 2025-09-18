#!/usr/bin/env python3
"""
Quick test script for supervisor assignment functionality.
"""

import asyncio
from supervisor_assignment import SupervisorAssignmentManager

async def test_assignment():
    """Test supervisor assignment."""
    manager = SupervisorAssignmentManager()
    await manager.connect()
    
    try:
        print("🔍 Testing Supervisor Assignment System")
        print("=" * 50)
        
        # Get available supervisors
        print("\n📋 Available Supervisors:")
        supervisors = await manager.get_available_supervisors()
        for i, supervisor in enumerate(supervisors[:3], 1):
            print(f"{i}. {supervisor['lecturer_name']} (ID: {supervisor['_id']}) - {supervisor['available_slots']} slots")
        
        # Get unassigned students
        print("\n🎓 Unassigned Students:")
        students = await manager.get_unassigned_students(limit=3)
        for i, student in enumerate(students[:3], 1):
            print(f"{i}. {student['student_name']} (ID: {student['_id']})")
        
        if supervisors and students:
            # Test assignment
            student_id = str(students[0]['_id'])
            supervisor_id = str(supervisors[0]['_id'])
            
            print(f"\n🔄 Testing assignment:")
            print(f"Student: {students[0]['student_name']} → Supervisor: {supervisors[0]['lecturer_name']}")
            
            result = await manager.assign_supervisor_to_student(student_id, supervisor_id)
            
            if result["success"]:
                print(f"✅ {result['message']}")
                
                # Verify assignment
                assignments = await manager.get_student_assignments(limit=1)
                if assignments:
                    latest = assignments[0]
                    print(f"📝 Verified: {latest['student_name']} → {latest['supervisor_name']}")
            else:
                print(f"❌ {result['error']}")
        
        print("\n✨ Test completed!")
        
    finally:
        await manager.disconnect()

if __name__ == "__main__":
    asyncio.run(test_assignment())
