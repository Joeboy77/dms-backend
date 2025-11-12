from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException


class FypController:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db["fyps"]
        self.project_areas_collection = db["project_areas"]

    def _validate_object_id(self, id_str: str, field_name: str = "ID") -> ObjectId:
        """Validate and convert string to ObjectId, raising appropriate error if invalid."""
        if not ObjectId.is_valid(id_str):
            raise HTTPException(status_code=400, detail=f"Invalid {field_name}: {id_str}")
        return ObjectId(id_str)

    async def get_all_fyps(self, limit: int = 10, cursor: str | None = None):
        query = {}
        if cursor:
            try:
                query["_id"] = {"$gt": self._validate_object_id(cursor, "cursor")}
            except HTTPException:
                raise HTTPException(status_code=400, detail=f"Invalid cursor: {cursor}")

        fyps = await self.collection.find(query).limit(limit).to_list(limit)

        next_cursor = None
        if len(fyps) == limit:
            next_cursor = str(fyps[-1]["_id"])

        return {
            "items": fyps,
            "next_cursor": next_cursor
        }

    async def get_fyp_by_id(self, fyp_id: str):
        try:
            fyp_oid = self._validate_object_id(fyp_id, "FYP ID")
        except HTTPException:
            raise

        fyp = await self.collection.find_one({"_id": fyp_oid})
        if not fyp:
            raise HTTPException(status_code=404, detail="FYP not found")
        return fyp

    async def create_fyp(self, fyp_data: dict):
        fyp_data["createdAt"] = datetime.utcnow()
        fyp_data["updatedAt"] = datetime.utcnow()

        # Normalize student field - handle both ObjectId and string
        student_field = fyp_data.get("student")
        if student_field:
            # If it's a string, try to find student by academicId first, then by ObjectId
            if isinstance(student_field, str):
                student = await self.db["students"].find_one({"academicId": student_field})
                if not student and ObjectId.is_valid(student_field):
                    student = await self.db["students"].find_one({"_id": ObjectId(student_field)})
                if not student:
                    raise HTTPException(status_code=404, detail=f"Student {student_field} not found")
                fyp_data["student"] = student["_id"]
            elif isinstance(student_field, ObjectId):
                # Verify student exists
                student = await self.db["students"].find_one({"_id": student_field})
                if not student:
                    raise HTTPException(status_code=404, detail=f"Student with ID {student_field} not found")
            # If it's already an ObjectId, keep it as is

        # Check if student already has an FYP - handle both ObjectId and string forms
        student_oid = fyp_data.get("student")
        if student_oid:
            existing_fyp = await self.collection.find_one(
                {
                    "$or": [
                        {"student": student_oid},
                        {"student": str(student_oid)}
                    ]
                }
            )
            if existing_fyp:
                raise HTTPException(status_code=400, detail="Student already has an FYP assigned")

        # Normalize supervisor field if present
        supervisor_field = fyp_data.get("supervisor")
        if supervisor_field and isinstance(supervisor_field, str):
            # Try to find lecturer by academicId first
            lecturer = await self.db["lecturers"].find_one({"academicId": supervisor_field})
            if not lecturer and ObjectId.is_valid(supervisor_field):
                lecturer = await self.db["lecturers"].find_one({"_id": ObjectId(supervisor_field)})
            if not lecturer:
                raise HTTPException(status_code=404, detail=f"Supervisor {supervisor_field} not found")
            fyp_data["supervisor"] = lecturer["_id"]
        elif supervisor_field and isinstance(supervisor_field, ObjectId):
            # Verify supervisor exists
            lecturer = await self.db["lecturers"].find_one({"_id": supervisor_field})
            if not lecturer:
                raise HTTPException(status_code=404, detail=f"Supervisor with ID {supervisor_field} not found")

        # Normalize projectArea field if present
        project_area_field = fyp_data.get("projectArea")
        if project_area_field and isinstance(project_area_field, str):
            if ObjectId.is_valid(project_area_field):
                project_area_oid = ObjectId(project_area_field)
                # Verify project area exists
                project_area = await self.project_areas_collection.find_one({"_id": project_area_oid})
                if not project_area:
                    raise HTTPException(status_code=404, detail=f"Project area {project_area_field} not found")
                fyp_data["projectArea"] = project_area_oid
            else:
                raise HTTPException(status_code=400, detail=f"Invalid project area ID: {project_area_field}")
        elif project_area_field and isinstance(project_area_field, ObjectId):
            # Verify project area exists
            project_area = await self.project_areas_collection.find_one({"_id": project_area_field})
            if not project_area:
                raise HTTPException(status_code=404, detail=f"Project area with ID {project_area_field} not found")

        result = await self.collection.insert_one(fyp_data)
        created_fyp = await self.collection.find_one({"_id": result.inserted_id})
        return created_fyp

    async def update_fyp(self, fyp_id: str, update_data: dict):
        try:
            fyp_oid = self._validate_object_id(fyp_id, "FYP ID")
        except HTTPException:
            raise

        update_data = {k: v for k, v in update_data.items() if v is not None}

        if not update_data:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        # Normalize student field if being updated
        if "student" in update_data:
            student_field = update_data["student"]
            if isinstance(student_field, str):
                student = await self.db["students"].find_one({"academicId": student_field})
                if not student and ObjectId.is_valid(student_field):
                    student = await self.db["students"].find_one({"_id": ObjectId(student_field)})
                if not student:
                    raise HTTPException(status_code=404, detail=f"Student {student_field} not found")
                update_data["student"] = student["_id"]
            elif isinstance(student_field, ObjectId):
                student = await self.db["students"].find_one({"_id": student_field})
                if not student:
                    raise HTTPException(status_code=404, detail=f"Student with ID {student_field} not found")

            # Check if another FYP already exists for this student (excluding current FYP)
            student_oid = update_data["student"]
            existing_fyp = await self.collection.find_one(
                {
                    "_id": {"$ne": fyp_oid},
                    "$or": [
                        {"student": student_oid},
                        {"student": str(student_oid)}
                    ]
                }
            )
            if existing_fyp:
                raise HTTPException(status_code=400, detail="Student already has an FYP assigned")

        # Normalize supervisor field if being updated
        if "supervisor" in update_data:
            supervisor_field = update_data["supervisor"]
            if isinstance(supervisor_field, str):
                lecturer = await self.db["lecturers"].find_one({"academicId": supervisor_field})
                if not lecturer and ObjectId.is_valid(supervisor_field):
                    lecturer = await self.db["lecturers"].find_one({"_id": ObjectId(supervisor_field)})
                if not lecturer:
                    raise HTTPException(status_code=404, detail=f"Supervisor {supervisor_field} not found")
                update_data["supervisor"] = lecturer["_id"]
            elif isinstance(supervisor_field, ObjectId):
                lecturer = await self.db["lecturers"].find_one({"_id": supervisor_field})
                if not lecturer:
                    raise HTTPException(status_code=404, detail=f"Supervisor with ID {supervisor_field} not found")

        # Normalize projectArea field if being updated
        if "projectArea" in update_data:
            project_area_field = update_data["projectArea"]
            if isinstance(project_area_field, str):
                if ObjectId.is_valid(project_area_field):
                    project_area_oid = ObjectId(project_area_field)
                    project_area = await self.project_areas_collection.find_one({"_id": project_area_oid})
                    if not project_area:
                        raise HTTPException(status_code=404, detail=f"Project area {project_area_field} not found")
                    update_data["projectArea"] = project_area_oid
                else:
                    raise HTTPException(status_code=400, detail=f"Invalid project area ID: {project_area_field}")
            elif isinstance(project_area_field, ObjectId):
                project_area = await self.project_areas_collection.find_one({"_id": project_area_field})
                if not project_area:
                    raise HTTPException(status_code=404, detail=f"Project area with ID {project_area_field} not found")

        update_data["updatedAt"] = datetime.utcnow()

        result = await self.collection.update_one(
            {"_id": fyp_oid},
            {"$set": update_data}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="FYP not found")

        updated_fyp = await self.collection.find_one({"_id": fyp_oid})
        return updated_fyp

    async def delete_fyp(self, fyp_id: str):
        try:
            fyp_oid = self._validate_object_id(fyp_id, "FYP ID")
        except HTTPException:
            raise

        result = await self.collection.delete_one({"_id": fyp_oid})

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="FYP not found")

        return {"message": "FYP deleted successfully"}

    async def get_fyps_by_student(self, student_id: str):
        # Accept either academicId (e.g., CS2025001) or a Mongo ObjectId string
        student = await self.db["students"].find_one({"academicId": student_id})
        if not student and ObjectId.is_valid(student_id):
            student = await self.db["students"].find_one({"_id": ObjectId(student_id)})
        if not student:
            raise HTTPException(status_code=404, detail=f"Student {student_id} not found")

        # There should be at most one FYP per student; pick most recent if multiple
        # Handle both storage forms: ObjectId and stringified ObjectId
        student_oid = student["_id"]
        fyp = await self.collection.find_one(
            {
                "$or": [
                    {"student": student_oid},
                    {"student": str(student_oid)}
                ]
            },
            sort=[("createdAt", -1)]
        )
        if not fyp:
            raise HTTPException(status_code=404, detail=f"No FYP found for student {student_id}")

        # Populate single projectArea document in place of ObjectId
        project_area_id = fyp.get("projectArea")
        if project_area_id:
            if isinstance(project_area_id, str) and ObjectId.is_valid(project_area_id):
                project_area_id = ObjectId(project_area_id)
            project_area_doc = await self.project_areas_collection.find_one({"_id": project_area_id})
            if project_area_doc:
                fyp["projectArea"] = project_area_doc

        return fyp

    async def get_fyps_by_supervisor(self, supervisor_id: str):
        fyps = await self.collection.find({"supervisor": ObjectId(supervisor_id)}).to_list(None)
        return fyps

    async def get_fyps_by_project_area(self, project_area_id: str):
        fyps = await self.collection.find({"projectArea": ObjectId(project_area_id)}).to_list(None)
        return fyps

    async def get_fyps_by_checkin(self, checkin_id: str):
        fyps = await self.collection.find({"checkin": ObjectId(checkin_id)}).to_list(None)
        return fyps