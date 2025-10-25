from datetime import datetime

from bson import ObjectId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase


class ActivityLogController:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db["activity_logs"]

    async def get_all_logs(self, limit: int = 10, cursor: str | None = None):
        query = {}
        if cursor:
            query["_id"] = {"$gt": ObjectId(cursor)}

        logs = await self.collection.find(query).sort("_id", -1).limit(limit).to_list(limit)

        # Transform logs to match expected frontend format
        transformed_logs = []
        for log in logs:
            # Create a details object that matches the expected schema
            details = {
                "status": 200,
                "message": log.get("description", ""),
                "requestType": log.get("action", "activity")
            }
            
            transformed_log = {
                "_id": str(log["_id"]),
                "action": log.get("action", "activity"),
                "details": details,
                "createdAt": log.get("createdAt", log.get("timestamp")),
                "updatedAt": log.get("updatedAt")
            }
            transformed_logs.append(transformed_log)

        next_cursor = None
        has_more = False
        if len(logs) == limit:
            next_cursor = str(logs[-1]["_id"])
            has_more = True

        return {
            "items": transformed_logs, 
            "next_cursor": next_cursor,
            "has_more": has_more
        }
