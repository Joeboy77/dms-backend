from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException
import random
import string


class ComplaintController:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db["complaints"]

    def generate_reference_number(self):
        """Generate a unique reference number like CMP-7351-62777"""
        random_part1 = ''.join(random.choices(string.digits, k=4))
        random_part2 = ''.join(random.choices(string.digits, k=5))
        return f"CMP-{random_part1}-{random_part2}"

    async def get_all_complaints(self, limit: int = 10, cursor: str | None = None):
        query = {"deleted": {"$ne": True}}
        if cursor:
            query["_id"] = {"$gt": ObjectId(cursor)}

        complaints = await self.collection.find(query).limit(limit).to_list(limit)

        next_cursor = None
        if len(complaints) == limit:
            next_cursor = str(complaints[-1]["_id"])

        return {
            "items": complaints,
            "next_cursor": next_cursor
        }

    async def get_complaint_by_id(self, complaint_id: str):
        complaint = await self.collection.find_one({
            "_id": ObjectId(complaint_id),
            "deleted": {"$ne": True}
        })
        if not complaint:
            raise HTTPException(status_code=404, detail="Complaint not found")
        return complaint

    async def create_complaint(self, complaint_data: dict):
        complaint_data["createdAt"] = datetime.now()
        complaint_data["updatedAt"] = datetime.now()

        # Generate reference number if not provided
        if not complaint_data.get("reference"):
            complaint_data["reference"] = self.generate_reference_number()

        result = await self.collection.insert_one(complaint_data)
        created_complaint = await self.collection.find_one({"_id": result.inserted_id})
        return created_complaint

    async def update_complaint(self, complaint_id: str, update_data: dict):
        update_data = {k: v for k, v in update_data.items() if v is not None}

        if not update_data:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        update_data["updatedAt"] = datetime.now()

        result = await self.collection.update_one(
            {"_id": ObjectId(complaint_id), "deleted": {"$ne": True}},
            {"$set": update_data}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Complaint not found")

        updated_complaint = await self.collection.find_one({"_id": ObjectId(complaint_id)})
        return updated_complaint

    async def delete_complaint(self, complaint_id: str):
        result = await self.collection.update_one(
            {"_id": ObjectId(complaint_id)},
            {"$set": {"deleted": True, "updatedAt": datetime.now()}}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Complaint not found")

        return {"message": "Complaint deleted successfully"}

    async def get_complaints_by_status(self, status: str):
        complaints = await self.collection.find({
            "status": status,
            "deleted": {"$ne": True}
        }).to_list(None)
        return complaints

    async def get_complaints_by_category(self, category_id: str):
        complaints = await self.collection.find({
            "category": ObjectId(category_id),
            "deleted": {"$ne": True}
        }).to_list(None)
        return complaints

    async def get_complaints_by_reference(self, reference: str):
        complaint = await self.collection.find_one({
            "reference": reference,
            "deleted": {"$ne": True}
        })
        if not complaint:
            raise HTTPException(status_code=404, detail="Complaint not found with this reference")
        return complaint

    async def assign_complaint(self, complaint_id: str, assigned_to: list[str]):
        assigned_to_objects = [ObjectId(user_id) for user_id in assigned_to]

        # Add action for assignment
        action = {
            "action_type": "ASSIGNED",
            "description": f"Complaint assigned to {len(assigned_to)} user(s)",
            "performed_at": datetime.now(),
            "notes": f"Assigned to: {', '.join(assigned_to)}"
        }

        result = await self.collection.update_one(
            {"_id": ObjectId(complaint_id), "deleted": {"$ne": True}},
            {
                "$set": {
                    "assignedTo": assigned_to_objects,
                    "status": "ASSIGNED",
                    "updatedAt": datetime.now()
                },
                "$push": {"actions": action}
            }
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Complaint not found")

        updated_complaint = await self.collection.find_one({"_id": ObjectId(complaint_id)})
        return updated_complaint

    async def add_feedback(self, complaint_id: str, feedback_data: dict):
        feedback = {
            "feedback_type": feedback_data.get("feedback_type", "GENERAL"),
            "message": feedback_data["message"],
            "provided_by": ObjectId(feedback_data["provided_by"]),
            "provided_at": datetime.now(),
            "rating": feedback_data.get("rating")
        }

        result = await self.collection.update_one(
            {"_id": ObjectId(complaint_id), "deleted": {"$ne": True}},
            {
                "$push": {"feedbacks": feedback},
                "$set": {"updatedAt": datetime.now()}
            }
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Complaint not found")

        updated_complaint = await self.collection.find_one({"_id": ObjectId(complaint_id)})
        return updated_complaint

    async def update_status(self, complaint_id: str, status: str, notes: str | None = None):
        action = {
            "action_type": "STATUS_CHANGE",
            "description": f"Status changed to {status}",
            "performed_at": datetime.now(),
            "notes": notes
        }

        result = await self.collection.update_one(
            {"_id": ObjectId(complaint_id), "deleted": {"$ne": True}},
            {
                "$set": {
                    "status": status,
                    "updatedAt": datetime.now()
                },
                "$push": {"actions": action}
            }
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Complaint not found")

        updated_complaint = await self.collection.find_one({"_id": ObjectId(complaint_id)})
        return updated_complaint