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
            group["student_count"] = len(group.get("student_ids", []))

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
        # Convert student_ids to ObjectIds if they're strings
        if "student_ids" in group_data:
            group_data["student_ids"] = [
                ObjectId(sid) if isinstance(sid, str) else sid
                for sid in group_data["student_ids"]
            ]

        group_data["createdAt"] = datetime.now()
        group_data["updatedAt"] = datetime.now()

        result = await self.collection.insert_one(group_data)
        created_group = await self.collection.find_one({"_id": result.inserted_id})
        created_group["student_count"] = len(created_group.get("student_ids", []))
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
        updated_group["student_count"] = len(updated_group.get("student_ids", []))
        return updated_group

    async def delete_group(self, group_id: str):
        result = await self.collection.delete_one({"_id": ObjectId(group_id)})

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Group not found")

        return {"message": "Group deleted successfully"}

    async def add_student_to_group(self, group_id: str, student_id: str):
        # Check if student exists
        student = await self.db["students"].find_one({"_id": ObjectId(student_id)})
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

        # Check if student is already in the group
        group = await self.collection.find_one({"_id": ObjectId(group_id)})
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")

        student_ids = group.get("student_ids", [])
        if ObjectId(student_id) in student_ids:
            raise HTTPException(status_code=400, detail="Student is already in the group")

        # Add student to group
        result = await self.collection.update_one(
            {"_id": ObjectId(group_id)},
            {
                "$push": {"student_ids": ObjectId(student_id)},
                "$set": {"updatedAt": datetime.now()}
            }
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Group not found")

        updated_group = await self.collection.find_one({"_id": ObjectId(group_id)})
        updated_group["student_count"] = len(updated_group.get("student_ids", []))
        return updated_group

    async def remove_student_from_group(self, group_id: str, student_id: str):
        result = await self.collection.update_one(
            {"_id": ObjectId(group_id)},
            {
                "$pull": {"student_ids": ObjectId(student_id)},
                "$set": {"updatedAt": datetime.now()}
            }
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Group not found")

        updated_group = await self.collection.find_one({"_id": ObjectId(group_id)})
        updated_group["student_count"] = len(updated_group.get("student_ids", []))
        return updated_group

    async def get_group_with_students(self, group_id: str):
        group = await self.get_group_by_id(group_id)

        students = []
        for student_id in group.get("student_ids", []):
            student = await self.db["students"].find_one({"_id": student_id})
            if student:
                student_name = f"{student.get('surname', '')} {student.get('otherNames', '')}".strip()
                students.append({
                    "student_id": str(student["_id"]),
                    "student_name": student_name,
                    "student_email": student.get("email", ""),
                    "student_image": student.get("image", "")
                })

        return {
            "group": group,
            "students": students
        }

    async def get_groups_by_student(self, student_id: str):
        groups = await self.collection.find(
            {"student_ids": ObjectId(student_id)}
        ).to_list(None)

        for group in groups:
            group["student_count"] = len(group.get("student_ids", []))

        return groups