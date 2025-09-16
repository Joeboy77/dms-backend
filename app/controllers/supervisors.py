from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException


class SupervisorController:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db["supervisors"]

    async def get_all_supervisors(self, limit: int = 10, cursor: str | None = None):
        query = {}
        if cursor:
            query["_id"] = {"$gt": ObjectId(cursor)}

        supervisors = await self.collection.find(query).limit(limit).to_list(limit)

        # Add project student count for each supervisor
        for supervisor in supervisors:
            count = await self.db["fyps"].count_documents({"supervisor": supervisor["_id"]})
            supervisor["project_student_count"] = count

        next_cursor = None
        if len(supervisors) == limit:
            next_cursor = str(supervisors[-1]["_id"])

        return {
            "items": supervisors,
            "next_cursor": next_cursor
        }

    async def get_supervisor_by_id(self, supervisor_id: str):
        supervisor = await self.collection.find_one({"_id": ObjectId(supervisor_id)})
        if not supervisor:
            raise HTTPException(status_code=404, detail="Supervisor not found")

        # Add project student count
        count = await self.db["fyps"].count_documents({"supervisor": supervisor["_id"]})
        supervisor["project_student_count"] = count

        return supervisor

    async def create_supervisor(self, supervisor_data: dict):
        # Convert lecturer_id to ObjectId if it's a string
        if "lecturer_id" in supervisor_data and isinstance(supervisor_data["lecturer_id"], str):
            supervisor_data["lecturer_id"] = ObjectId(supervisor_data["lecturer_id"])

        # Check if lecturer exists
        lecturer = await self.db["lecturers"].find_one({"_id": supervisor_data["lecturer_id"]})
        if not lecturer:
            raise HTTPException(status_code=404, detail="Lecturer not found")

        # Check if supervisor already exists for this lecturer
        existing_supervisor = await self.collection.find_one({"lecturer_id": supervisor_data["lecturer_id"]})
        if existing_supervisor:
            raise HTTPException(status_code=400, detail="Supervisor already exists for this lecturer")

        supervisor_data["createdAt"] = datetime.now()
        supervisor_data["updatedAt"] = datetime.now()

        result = await self.collection.insert_one(supervisor_data)
        created_supervisor = await self.collection.find_one({"_id": result.inserted_id})

        # Add project student count
        created_supervisor["project_student_count"] = 0

        return created_supervisor

    async def update_supervisor(self, supervisor_id: str, update_data: dict):
        update_data = {k: v for k, v in update_data.items() if v is not None}

        if not update_data:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        # Convert lecturer_id to ObjectId if it's a string
        if "lecturer_id" in update_data and isinstance(update_data["lecturer_id"], str):
            update_data["lecturer_id"] = ObjectId(update_data["lecturer_id"])

        # If updating lecturer_id, check if lecturer exists
        if "lecturer_id" in update_data:
            lecturer = await self.db["lecturers"].find_one({"_id": update_data["lecturer_id"]})
            if not lecturer:
                raise HTTPException(status_code=404, detail="Lecturer not found")

        update_data["updatedAt"] = datetime.now()

        result = await self.collection.update_one(
            {"_id": ObjectId(supervisor_id)},
            {"$set": update_data}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Supervisor not found")

        updated_supervisor = await self.collection.find_one({"_id": ObjectId(supervisor_id)})

        # Add project student count
        count = await self.db["fyps"].count_documents({"supervisor": updated_supervisor["_id"]})
        updated_supervisor["project_student_count"] = count

        return updated_supervisor

    async def delete_supervisor(self, supervisor_id: str):
        result = await self.collection.delete_one({"_id": ObjectId(supervisor_id)})

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Supervisor not found")

        return {"message": "Supervisor deleted successfully"}

    async def get_supervisor_with_lecturer(self, supervisor_id: str):
        supervisor = await self.get_supervisor_by_id(supervisor_id)

        lecturer = await self.db["lecturers"].find_one({"_id": supervisor["lecturer_id"]})
        if not lecturer:
            raise HTTPException(status_code=404, detail="Lecturer not found")

        return {
            "supervisor": supervisor,
            "lecturer": lecturer
        }

    async def get_all_supervisors_with_lecturer_details(self, limit: int = 10, cursor: str | None = None):
        query = {}
        if cursor:
            query["_id"] = {"$gt": ObjectId(cursor)}

        supervisors = await self.collection.find(query).limit(limit).to_list(limit)

        supervisors_with_details = []
        for supervisor in supervisors:
            # Get project student count
            count = await self.db["fyps"].count_documents({"supervisor": supervisor["_id"]})
            supervisor["project_student_count"] = count

            # Get lecturer details
            lecturer = await self.db["lecturers"].find_one({"_id": supervisor["lecturer_id"]})
            if lecturer:
                supervisor_with_details = {
                    "_id": supervisor["_id"],
                    "lecturer_id": supervisor["lecturer_id"],
                    "max_students": supervisor.get("max_students"),
                    "project_student_count": supervisor["project_student_count"],
                    "createdAt": supervisor["createdAt"],
                    "updatedAt": supervisor["updatedAt"],
                    "lecturer_name": lecturer.get("name", ""),
                    "lecturer_email": lecturer.get("email", ""),
                    "lecturer_phone": lecturer.get("phone"),
                    "lecturer_department": lecturer.get("department"),
                    "lecturer_title": lecturer.get("title"),
                    "lecturer_specialization": lecturer.get("specialization"),
                }
                supervisors_with_details.append(supervisor_with_details)

        next_cursor = None
        if len(supervisors_with_details) == limit:
            next_cursor = str(supervisors_with_details[-1]["_id"])

        return {
            "items": supervisors_with_details,
            "next_cursor": next_cursor
        }

    async def get_lecturer_by_supervisor_id(self, supervisor_id: str):
        supervisor = await self.collection.find_one({"_id": ObjectId(supervisor_id)})
        if not supervisor:
            raise HTTPException(status_code=404, detail="Supervisor not found")

        lecturer = await self.db["lecturers"].find_one({"_id": supervisor["lecturer_id"]})
        if not lecturer:
            raise HTTPException(status_code=404, detail="Lecturer not found")

        return lecturer