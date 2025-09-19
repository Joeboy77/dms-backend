from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException


class SupervisorController:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db["supervisors"]

    async def get_all_supervisors(self, limit: int = 10, cursor: str | None = None):
        # Get all lecturers who have supervisor role in logins
        supervisor_role_id = "684b0436cb438526c6aea950"
        supervisor_logins = await self.db["logins"].find({"roles": ObjectId(supervisor_role_id)}).to_list(None)

        supervisors = []
        count = 0

        for login in supervisor_logins:
            if cursor and count < int(cursor):
                count += 1
                continue

            if len(supervisors) >= limit:
                break

            # Get lecturer details using academicId
            lecturer = await self.db["lecturers"].find_one({"academicId": login["academicId"]})
            if lecturer:
                # Count students supervised by this lecturer
                student_count = await self.db["fyps"].count_documents({"supervisor": lecturer["_id"]})

                supervisor_data = {
                    "_id": lecturer["_id"],
                    "lecturer_id": lecturer["_id"],
                    "max_students": lecturer.get("max_students"),
                    "project_student_count": student_count,
                    "created_at": lecturer.get("createdAt"),
                    "updated_at": lecturer.get("updatedAt"),
                    "academic_id": login["academicId"]
                }
                supervisors.append(supervisor_data)

        next_cursor = None
        if len(supervisors) == limit:
            next_cursor = str(count + limit)

        return {
            "items": supervisors,
            "next_cursor": next_cursor
        }

    async def get_supervisor_by_id(self, supervisor_id: str):
        # Get lecturer details
        lecturer = await self.db["lecturers"].find_one({"_id": ObjectId(supervisor_id)})
        if not lecturer:
            raise HTTPException(status_code=404, detail="Lecturer not found")

        # Check if lecturer has supervisor role
        supervisor_role_id = "684b0436cb438526c6aea950"
        login = await self.db["logins"].find_one({
            "academicId": lecturer.get("academicId"),
            "roles": ObjectId(supervisor_role_id)
        })

        if not login:
            raise HTTPException(status_code=404, detail="Supervisor role not found for this lecturer")

        # Count students supervised by this lecturer
        student_count = await self.db["fyps"].count_documents({"supervisor": lecturer["_id"]})

        supervisor_data = {
            "_id": lecturer["_id"],
            "lecturer_id": lecturer["_id"],
            "max_students": lecturer.get("max_students"),
            "project_student_count": student_count,
            "created_at": lecturer.get("createdAt"),
            "updated_at": lecturer.get("updatedAt"),
            "academic_id": lecturer.get("academicId")
        }

        return supervisor_data

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
        # Get all lecturers who have supervisor role in logins
        supervisor_role_id = "684b0436cb438526c6aea950"
        supervisor_logins = await self.db["logins"].find({"roles": ObjectId(supervisor_role_id)}).to_list(None)

        supervisors_with_details = []
        count = 0

        for login in supervisor_logins:
            if cursor and count < int(cursor):
                count += 1
                continue

            if len(supervisors_with_details) >= limit:
                break

            # Get lecturer details using academicId
            lecturer = await self.db["lecturers"].find_one({"academicId": login["academicId"]})
            if lecturer:
                # Count students supervised by this lecturer
                student_count = await self.db["fyps"].count_documents({"supervisor": lecturer["_id"]})

                # Create full name from surname and otherNames
                lecturer_name = f"{lecturer.get('surname', '')} {lecturer.get('otherNames', '')}".strip()

                supervisor_with_details = {
                    "_id": str(lecturer["_id"]),
                    "lecturer_id": str(lecturer["_id"]),
                    "max_students": lecturer.get("max_students"),
                    "project_student_count": student_count,
                    "createdAt": lecturer.get("createdAt"),
                    "updatedAt": lecturer.get("updatedAt"),
                    "lecturer_name": lecturer_name,
                    "lecturer_email": lecturer.get("email", ""),
                    "lecturer_phone": lecturer.get("phone"),
                    "lecturer_position": lecturer.get("position"),
                    "lecturer_title": lecturer.get("title"),
                    "lecturer_bio": lecturer.get("bio"),
                    "lecturer_office_hours": lecturer.get("officeHours"),
                    "lecturer_office_location": lecturer.get("officeLocation"),
                    "academic_id": lecturer.get("academicId", "")
                }
                supervisors_with_details.append(supervisor_with_details)
                count += 1

        next_cursor = None
        if len(supervisors_with_details) == limit:
            next_cursor = str(count)

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

    async def get_supervisors_by_academic_year(self, academic_year_id: str):
        # First get the fypcheckin for this academic year
        checkin = await self.db["fypcheckins"].find_one({"academicYear": ObjectId(academic_year_id)})
        if not checkin:
            return []

        # Get all FYPs for this checkin period to find active supervisors
        fyps = await self.db["fyps"].find({"checkin": checkin["_id"]}).to_list(None)

        # Extract unique supervisor IDs (lecturer IDs)
        supervisor_ids = list(set(fyp["supervisor"] for fyp in fyps if fyp.get("supervisor")))

        # Get supervisor details - check if they have supervisor role
        supervisor_role_id = "684b0436cb438526c6aea950"
        supervisors = []

        for supervisor_id in supervisor_ids:
            # Get lecturer details
            lecturer = await self.db["lecturers"].find_one({"_id": supervisor_id})
            if lecturer:
                # Check if lecturer has supervisor role in logins
                login = await self.db["logins"].find_one({
                    "academicId": lecturer.get("academicId"),
                    "roles": ObjectId(supervisor_role_id)
                })

                if login:
                    # Count students for this academic year
                    student_count = len([fyp for fyp in fyps if fyp.get("supervisor") == supervisor_id])

                    supervisor_data = {
                        "_id": lecturer["_id"],
                        "lecturer_id": lecturer["_id"],
                        "max_students": lecturer.get("max_students"),
                        "project_student_count": student_count,
                        "created_at": lecturer.get("createdAt"),
                        "updated_at": lecturer.get("updatedAt"),
                        "academic_id": lecturer.get("academicId")
                    }
                    supervisors.append(supervisor_data)

        return supervisors

    async def get_supervisors_by_academic_year_detailed(self, academic_year_id: str):
        # Get basic supervisors for this academic year
        supervisors = await self.get_supervisors_by_academic_year(academic_year_id)

        # Get academic year details
        academic_year = await self.db["academic_years"].find_one({"_id": ObjectId(academic_year_id)})

        detailed_supervisors = []
        for supervisor in supervisors:
            # Get lecturer details (supervisor already contains lecturer info)
            lecturer_id = supervisor["lecturer_id"]
            lecturer = await self.db["lecturers"].find_one({"_id": lecturer_id})

            # Get lecturer's project areas for this academic year
            lpa = await self.db["lecturer_project_areas"].find_one({
                "lecturer": lecturer_id,
                "academicYear": ObjectId(academic_year_id)
            })

            project_areas = []
            if lpa and lpa.get("projectAreas"):
                for pa_id in lpa["projectAreas"]:
                    pa = await self.db["project_areas"].find_one({"_id": pa_id})
                    if pa:
                        project_areas.append({
                            "project_area_id": str(pa["_id"]),
                            "title": pa.get("title", ""),
                            "description": pa.get("description", ""),
                            "image": pa.get("image", "")
                        })

            detailed_supervisor = {
                "supervisor": {
                    "supervisor_id": str(supervisor["_id"]),
                    "academic_id": supervisor.get("academic_id", ""),
                    "max_students": supervisor.get("max_students"),
                    "project_student_count": supervisor.get("project_student_count", 0),
                    "created_at": supervisor.get("created_at"),
                    "updated_at": supervisor.get("updated_at")
                },
                "lecturer": {
                    "lecturer_id": str(lecturer["_id"]) if lecturer else None,
                    "name": lecturer.get("name", "") if lecturer else None,
                    "email": lecturer.get("email", "") if lecturer else None,
                    "phone": lecturer.get("phone", "") if lecturer else None,
                    "department": lecturer.get("department", "") if lecturer else None,
                    "title": lecturer.get("title", "") if lecturer else None,
                    "specialization": lecturer.get("specialization", "") if lecturer else None,
                    "academic_id": lecturer.get("academicId", "") if lecturer else None
                } if lecturer else None,
                "academic_year": {
                    "academic_year_id": str(academic_year["_id"]) if academic_year else None,
                    "title": academic_year.get("title", "") if academic_year else None,
                    "status": academic_year.get("status", "") if academic_year else None,
                    "terms": academic_year.get("terms", 0) if academic_year else None,
                    "current_term": academic_year.get("currentTerm", 0) if academic_year else None
                } if academic_year else None,
                "project_areas": project_areas
            }
            detailed_supervisors.append(detailed_supervisor)

        return detailed_supervisors

    async def get_supervisor_by_student_id(self, student_id: str):
        """Get supervisor details for a specific student by student academic ID"""
        # First find the student by academicId
        student = await self.db["students"].find_one({"academicId": student_id})
        if not student:
            raise HTTPException(status_code=404, detail=f"Student {student_id} not found")

        # Find the most recent FYP assignment for this student (sorted by creation date)
        fyp = await self.db["fyps"].find_one(
            {"student": student["_id"]},
            sort=[("createdAt", -1)]  # Get most recent assignment
        )
        if not fyp or not fyp.get("supervisor"):
            raise HTTPException(status_code=404, detail=f"No supervisor assigned to student {student_id}")

        # Get supervisor (lecturer) details
        lecturer = await self.db["lecturers"].find_one({"_id": fyp["supervisor"]})
        if not lecturer:
            raise HTTPException(status_code=404, detail="Supervisor lecturer not found")

        # Check if lecturer has supervisor role
        supervisor_role_id = "684b0436cb438526c6aea950"
        login = await self.db["logins"].find_one({
            "academicId": lecturer.get("academicId"),
            "roles": ObjectId(supervisor_role_id)
        })

        if not login:
            raise HTTPException(status_code=404, detail="Lecturer does not have supervisor role")

        # Count total students supervised by this lecturer
        total_students = await self.db["fyps"].count_documents({"supervisor": lecturer["_id"]})

        # Get FYP details
        fyp_details = {
            "fyp_id": str(fyp["_id"]),
            "created_at": fyp.get("createdAt"),
            "updated_at": fyp.get("updatedAt"),
            "checkin_id": str(fyp["checkin"]) if fyp.get("checkin") else None,
            "project_area_id": str(fyp["projectArea"]) if fyp.get("projectArea") else None
        }

        # Get project area details if available
        project_area = None
        if fyp.get("projectArea"):
            pa = await self.db["project_areas"].find_one({"_id": fyp["projectArea"]})
            if pa:
                project_area = {
                    "project_area_id": str(pa["_id"]),
                    "title": pa.get("title", ""),
                    "description": pa.get("description", ""),
                    "image": pa.get("image", "")
                }

        # Format supervisor name
        supervisor_name = f"{lecturer.get('surname', '')} {lecturer.get('otherNames', '')}".strip()

        return {
            "student": {
                "student_id": str(student["_id"]),
                "academic_id": student.get("academicId", ""),
                "student_name": f"{student.get('surname', '')} {student.get('otherNames', '')}".strip(),
                "email": student.get("email", ""),
                "phone": student.get("phone", ""),
                "program": str(student.get("program")) if student.get("program") else None,
                "level": str(student.get("level")) if student.get("level") else None
            },
            "supervisor": {
                "supervisor_id": str(lecturer["_id"]),
                "academic_id": lecturer.get("academicId", ""),
                "name": supervisor_name,
                "email": lecturer.get("email", ""),
                "phone": lecturer.get("phone", ""),
                "title": lecturer.get("title", ""),
                "position": lecturer.get("position", ""),
                "department": lecturer.get("department", ""),
                "bio": lecturer.get("bio", ""),
                "office_hours": lecturer.get("officeHours", ""),
                "office_location": lecturer.get("officeLocation", ""),
                "max_students": lecturer.get("max_students"),
                "total_students_supervised": total_students,
                "specialization": lecturer.get("specialization", "")
            },
            "assignment": fyp_details,
            "project_area": project_area
        }