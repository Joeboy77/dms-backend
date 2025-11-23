from datetime import datetime
from typing import Optional, List, Dict
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException


class LecturerProjectAreaController:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db["lecturer_project_areas"]

    async def get_all_lecturer_project_areas(self, limit: int = 10, cursor: Optional[str] = None):
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
            lpa_data["academicYear"] = lpa_data["academicYear"]
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
        # student = await self.db["students"].find_one({"_id": ObjectId(student_id)})
        student = await self.db["students"].find_one({"academicId": student_id})
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

        # Get student's FYP details to find supervisor and project area
        # fyp = await self.db["fyps"].find_one({"student": ObjectId(student_id)})
        fyp = await self.db["fyps"].find_one({"student": str(student["_id"])})
        print(fyp)
        print(student)

        supervisor = None
        project_area = None

        if fyp:
            # Get supervisor details
            if fyp.get("supervisor"):
                supervisor = await self.db["supervisors"].find_one({"_id": ObjectId(fyp["supervisor"])})
                lecturer = await self.db["lecturers"].find_one({"_id": supervisor["lecturer_id"]})

            # Get project area details
            if fyp.get("projectArea"):
                project_area = await self.db["project_areas"].find_one({"_id": ObjectId(fyp["projectArea"])})

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
                "program": student.get("program", ""),
                "level": student.get("level"),
                "type": student.get("type", "UNDERGRADUATE"),
                "deleted": student.get("deleted", False)
            },
            "supervisor": {
                "supervisor_id": str(supervisor["_id"]) if supervisor else None,
                "supervisor_name": f"{lecturer.get('surname', '')} {lecturer.get('otherNames', '')}".strip() if lecturer else None,
                "supervisor_email": lecturer.get("email", "") if lecturer else None,
                "supervisor_phone": lecturer.get("phone", "") if lecturer else None,
                "supervisor_title": lecturer.get("title", "") if lecturer else None,
                # "supervisor_department": lecturer.get("department", "") if lecturer else None,
                # "supervisor_specialization": lecturer.get("specialization", "") if lecturer else None,
                "supervisor_academic_id": lecturer.get("academicId", "") if lecturer else None,
                "supervisor_office_hours": lecturer.get("officeHours", "") if lecturer else None,
                "supervisor_office_location": lecturer.get("officeLocation", "") if lecturer else None,
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

    async def get_detailed_by_academic_year(self, academic_year_id: str):
        lpas = await self.collection.find({"academicYear": academic_year_id}).to_list(None)

        detailed_lpas = []
        for lpa in lpas:
            # Get lecturer details
            lecturer = await self.db["lecturers"].find_one({"_id": lpa["lecturer"]})

            # Get academic year details
            academic_year = await self.db["academic_years"].find_one({"year": lpa["academicYear"]})

            # Get project areas details
            project_areas = []
            for pa_id in lpa["projectAreas"]:
                pa = await self.db["project_areas"].find_one({"_id": pa_id})
                if pa:
                    project_areas.append({
                        "project_area_id": str(pa["_id"]),
                        "title": pa.get("title", ""),
                        "description": pa.get("description", ""),
                        "image": pa.get("image", ""),
                        "created_at": pa.get("createdAt"),
                        "updated_at": pa.get("updatedAt")
                    })

            detailed_lpa = {
                "id": str(lpa["_id"]),
                "lecturer": {
                    "lecturer_id": str(lecturer["_id"]) if lecturer else None,
                    "name": f"{lecturer.get('surname', '')} {lecturer.get('otherNames', '')}" if lecturer else None,
                    "email": lecturer.get("email", "") if lecturer else None,
                    "phone": lecturer.get("phone", "") if lecturer else None,
                    "department": lecturer.get("department", "Computer Science") if lecturer else None,
                    "title": lecturer.get("title", "") if lecturer else None,
                    "specialization": lecturer.get("specialization", "") if lecturer else None
                } if lecturer else None,
                "academic_year": {
                    "academic_year_id": str(academic_year["_id"]) if academic_year else None,
                    "year": academic_year.get("year", "") if academic_year else None,
                    "status": academic_year.get("status", "") if academic_year else None,
                    "terms": academic_year.get("terms", 0) if academic_year else None,
                    "current_term": academic_year.get("currentTerm", 0) if academic_year else None
                } if academic_year else None,
                "project_areas": project_areas,
                "created_at": lpa.get("createdAt"),
                "updated_at": lpa.get("updatedAt")
            }
            detailed_lpas.append(detailed_lpa)

        return detailed_lpas