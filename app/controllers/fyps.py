from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException


class FypController:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db["fyps"]
        self.project_areas_collection = db["project_areas"]

    async def get_all_fyps(self, limit: int = 10, cursor: str | None = None):
        query = {}
        if cursor:
            query["_id"] = {"$gt": ObjectId(cursor)}

        fyps = await self.collection.find(query).limit(limit).to_list(limit)

        next_cursor = None
        if len(fyps) == limit:
            next_cursor = str(fyps[-1]["_id"])

        return {
            "items": fyps,
            "next_cursor": next_cursor
        }

    async def get_fyp_by_id(self, fyp_id: str):
        fyp = await self.collection.find_one({"_id": ObjectId(fyp_id)})
        if not fyp:
            raise HTTPException(status_code=404, detail="FYP not found")
        return fyp

    async def create_fyp(self, fyp_data: dict):
        fyp_data["createdAt"] = datetime.now()
        fyp_data["updatedAt"] = datetime.now()

        # Check if student already has an FYP
        existing_fyp = await self.collection.find_one({"student": fyp_data["student"]})
        if existing_fyp:
            raise HTTPException(status_code=400, detail="Student already has an FYP assigned")

        result = await self.collection.insert_one(fyp_data)
        created_fyp = await self.collection.find_one({"_id": result.inserted_id})
        return created_fyp

    async def update_fyp(self, fyp_id: str, update_data: dict):
        update_data = {k: v for k, v in update_data.items() if v is not None}

        if not update_data:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        update_data["updatedAt"] = datetime.now()

        result = await self.collection.update_one(
            {"_id": ObjectId(fyp_id)},
            {"$set": update_data}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="FYP not found")

        updated_fyp = await self.collection.find_one({"_id": ObjectId(fyp_id)})
        return updated_fyp

    async def delete_fyp(self, fyp_id: str):
        result = await self.collection.delete_one({"_id": ObjectId(fyp_id)})

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="FYP not found")

        return {"message": "FYP deleted successfully"}

    async def get_fyps_by_student(self, student_id: str):
        # Accept either academicId (e.g., CS2025001) or a Mongo ObjectId string
        student = await self.db["students"].find_one({"academicId": student_id})
        if not student and ObjectId.is_valid(student_id):
            student = await self.db["students"].find_one({"_id": ObjectId(student_id)})
        if not student:
            raise HTTPException(status_code=404, detail=f"Student {student_id} not found")

        # There should be at most one FYP per student; pick most recent if multiple
        # Handle both storage forms: ObjectId and stringified ObjectId
        student_oid = student["_id"]
        fyp = await self.collection.find_one(
            {
                "$or": [
                    {"student": student_oid},
                    {"student": str(student_oid)}
                ]
            },
            sort=[("createdAt", -1)]
        )
        if not fyp:
            raise HTTPException(status_code=404, detail=f"No FYP found for student {student_id}")

        # Populate single projectArea document in place of ObjectId
        project_area_id = fyp.get("projectArea")
        if project_area_id:
            if isinstance(project_area_id, str) and ObjectId.is_valid(project_area_id):
                project_area_id = ObjectId(project_area_id)
            project_area_doc = await self.project_areas_collection.find_one({"_id": project_area_id})
            if project_area_doc:
                fyp["projectArea"] = project_area_doc

        return fyp

    async def get_fyps_by_supervisor(self, supervisor_id: str):
        fyps = await self.collection.find({"supervisor": ObjectId(supervisor_id)}).to_list(None)
        return fyps

    async def get_fyps_by_project_area(self, project_area_id: str):
        fyps = await self.collection.find({"projectArea": ObjectId(project_area_id)}).to_list(None)
        return fyps

    async def get_fyps_by_checkin(self, checkin_id: str):
        fyps = await self.collection.find({"checkin": ObjectId(checkin_id)}).to_list(None)
        return fyps