from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException


class AcademicYearController:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db["academic_years"]

    async def get_all_academic_years(self, limit: int = 10, cursor: str | None = None):
        query = {"deleted": {"$ne": True}}
        if cursor:
            query["_id"] = {"$gt": ObjectId(cursor)}

        academic_years = await self.collection.find(query).limit(limit).to_list(limit)

        next_cursor = None
        if len(academic_years) == limit:
            next_cursor = str(academic_years[-1]["_id"])

        return {
            "items": academic_years,
            "next_cursor": next_cursor
        }

    async def get_academic_year_by_id(self, academic_year_id: str):
        academic_year = await self.collection.find_one({
            "_id": ObjectId(academic_year_id),
            "deleted": {"$ne": True}
        })
        if not academic_year:
            raise HTTPException(status_code=404, detail="Academic year not found")
        return academic_year

    async def create_academic_year(self, academic_year_data: dict):
        academic_year_data["createdAt"] = datetime.now()
        academic_year_data["updatedAt"] = datetime.now()

        # Check if title already exists
        existing = await self.collection.find_one({
            "title": academic_year_data["title"],
            "deleted": {"$ne": True}
        })
        if existing:
            raise HTTPException(status_code=400, detail="Academic year title already exists")

        result = await self.collection.insert_one(academic_year_data)
        created_academic_year = await self.collection.find_one({"_id": result.inserted_id})
        return created_academic_year

    async def update_academic_year(self, academic_year_id: str, update_data: dict):
        update_data = {k: v for k, v in update_data.items() if v is not None}

        if not update_data:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        update_data["updatedAt"] = datetime.now()

        result = await self.collection.update_one(
            {"_id": ObjectId(academic_year_id), "deleted": {"$ne": True}},
            {"$set": update_data}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Academic year not found")

        updated_academic_year = await self.collection.find_one({"_id": ObjectId(academic_year_id)})
        return updated_academic_year

    async def delete_academic_year(self, academic_year_id: str):
        result = await self.collection.update_one(
            {"_id": ObjectId(academic_year_id)},
            {"$set": {"deleted": True, "updatedAt": datetime.now()}}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Academic year not found")

        return {"message": "Academic year deleted successfully"}

    async def get_active_academic_years(self):
        academic_years = await self.collection.find({
            "status": "ACTIVE",
            "deleted": {"$ne": True}
        }).to_list(None)
        return academic_years