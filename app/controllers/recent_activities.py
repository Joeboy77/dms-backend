from datetime import datetime
from typing import Optional, List, Dict
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException


class RecentActivityController:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db["recent_activities"]

    async def get_all_activities(self, limit: int = 10, cursor: Optional[str] = None):
        query = {}
        if cursor:
            query["_id"] = {"$gt": ObjectId(cursor)}

        activities = await self.collection.find(query).sort("timestamp", -1).limit(limit).to_list(limit)

        next_cursor = None
        if len(activities) == limit:
            next_cursor = str(activities[-1]["_id"])

        return {
            "items": activities,
            "next_cursor": next_cursor
        }

    async def get_activity_by_id(self, activity_id: str):
        activity = await self.collection.find_one({"_id": ObjectId(activity_id)})
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")
        return activity

    async def create_activity(self, activity_data: dict):
        activity_data["createdAt"] = datetime.now()
        activity_data["updatedAt"] = None

        result = await self.collection.insert_one(activity_data)
        created_activity = await self.collection.find_one({"_id": result.inserted_id})
        return created_activity

    async def update_activity(self, activity_id: str, update_data: dict):
        update_data = {k: v for k, v in update_data.items() if v is not None}

        if not update_data:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        update_data["updatedAt"] = datetime.now()

        result = await self.collection.update_one(
            {"_id": ObjectId(activity_id)},
            {"$set": update_data}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Activity not found")

        updated_activity = await self.collection.find_one({"_id": ObjectId(activity_id)})
        return updated_activity

    async def delete_activity(self, activity_id: str):
        result = await self.collection.delete_one({"_id": ObjectId(activity_id)})

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Activity not found")

        return {"message": "Activity deleted successfully"}

    async def get_activities_by_user(self, user_id: str):
        activities = await self.collection.find({"user_id": ObjectId(user_id)}).sort("timestamp", -1).to_list(None)
        return activities

    async def get_recent_activities(self, limit: int = 20):
        activities = await self.collection.find({}).sort("timestamp", -1).limit(limit).to_list(limit)
        return activities

    async def seed_sample_data(self):
        sample_activities = [
            {
                "timestamp": datetime(2024, 9, 15, 14, 30),
                "user_id": ObjectId(),
                "user_name": "David Mainoo",
                "description": "Submitted final year project proposal for review"
            },
            {
                "timestamp": datetime(2024, 9, 15, 13, 45),
                "user_id": ObjectId(),
                "user_name": "Sarah Johnson",
                "description": "Uploaded chapter 3 of dissertation"
            },
            {
                "timestamp": datetime(2024, 9, 15, 12, 20),
                "user_id": ObjectId(),
                "user_name": "Michael Chen",
                "description": "Completed coursework submission for Data Structures"
            },
            {
                "timestamp": datetime(2024, 9, 15, 11, 15),
                "user_id": ObjectId(),
                "user_name": "Emily Watson",
                "description": "Registered for Advanced Machine Learning course"
            },
            {
                "timestamp": datetime(2024, 9, 15, 10, 30),
                "user_id": ObjectId(),
                "user_name": "James Wilson",
                "description": "Submitted research paper to IEEE conference"
            },
            {
                "timestamp": datetime(2024, 9, 15, 9, 45),
                "user_id": ObjectId(),
                "user_name": "Lisa Brown",
                "description": "Completed peer review for Software Engineering project"
            },
            {
                "timestamp": datetime(2024, 9, 14, 16, 20),
                "user_id": ObjectId(),
                "user_name": "Robert Davis",
                "description": "Defended final year project successfully"
            },
            {
                "timestamp": datetime(2024, 9, 14, 15, 10),
                "user_id": ObjectId(),
                "user_name": "Amanda Miller",
                "description": "Updated project timeline for mobile app development"
            },
            {
                "timestamp": datetime(2024, 9, 14, 14, 35),
                "user_id": ObjectId(),
                "user_name": "Kevin Taylor",
                "description": "Submitted lab report for Computer Networks"
            },
            {
                "timestamp": datetime(2024, 9, 14, 13, 50),
                "user_id": ObjectId(),
                "user_name": "Jennifer Lee",
                "description": "Completed group project presentation for Database Systems"
            }
        ]

        for activity in sample_activities:
            activity["createdAt"] = datetime.now()
            activity["updatedAt"] = None

        result = await self.collection.insert_many(sample_activities)
        return {"message": f"Seeded {len(result.inserted_ids)} sample activities"}