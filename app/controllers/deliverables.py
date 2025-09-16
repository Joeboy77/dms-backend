from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException


class DeliverableController:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db["deliverables"]

    async def get_all_deliverables(self, limit: int = 10, cursor: str | None = None):
        query = {}
        if cursor:
            query["_id"] = {"$gt": ObjectId(cursor)}

        deliverables = await self.collection.find(query).sort("start_date", -1).limit(limit).to_list(limit)

        # Calculate total submissions for each deliverable
        for deliverable in deliverables:
            submissions_count = await self.db["submissions"].count_documents(
                {"deliverable_id": deliverable["_id"]}
            )
            deliverable["total_submissions"] = submissions_count

        next_cursor = None
        if len(deliverables) == limit:
            next_cursor = str(deliverables[-1]["_id"])

        return {
            "items": deliverables,
            "next_cursor": next_cursor
        }

    async def get_deliverable_by_id(self, deliverable_id: str):
        deliverable = await self.collection.find_one({"_id": ObjectId(deliverable_id)})
        if not deliverable:
            raise HTTPException(status_code=404, detail="Deliverable not found")

        # Calculate total submissions
        submissions_count = await self.db["submissions"].count_documents(
            {"deliverable_id": ObjectId(deliverable_id)}
        )
        deliverable["total_submissions"] = submissions_count

        return deliverable

    async def create_deliverable(self, deliverable_data: dict):
        # Convert supervisor_id to ObjectId if it's a string
        if "supervisor_id" in deliverable_data and isinstance(deliverable_data["supervisor_id"], str):
            deliverable_data["supervisor_id"] = ObjectId(deliverable_data["supervisor_id"])

        deliverable_data["createdAt"] = datetime.now()
        deliverable_data["updatedAt"] = datetime.now()
        deliverable_data["total_submissions"] = 0

        result = await self.collection.insert_one(deliverable_data)
        created_deliverable = await self.collection.find_one({"_id": result.inserted_id})
        created_deliverable["total_submissions"] = 0
        return created_deliverable

    async def update_deliverable(self, deliverable_id: str, update_data: dict):
        update_data = {k: v for k, v in update_data.items() if v is not None}

        if not update_data:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        update_data["updatedAt"] = datetime.now()

        result = await self.collection.update_one(
            {"_id": ObjectId(deliverable_id)},
            {"$set": update_data}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Deliverable not found")

        updated_deliverable = await self.collection.find_one({"_id": ObjectId(deliverable_id)})

        # Calculate total submissions
        submissions_count = await self.db["submissions"].count_documents(
            {"deliverable_id": ObjectId(deliverable_id)}
        )
        updated_deliverable["total_submissions"] = submissions_count

        return updated_deliverable

    async def delete_deliverable(self, deliverable_id: str):
        result = await self.collection.delete_one({"_id": ObjectId(deliverable_id)})

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Deliverable not found")

        return {"message": "Deliverable deleted successfully"}

    async def get_deliverables_by_supervisor(self, supervisor_id: str):
        # Try both ObjectId and string formats
        deliverables = await self.collection.find({
            "$or": [
                {"supervisor_id": ObjectId(supervisor_id)},
                {"supervisor_id": supervisor_id}
            ]
        }).sort("start_date", -1).to_list(None)

        # Calculate total submissions for each deliverable
        for deliverable in deliverables:
            submissions_count = await self.db["submissions"].count_documents(
                {"deliverable_id": deliverable["_id"]}
            )
            deliverable["total_submissions"] = submissions_count

        return deliverables

    async def get_active_deliverables(self):
        current_time = datetime.now()
        deliverables = await self.collection.find({
            "start_date": {"$lte": current_time},
            "end_date": {"$gte": current_time}
        }).sort("end_date", 1).to_list(None)

        # Calculate total submissions for each deliverable
        for deliverable in deliverables:
            submissions_count = await self.db["submissions"].count_documents(
                {"deliverable_id": deliverable["_id"]}
            )
            deliverable["total_submissions"] = submissions_count

        return deliverables

    async def get_upcoming_deliverables(self, limit: int = 10):
        current_time = datetime.now()
        deliverables = await self.collection.find({
            "start_date": {"$gt": current_time}
        }).sort("start_date", 1).limit(limit).to_list(limit)

        # Calculate total submissions for each deliverable
        for deliverable in deliverables:
            submissions_count = await self.db["submissions"].count_documents(
                {"deliverable_id": deliverable["_id"]}
            )
            deliverable["total_submissions"] = submissions_count

        return deliverables