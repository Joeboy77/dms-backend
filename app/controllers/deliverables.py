from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException

from app.api.v1.routes.database import convert_objectid_to_str


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
            "items": convert_objectid_to_str(deliverables),
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

        return convert_objectid_to_str(deliverable)

    async def create_deliverable(self, deliverable_data: dict):
        # Convert supervisor_id to ObjectId if it's a string
        if "supervisor_id" in deliverable_data and isinstance(deliverable_data["supervisor_id"], str):
            deliverable_data["supervisor_id"] = ObjectId(deliverable_data["supervisor_id"])

        # Auto-populate student_ids if not provided
        if not deliverable_data.get("student_ids"):
            supervisor_id = deliverable_data["supervisor_id"]

            # Get all FYPs for this supervisor to find their students (same logic as students controller)
            fyps = await self.db["fyps"].find({"supervisor": supervisor_id}).to_list(None)

            # Only include students that actually exist in the students collection
            student_ids = []
            for fyp in fyps:
                if fyp.get("student"):
                    # Verify the student still exists
                    student = await self.db["students"].find_one({"_id": fyp["student"]})
                    if student:
                        student_ids.append(fyp["student"])

            deliverable_data["student_ids"] = student_ids
        else:
            # Convert student_ids to ObjectIds if they're strings
            student_ids = []
            for student_id in deliverable_data["student_ids"]:
                if isinstance(student_id, str):
                    student_ids.append(ObjectId(student_id))
                else:
                    student_ids.append(student_id)
            deliverable_data["student_ids"] = student_ids

        deliverable_data["createdAt"] = datetime.now()
        deliverable_data["updatedAt"] = datetime.now()
        deliverable_data["total_submissions"] = 0

        result = await self.collection.insert_one(deliverable_data)
        created_deliverable = await self.collection.find_one({"_id": result.inserted_id})
        created_deliverable["total_submissions"] = 0
        return convert_objectid_to_str(created_deliverable)

    async def update_deliverable(self, deliverable_id: str, update_data: dict):
        update_data = {k: v for k, v in update_data.items() if v is not None}

        if not update_data:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        # Convert supervisor_id to ObjectId if it's a string
        if "supervisor_id" in update_data and isinstance(update_data["supervisor_id"], str):
            update_data["supervisor_id"] = ObjectId(update_data["supervisor_id"])

        # Convert student_ids to ObjectIds if they're strings
        if "student_ids" in update_data and update_data["student_ids"]:
            student_ids = []
            for student_id in update_data["student_ids"]:
                if isinstance(student_id, str):
                    student_ids.append(ObjectId(student_id))
                else:
                    student_ids.append(student_id)
            update_data["student_ids"] = student_ids

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

        return convert_objectid_to_str(updated_deliverable)

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

    async def get_deliverables_by_student_id(self, student_id: str):
        """Get all deliverables for a specific student by finding their supervisor first"""
        # First find the student by academicId
        student = await self.db["students"].find_one({"academicId": student_id})
        if not student:
            raise HTTPException(status_code=404, detail=f"Student {student_id} not found")

        # Find the most recent FYP assignment for this student to get supervisor
        fyp = await self.db["fyps"].find_one(
            {"student": student["_id"]},
            sort=[("createdAt", -1)]  # Get most recent assignment
        )
        if not fyp or not fyp.get("supervisor"):
            raise HTTPException(status_code=404, detail=f"No supervisor assigned to student {student_id}")

        supervisor_id = fyp["supervisor"]

        # Get all deliverables for this supervisor where this student is in the student_ids list
        deliverables = await self.collection.find({
            "supervisor_id": supervisor_id,
            "student_ids": student["_id"]
        }).sort("start_date", -1).to_list(None)

        # Calculate total submissions for each deliverable
        for deliverable in deliverables:
            submissions_count = await self.db["submissions"].count_documents(
                {"deliverable_id": deliverable["_id"]}
            )
            deliverable["total_submissions"] = submissions_count

            # Check if this specific student has submitted for this deliverable
            student_submission = await self.db["submissions"].find_one({
                "deliverable_id": deliverable["_id"],
                "student_id": student["_id"]
            })
            deliverable["student_submitted"] = student_submission is not None
            if student_submission:
                deliverable["student_submission_date"] = student_submission.get("submitted_at")
                deliverable["student_submission_id"] = str(student_submission["_id"])

        # Get student details for response
        student_info = {
            "student_id": str(student["_id"]),
            "academic_id": student.get("academicId", ""),
            "student_name": f"{student.get('surname', '')} {student.get('otherNames', '')}".strip(),
            "email": student.get("email", "")
        }

        # Get supervisor details
        supervisor = await self.db["lecturers"].find_one({"_id": supervisor_id})
        supervisor_info = {}
        if supervisor:
            supervisor_info = {
                "supervisor_id": str(supervisor["_id"]),
                "academic_id": supervisor.get("academicId", ""),
                "name": f"{supervisor.get('surname', '')} {supervisor.get('otherNames', '')}".strip(),
                "email": supervisor.get("email", "")
            }

        return {
            "student": student_info,
            "supervisor": supervisor_info,
            "deliverables": convert_objectid_to_str(deliverables),
            "total_deliverables": len(deliverables)
        }