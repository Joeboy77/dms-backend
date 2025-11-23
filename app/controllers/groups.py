from datetime import datetime
from typing import Optional, List, Dict
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException


class GroupController:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db["groups"]

    async def get_all_groups(self, limit: int = 10, cursor: Optional[str] = None):
        query = {}
        if cursor:
            query["_id"] = {"$gt": ObjectId(cursor)}

        groups = await self.collection.find(query).limit(limit).to_list(limit)
        

        # Add student count for each group
        for group in groups:
            group["student_count"] = len(group.get("students", []))
        next_cursor = None
        if len(groups) == limit:
            next_cursor = str(groups[-1]["_id"])

        return {
            "items": groups,
            "next_cursor": next_cursor
        }

    async def get_group_by_id(self, group_id: str):
        group = await self.collection.find_one({"_id": ObjectId(group_id)})
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")

        group["student_count"] = len(group.get("student_ids", []))
        return group

    async def create_group(self, group_data: dict):
        # Convert students to ObjectIds if they're strings
        if "students" in group_data:
            group_data["students"] = [
                ObjectId(sid) if isinstance(sid, str) else sid
                for sid in group_data["students"]
            ]

        group_data["createdAt"] = datetime.now()
        group_data["updatedAt"] = datetime.now()

        result = await self.collection.insert_one(group_data)
        created_group = await self.collection.find_one({"_id": result.inserted_id})
        created_group["student_count"] = len(created_group.get("students", []))
        return created_group

    async def update_group(self, group_id: str, update_data: dict):
        update_data = {k: v for k, v in update_data.items() if v is not None}

        if not update_data:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        update_data["updatedAt"] = datetime.now()

        result = await self.collection.update_one(
            {"_id": ObjectId(group_id)},
            {"$set": update_data}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Group not found")

        updated_group = await self.collection.find_one({"_id": ObjectId(group_id)})
        updated_group["student_count"] = len(updated_group.get("students", []))
        return updated_group

    async def delete_group(self, group_id: str):
        result = await self.collection.delete_one({"_id": ObjectId(group_id)})

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Group not found")

        return {"message": "Group deleted successfully"}

    async def add_student_to_group(self, group_id: str, student_id: str):
        # Check if student exists
        student = await self.db["students"].find_one({"academicId": student_id})
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

        # Check if student is already in the group
        group = await self.collection.find_one({"_id": ObjectId(group_id)})
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")

        students = group.get("students", [])
        if ObjectId(student["_id"]) in students:
            raise HTTPException(status_code=400, detail="Student is already in the group")

        # Add student to group
        result = await self.collection.update_one(
            {"_id": ObjectId(group_id)},
            {
                "$push": {"students": ObjectId(student["_id"])},
                "$set": {"updatedAt": datetime.now()}
            }
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Group not found")

        updated_group = await self.collection.find_one({"_id": ObjectId(group_id)})
        updated_group["student_count"] = len(updated_group.get("students", []))
        return updated_group

    async def remove_student_from_group(self, group_id: str, student_id: str):
        result = await self.collection.update_one(
            {"_id": ObjectId(group_id)},
            {
                "$pull": {"students": ObjectId(student_id)},
                "$set": {"updatedAt": datetime.now()}
            }
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Group not found")

        updated_group = await self.collection.find_one({"_id": ObjectId(group_id)})
        updated_group["student_count"] = len(updated_group.get("students", []))
        return updated_group

    async def get_group_with_students(self, group_id: str):
        group = await self.get_group_by_id(group_id)

        students = []
        for student_id in group.get("students", []):
            student = await self.db["students"].find_one({"_id": student_id})
            if student:
                student_name = f"{student.get('surname', '')} {student.get('otherNames', '')}".strip()
                students.append({
                    "student_id": str(student["_id"]),
                    "student_academicId": student.get("academicId", ""),
                    "student_name": student_name,
                    "student_email": student.get("email", ""),
                    "student_image": student.get("image", ""),
                    "student_programme": student.get("program", "")
                })
        group["student_count"] = len(students)

        return {
            "group": group,
            "students": students
        }

    async def get_group_details_with_submissions(self, group_id: str):
        group = await self.get_group_by_id(group_id)
        
        students = []
        for student_id in group.get("students", []):
            student = await self.db["students"].find_one({"_id": student_id})
            if student:
                student_name = f"{student.get('surname', '')} {student.get('otherNames', '')}".strip()
                
                program_name = "Unknown Program"
                program_field = student.get("program", "")
                if program_field:
                    if isinstance(program_field, str) and len(program_field) == 24 and ObjectId.is_valid(program_field):
                        program = await self.db["programs"].find_one({"_id": ObjectId(program_field)})
                        program_name = program.get("title", program.get("name", "Unknown Program")) if program else "Unknown Program"
                    else:
                        program_name = program_field
                
                students.append({
                    "id": str(student["_id"]),
                    "academic_id": student.get("academicId", ""),
                    "name": student_name,
                    "program": program_name,
                    "image": student.get("image", ""),
                    "email": student.get("email", "")
                })
        
        submissions_data = []
        
        if group.get("supervisor"):
            deliverables = await self.db["deliverables"].find({
                "supervisor_id": group["supervisor"]
            }).sort("created_at", 1).to_list(length=None)
            
            for deliverable in deliverables:
                deliverable_id = deliverable["_id"]
                
                submission = await self.db["submissions"].find_one({
                    "group_id": ObjectId(group_id),
                    "deliverable_id": deliverable_id
                })
                
                files = []
                if submission:
                    files = await self.db["submission_files"].find({
                        "submission_id": submission["_id"]
                    }).to_list(length=None)
                
                submissions_data.append({
                    "deliverable_id": str(deliverable_id),
                    "deliverable_name": deliverable.get("name", deliverable.get("title", "")),
                    "status": submission.get("status", "not_started") if submission else "not_started",
                    "submitted_at": submission.get("createdAt") if submission else None,
                    "files": [
                        {
                            "id": str(file["_id"]),
                            "file_name": file.get("file_name", ""),
                            "file_path": file.get("file_path", ""),
                            "file_type": file.get("file_type", ""),
                            "file_size": file.get("file_size", 0),
                            "uploaded_at": file.get("createdAt")
                        }
                        for file in files
                    ]
                })
        
        return {
            "group": {
                "id": str(group["_id"]),
                "name": group.get("name", ""),
                "project_topic": group.get("project_topic", ""),
                "created_at": group.get("createdAt"),
                "member_count": len(students),
                "members": students
            },
            "submissions": submissions_data
        }


    async def assign_groups_to_supervisor(self, group_ids: List[str], supervisor_id: str):
        supervisor = await self.db["supervisors"].find_one({"_id": ObjectId(supervisor_id)})
        if not supervisor:
            raise HTTPException(status_code=404, detail="Supervisor not found")

        lecturer = await self.db["lecturers"].find_one({"_id": ObjectId(supervisor["lecturer_id"])})
        if not lecturer:
            raise HTTPException(status_code=404, detail="Lecturer for supervisor not found")

        successful = []
        errors = []

        for group_id in group_ids:
            try:
                group = await self.collection.find_one({"_id": ObjectId(group_id)})
                if not group:
                    errors.append(f"Group with ID {group_id} not found")
                    continue

                # Check if already assigned
                if "supervisor" in group and group["supervisor"]:
                    errors.append(f"Group {group['name']} already has a supervisor assigned")
                    continue

                # Assign supervisor directly to group
                await self.collection.update_one(
                    {"_id": group["_id"]},
                    {"$set": {"supervisor": supervisor_id}}
                )

                successful.append({
                    "group_id": group_id,
                    "group_name": group["name"],
                    "assigned_supervisor": supervisor_id
                })

            except Exception as e:
                errors.append(f"Error assigning group {group_id}: {str(e)}")

        # Log activity (Optional but recommended)
        if successful:
            try:
                await self.db["activity_logs"].insert_one({
                    "description": f"Assigned {len(successful)} group(s) to Supervisor {lecturer.get('surname', '')} {lecturer.get('otherNames', '')}.",
                    "action": "group_assignment",
                    "user_id": str(supervisor["_id"]),
                    "timestamp": datetime.utcnow(),
                    "details": {
                        "groups_assigned": successful
                    }
                })
            except Exception as log_error:
                print("Logging failed:", log_error)

        return {
            "message": "Group assignment completed",
            "successful_assignments": successful,
            "failed_assignments": errors
        }
        
    async def unassign_groups_from_supervisor(self, supervisor_id: str):
        result = await self.collection.update_many(
            {"supervisor": supervisor_id},
            {"$set": {"supervisor": None}}
        )

        return {
            "message": f"Unassigned {result.modified_count} groups from supervisor {supervisor_id}"
        }

    async def get_groups_by_student(self, student_id: str):
        student = await self.db["students"].find_one({"academicId": student_id})
        if not student and ObjectId.is_valid(student_id):
            student = await self.db["students"].find_one({"_id": ObjectId(student_id)})
        if not student:
            return []

        student_oid = student["_id"]
        
        groups = await self.collection.find({
            "students": {"$in": [student_oid, ObjectId(student_oid)]}
        }).to_list(None)
        
        formatted_groups = []
        for group in groups:
            group["student_count"] = len(group.get("students", []))
            group["id"] = str(group["_id"])
            formatted_groups.append(group)
        
        return formatted_groups