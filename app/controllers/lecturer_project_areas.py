from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException


class LecturerProjectAreaController:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db["lecturer_project_areas"]

    async def get_all_lecturer_project_areas(self, limit: int = 10, cursor: str | None = None):
        query = {}
        if cursor:
            query["_id"] = {"$gt": ObjectId(cursor)}

        lecturer_project_areas = await self.collection.find(query).limit(limit).to_list(limit)

        next_cursor = None
        if len(lecturer_project_areas) == limit:
            next_cursor = str(lecturer_project_areas[-1]["_id"])

        return {
            "items": lecturer_project_areas,
            "next_cursor": next_cursor
        }

    async def get_lecturer_project_area_by_id(self, lpa_id: str):
        lpa = await self.collection.find_one({"_id": ObjectId(lpa_id)})
        if not lpa:
            raise HTTPException(status_code=404, detail="Lecturer project area not found")
        return lpa

    async def create_lecturer_project_area(self, lpa_data: dict):
        # Convert IDs to ObjectId if they're strings
        if "lecturer" in lpa_data and isinstance(lpa_data["lecturer"], str):
            lpa_data["lecturer"] = ObjectId(lpa_data["lecturer"])
        if "academicYear" in lpa_data and isinstance(lpa_data["academicYear"], str):
            lpa_data["academicYear"] = ObjectId(lpa_data["academicYear"])
        if "projectAreas" in lpa_data:
            lpa_data["projectAreas"] = [
                ObjectId(pa_id) if isinstance(pa_id, str) else pa_id
                for pa_id in lpa_data["projectAreas"]
            ]

        lpa_data["createdAt"] = datetime.now()
        lpa_data["updatedAt"] = datetime.now()

        result = await self.collection.insert_one(lpa_data)
        created_lpa = await self.collection.find_one({"_id": result.inserted_id})
        return created_lpa

    async def update_lecturer_project_area(self, lpa_id: str, update_data: dict):
        update_data = {k: v for k, v in update_data.items() if v is not None}

        if not update_data:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        # Convert IDs to ObjectId if they're strings
        if "lecturer" in update_data and isinstance(update_data["lecturer"], str):
            update_data["lecturer"] = ObjectId(update_data["lecturer"])
        if "academicYear" in update_data and isinstance(update_data["academicYear"], str):
            update_data["academicYear"] = ObjectId(update_data["academicYear"])
        if "projectAreas" in update_data:
            update_data["projectAreas"] = [
                ObjectId(pa_id) if isinstance(pa_id, str) else pa_id
                for pa_id in update_data["projectAreas"]
            ]

        update_data["updatedAt"] = datetime.now()

        result = await self.collection.update_one(
            {"_id": ObjectId(lpa_id)},
            {"$set": update_data}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Lecturer project area not found")

        updated_lpa = await self.collection.find_one({"_id": ObjectId(lpa_id)})
        return updated_lpa

    async def delete_lecturer_project_area(self, lpa_id: str):
        result = await self.collection.delete_one({"_id": ObjectId(lpa_id)})

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Lecturer project area not found")

        return {"message": "Lecturer project area deleted successfully"}

    async def get_by_lecturer(self, lecturer_id: str):
        lpas = await self.collection.find({"lecturer": ObjectId(lecturer_id)}).to_list(None)
        return lpas

    async def get_by_academic_year(self, academic_year_id: str):
        lpas = await self.collection.find({"academicYear": ObjectId(academic_year_id)}).to_list(None)
        return lpas

    async def get_student_info_with_supervisor_and_project_area(self, student_id: str):
        # Get student details
        student = await self.db["students"].find_one({"_id": ObjectId(student_id)})
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

        # Get student's FYP details to find supervisor and project area
        fyp = await self.db["fyps"].find_one({"student": ObjectId(student_id)})

        supervisor = None
        project_area = None

        if fyp:
            # Get supervisor details
            if fyp.get("supervisor"):
                supervisor = await self.db["lecturers"].find_one({"_id": fyp["supervisor"]})

            # Get project area details
            if fyp.get("projectArea"):
                project_area = await self.db["project_areas"].find_one({"_id": fyp["projectArea"]})

        # Get program details
        program = None
        if student.get("program"):
            program = await self.db["programs"].find_one({"_id": student["program"]})

        # Format student name
        student_name = f"{student.get('surname', '')} {student.get('otherNames', '')}".strip()

        return {
            "student": {
                "student_id": str(student["_id"]),
                "student_name": student_name,
                "surname": student.get("surname", ""),
                "otherNames": student.get("otherNames", ""),
                "email": student.get("email", ""),
                "phone": student.get("phone", ""),
                "student_image": student.get("image", ""),
                "academicId": student.get("academicId", student.get("studentID", "")),
                "program": program,
                "level": student.get("level"),
                "type": student.get("type", "UNDERGRADUATE"),
                "deleted": student.get("deleted", False)
            },
            "supervisor": {
                "supervisor_id": str(supervisor["_id"]) if supervisor else None,
                "supervisor_name": supervisor.get("name", "") if supervisor else None,
                "supervisor_email": supervisor.get("email", "") if supervisor else None,
                "supervisor_department": supervisor.get("department", "") if supervisor else None
            } if supervisor else None,
            "project_area": {
                "project_area_id": str(project_area["_id"]) if project_area else None,
                "title": project_area.get("title", "") if project_area else None,
                "description": project_area.get("description", "") if project_area else None,
                "image": project_area.get("image", "") if project_area else None
            } if project_area else None,
            "fyp_details": {
                "fyp_id": str(fyp["_id"]) if fyp else None,
                "checkin": str(fyp["checkin"]) if fyp and fyp.get("checkin") else None,
                "created_at": fyp.get("createdAt") if fyp else None,
                "updated_at": fyp.get("updatedAt") if fyp else None
            } if fyp else None
        }