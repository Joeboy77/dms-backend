from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException


class GroupController:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db["groups"]

    async def get_all_groups(self, limit: int = 10, cursor: str | None = None):
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

    async def get_groups_by_student(self, student_id: str):
        
        student = await self.db["students"].find({"academicId": student_id}).to_list(None)
        groups = await self.collection.find(
            {"students": student[0]["_id"]}
        ).to_list(None)

        for group in groups:
            group["student_count"] = len(group.get("students", []))
        return groups
    
    
    async def assign_groups_to_supervisor(self, group_ids: list[str], academic_year_id: str, supervisor_id: str):
        # Get the checkin record
        checkin = await self.db["fypcheckins"].find_one({"academicYear": academic_year_id})
        if not checkin:
            raise HTTPException(status_code=404, detail="FYP checkin not found for the academic year")

        checkin_id = checkin["_id"]

        # Fetch supervisor and linked lecturer
        supervisor = await self.db["supervisors"].find_one({"_id": ObjectId(supervisor_id)})
        if not supervisor:
            raise HTTPException(status_code=404, detail="Supervisor not found")

        lecturer = await self.db["lecturers"].find_one({"_id": ObjectId(supervisor["lecturer_id"])})
        if not lecturer:
            raise HTTPException(status_code=404, detail="Lecturer for supervisor not found")
        
        project_area = await self.db["lecturer_project_areas"].find_one({"lecturer": lecturer["_id"]})
        if not project_area:
            raise HTTPException(status_code=404, detail="Project area for lecturer not found")

        created_assignments = []
        assignment_errors = []

        # Assign students
        for group_id in group_ids:
            try:
                # Verify group exists
                group = await self.collection.find_one({"_id": ObjectId(group_id)})
                if not group:
                    assignment_errors.append(f"{group['name']} not found")
                    continue
                

                # Check if already assigned
                existing_fyp = await self.db["fyps"].find_one({
                    "group": group["_id"],
                    "checkin": checkin_id
                })
                if existing_fyp:
                    assignment_errors.append(f"Group {group['name']} already assigned to a supervisor for this academic year")
                    continue
                
                # Update the group's supervisor field
                await self.collection.update_one(
                    {"_id": group["_id"]},
                    {"$set": {"supervisor": supervisor_id}}
                )


                # Create assignment
                fyp_data = {
                    "group": group["_id"],
                    "checkin": checkin_id,
                    "supervisor": ObjectId(supervisor_id),
                    "projectArea": project_area["projectAreas"],
                    "createdAt": datetime.utcnow(),
                    "updatedAt": datetime.utcnow()
                }

                result = await self.db["fyps"].insert_one(fyp_data)
                created_fyp = await self.db["fyps"].find_one({"_id": result.inserted_id})

                created_assignments.append({
                    "fyp_id": str(created_fyp["_id"]),
                    "group_id": str(created_fyp["group"]),
                    "supervisor_id": str(created_fyp["supervisor"]),
                    "checkin_id": str(created_fyp["checkin"]),
                    "project_area_id": str(created_fyp["projectArea"]) if created_fyp["projectArea"] else None,
                    "created_at": created_fyp["createdAt"],
                    "updated_at": created_fyp["updatedAt"]
                })

            except Exception as e:
                assignment_errors.append(f"Error assigning group {group_id}: {str(e)}")

        # Log activity after all assignments
        if created_assignments:
            try:
                await self.db["activity_logs"].insert_one({
                    "description": f"Assigned {len(created_assignments)} student(s) to Supervisor {lecturer.get('title', '')} {lecturer.get('surname', '')} {lecturer.get('otherNames', '')}.",
                    "action": "student_assignment",
                    "user_name": lecturer.get("academicId"),
                    "user_id": str(supervisor["_id"]),
                    "type": "assignment",
                    "timestamp": datetime.utcnow(),
                    "createdAt": datetime.utcnow(),
                    "updatedAt": datetime.utcnow(),
                    "details": {
                        "student_count": len(created_assignments),
                        "supervisor_name": f"{lecturer.get('title', '')} {lecturer.get('surname', '')} {lecturer.get('otherNames', '')}".strip(),
                        "project_area": None,
                        "assigned_groups": group_ids
                    }
                })
            except Exception as log_error:
                print("Failed to log activity:", log_error)

        # Return response
        return {
            "message": "Assignment process completed",
            "successful_assignments": len(created_assignments),
            "failed_assignments": len(assignment_errors),
            "created_assignments": created_assignments,
            "errors": assignment_errors
        }