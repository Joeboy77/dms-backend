from bson import ObjectId
from fastapi import HTTPException

class ActivityLogController:
    def __init__(self, db):
        self.db = db
        self.collection = db["activity_logs"]

    async def get_logs(self, token, limit: int = 10, cursor: str | None = None, role: str | None = None):
        query = {}

        # Pagination cursor
        if cursor:
            query["_id"] = {"$gt": ObjectId(cursor)}

        # Admin can view all logs, optionally filtered by 'type'
        if token.role.lower() == "admin":
            if role:
                query["type"] = role.lower()
        else:
            # Non-admin users can only view their own logs
            query["user_id"] = token.id

        logs = await self.collection.find(query).sort("_id", 1).limit(limit).to_list(limit)

        next_cursor = str(logs[-1]["_id"]) if len(logs) == limit else None

        return {"items": logs, "next_cursor": next_cursor}
