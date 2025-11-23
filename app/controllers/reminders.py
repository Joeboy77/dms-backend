from datetime import datetime
from typing import Optional, List, Dict
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException


class ReminderController:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db["reminders"]

    async def get_all_reminders(self, limit: int = 10, cursor: Optional[str] = None):
        query = {}
        if cursor:
            query["_id"] = {"$gt": ObjectId(cursor)}

        reminders = await self.collection.find(query).sort("date_time", 1).limit(limit).to_list(limit)

        next_cursor = None
        if len(reminders) == limit:
            next_cursor = str(reminders[-1]["_id"])

        return {
            "items": reminders,
            "next_cursor": next_cursor
        }

    async def get_reminder_by_id(self, reminder_id: str):
        reminder = await self.collection.find_one({"_id": ObjectId(reminder_id)})
        if not reminder:
            raise HTTPException(status_code=404, detail="Reminder not found")
        return reminder

    async def create_reminder(self, reminder_data: dict):
        reminder_data["createdAt"] = datetime.now()
        reminder_data["updatedAt"] = None

        result = await self.collection.insert_one(reminder_data)
        created_reminder = await self.collection.find_one({"_id": result.inserted_id})
        return created_reminder

    async def update_reminder(self, reminder_id: str, update_data: dict):
        update_data = {k: v for k, v in update_data.items() if v is not None}

        if not update_data:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        update_data["updatedAt"] = datetime.now()

        result = await self.collection.update_one(
            {"_id": ObjectId(reminder_id)},
            {"$set": update_data}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Reminder not found")

        updated_reminder = await self.collection.find_one({"_id": ObjectId(reminder_id)})
        return updated_reminder

    async def delete_reminder(self, reminder_id: str):
        result = await self.collection.delete_one({"_id": ObjectId(reminder_id)})

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Reminder not found")

        return {"message": "Reminder deleted successfully"}

    async def get_upcoming_reminders(self, limit: int = 10):
        current_time = datetime.now()
        reminders = await self.collection.find(
            {"date_time": {"$gte": current_time}}
        ).sort("date_time", 1).limit(limit).to_list(limit)
        return reminders

    async def get_past_reminders(self, limit: int = 10):
        current_time = datetime.now()
        reminders = await self.collection.find(
            {"date_time": {"$lt": current_time}}
        ).sort("date_time", -1).limit(limit).to_list(limit)
        return reminders