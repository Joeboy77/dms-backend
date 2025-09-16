from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException


class FypCheckinController:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db["fypcheckins"]

    async def get_all_checkins(self, limit: int = 10, cursor: str | None = None):
        query = {}
        if cursor:
            query["_id"] = {"$gt": ObjectId(cursor)}

        checkins = await self.collection.find(query).limit(limit).to_list(limit)

        next_cursor = None
        if len(checkins) == limit:
            next_cursor = str(checkins[-1]["_id"])

        return {
            "items": checkins,
            "next_cursor": next_cursor
        }

    async def get_checkin_by_id(self, checkin_id: str):
        checkin = await self.collection.find_one({"_id": ObjectId(checkin_id)})
        if not checkin:
            raise HTTPException(status_code=404, detail="Checkin not found")
        return checkin

    async def create_checkin(self, checkin_data: dict):
        checkin_data["createdAt"] = datetime.now()
        checkin_data["updatedAt"] = datetime.now()

        result = await self.collection.insert_one(checkin_data)
        created_checkin = await self.collection.find_one({"_id": result.inserted_id})
        return created_checkin

    async def update_checkin(self, checkin_id: str, update_data: dict):
        update_data = {k: v for k, v in update_data.items() if v is not None}

        if not update_data:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        update_data["updatedAt"] = datetime.now()

        result = await self.collection.update_one(
            {"_id": ObjectId(checkin_id)},
            {"$set": update_data}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Checkin not found")

        updated_checkin = await self.collection.find_one({"_id": ObjectId(checkin_id)})
        return updated_checkin

    async def delete_checkin(self, checkin_id: str):
        result = await self.collection.delete_one({"_id": ObjectId(checkin_id)})

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Checkin not found")

        return {"message": "Checkin deleted successfully"}

    async def get_checkins_by_academic_year(self, academic_year_id: str):
        checkins = await self.collection.find({"academicYear": ObjectId(academic_year_id)}).to_list(None)
        return checkins

    async def get_active_checkins(self):
        checkins = await self.collection.find({"active": True}).to_list(None)
        return checkins