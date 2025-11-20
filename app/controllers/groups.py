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


    async def assign_groups_to_supervisor(self, group_ids: list[str], supervisor_id: str):
    # Verify supervisor
        supervisor = await self.db["supervisors"].find_one({"_id": ObjectId(supervisor_id)})
        if not supervisor:
            raise HTTPException(status_code=404, detail="Supervisor not found")

        # Fetch lecturer linked to supervisor
        lecturer = await self.db["lecturers"].find_one({"_id": ObjectId(supervisor["lecturer_id"])})
        if not lecturer:
            raise HTTPException(status_code=404, detail="Lecturer for supervisor not found")

        successful = []
        errors = []

        for group_id in group_ids:
            try:
                # Verify group exists
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