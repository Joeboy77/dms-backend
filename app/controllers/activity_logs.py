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

        logs = await self.collection.find(query).limit(limit).to_list(limit)

        next_cursor = None
        if len(logs) == limit:
            next_cursor = str(logs[-1]["_id"])

        return {"items": logs, "next_cursor": next_cursor}
