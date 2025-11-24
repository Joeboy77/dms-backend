from datetime import datetime
from typing import Optional, List, Dict
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException


class SupervisorController:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db["supervisors"]

    async def get_all_supervisors(self, limit: int = 10, cursor: Optional[str] = None):
        query = {}
        if cursor:
            query["_id"] = {"$gt": ObjectId(cursor)}

        supervisors_docs = await self.collection.find(query).limit(limit).to_list(limit)

        supervisors = []
        for doc in supervisors_docs:
            lecturer = await self.db["lecturers"].find_one({"_id": doc.get("lecturer_id")})
            if lecturer:
                student_count = await self.db["fyps"].count_documents({"supervisor": doc.get("_id")})

                # Create complete supervisor information
                supervisor_name = f"{lecturer.get('surname', '')} {lecturer.get('otherNames', '')}".strip()
                
                supervisors.append({
                    "_id": str(doc.get("_id")),
                    "lecturer_id": str(lecturer["_id"]),
                    "name": supervisor_name,
                    "title": lecturer.get("title", ""),
                    "email": lecturer.get("email", ""),
                    "phone": lecturer.get("phone", ""),
                    "position": lecturer.get("position", ""),
                    "bio": lecturer.get("bio", ""),
                    "office_hours": lecturer.get("officeHours", ""),
                    "office_location": lecturer.get("officeLocation", ""),
                    "academic_id": lecturer.get("academicId", ""),
                    "max_students": doc.get("max_students", lecturer.get("max_students", 5)),
                    "current_students": student_count,
                    "createdAt": doc.get("createdAt", lecturer.get("createdAt")),
                    "updatedAt": doc.get("updatedAt", lecturer.get("updatedAt"))
                })

        next_cursor = None
        if len(supervisors_docs) == limit:
            next_cursor = str(supervisors_docs[-1]["_id"])

        return {
            "items": supervisors,
            "next_cursor": next_cursor
        }

    async def get_supervisor_by_id(self, supervisor_id: str):
        # Find supervisor entry in supervisors collection
        supervisor = await self.collection.find_one({"_id": ObjectId(supervisor_id)})
        if not supervisor:
            raise HTTPException(status_code=404, detail="Supervisor not found")

        lecturer = await self.db["lecturers"].find_one({"_id": supervisor.get("lecturer_id")})
        if not lecturer:
            raise HTTPException(status_code=404, detail="Lecturer not found")

        student_count = await self.db["fyps"].count_documents({"supervisor": lecturer["_id"]})

        # Create complete supervisor information
        supervisor_name = f"{lecturer.get('surname', '')} {lecturer.get('otherNames', '')}".strip()
        
        supervisor_data = {
            "_id": str(supervisor["_id"]),
            "lecturer_id": str(lecturer["_id"]),
            "name": supervisor_name,
            "title": lecturer.get("title", ""),
            "email": lecturer.get("email", ""),
            "phone": lecturer.get("phone", ""),
            "position": lecturer.get("position", ""),
            "bio": lecturer.get("bio", ""),
            "office_hours": lecturer.get("officeHours", ""),
            "office_location": lecturer.get("officeLocation", ""),
            "academic_id": lecturer.get("academicId", ""),
            "max_students": supervisor.get("max_students", lecturer.get("max_students", 5)),
            "current_students": student_count,
            "createdAt": supervisor.get("createdAt", lecturer.get("createdAt")),
            "updatedAt": supervisor.get("updatedAt", lecturer.get("updatedAt"))
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

        # compute project student count from fyps collection (use lecturer _id)
        try:
            supervisor_id = created_supervisor.get("supervisor_id") or supervisor_data["supervisor_id"]
            # ensure ObjectId if necessary
            if isinstance(supervisor_id, str):
                supervisor_id = ObjectId(supervisor_id)
            count = await self.db["fyps"].count_documents({"supervisor": supervisor_id})
        except Exception:
            count = 0

        created_supervisor["project_student_count"] = count

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
        count = await self.db["fyps"].count_documents({"supervisor": updated_supervisor.get("lecturer_id")})
        updated_supervisor["project_student_count"] = count

        return updated_supervisor

    async def delete_supervisor(self, supervisor_id: str):
        result = await self.collection.delete_one({"_id": ObjectId(supervisor_id)})

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Supervisor not found")

        return {"message": "Supervisor deleted successfully"}

    async def get_supervisor_with_lecturer(self, supervisor_id: str):
        supervisor = await self.collection.find_one({"_id": ObjectId(supervisor_id)})
        if not supervisor:
            raise HTTPException(status_code=404, detail="Supervisor not found")

        lecturer = await self.db["lecturers"].find_one({"_id": supervisor.get("lecturer_id")})
        if not lecturer:
            raise HTTPException(status_code=404, detail="Lecturer not found")

        return {
            "supervisor": supervisor,
            "lecturer": lecturer
        }

    async def get_supervisor_with_lecturer(self, supervisor_id: str):
        supervisor = await self.get_supervisor_by_id(supervisor_id)

        lecturer = await self.db["lecturers"].find_one({"_id": supervisor["lecturer_id"]})
        if not lecturer:
            raise HTTPException(status_code=404, detail="Lecturer not found")

        return {
            "supervisor": supervisor,
            "lecturer": lecturer
        }

    async def get_all_supervisors_with_lecturer_details(self, limit: int = 10, cursor: Optional[str] = None, academic_year: Optional[str] = None):
        lecturers_query = {}
        if cursor:
            try:
                lecturers_query["_id"] = {"$gt": ObjectId(cursor)}
            except Exception:
                pass

        lecturers = await self.db["lecturers"].find(lecturers_query).limit(limit).to_list(limit)

        checkin_id = None
        if academic_year:
            academic_year_doc = await self.db["academic_years"].find_one({"title": academic_year})
            if academic_year_doc:
                checkin = await self.db["fypcheckins"].find_one({"academicYear": academic_year_doc["_id"]})
                if checkin:
                    checkin_id = checkin["_id"]

        supervisors_with_details = []
        for lecturer in lecturers:
            lecturer_id = lecturer["_id"]
            
            supervisor_doc = await self.collection.find_one({"lecturer_id": lecturer_id})
            
            lecturer_name = f"{lecturer.get('surname', '')} {lecturer.get('otherNames', '')}".strip()
            
            fyp_query = {
                "$or": [
                    {"supervisor": lecturer_id},
                    {"supervisor": str(lecturer_id)}
                ]
            }
            if checkin_id:
                fyp_query["checkin"] = checkin_id
            
            student_count_fyps = await self.db["fyps"].count_documents(fyp_query)
            
            groups = await self.db["groups"].find({
                "$or": [
                    {"supervisor": lecturer_id},
                    {"supervisor": str(lecturer_id)}
                ],
                "status": {"$ne": "inactive"}
            }).to_list(None)
            
            student_count_groups = 0
            for group in groups:
                members = group.get("members", []) or group.get("students", [])
                if members:
                    student_count_groups += len(members)
            
            total_student_count = student_count_fyps + student_count_groups
            
            project_area = None
            lpa = await self.db["lecturer_project_areas"].find_one({"lecturer": lecturer_id})
            if lpa and lpa.get("projectAreas") and len(lpa["projectAreas"]) > 0:
                project_area_id = lpa["projectAreas"][0]
                if isinstance(project_area_id, list):
                    project_area_id = project_area_id[0] if project_area_id else None
                
                if project_area_id:
                    pa_doc = await self.db["project_areas"].find_one({"_id": project_area_id})
                    if pa_doc:
                        project_area = pa_doc.get("title", "")

            supervisor_id = str(supervisor_doc["_id"]) if supervisor_doc else None

            supervisor_with_details = {
                "_id": supervisor_id or str(lecturer_id),
                "lecturer_id": str(lecturer_id),
                "max_students": supervisor_doc.get("max_students", lecturer.get("max_students", 5)) if supervisor_doc else lecturer.get("max_students", 5),
                "project_student_count": total_student_count,
                "createdAt": supervisor_doc.get("createdAt", lecturer.get("createdAt")) if supervisor_doc else lecturer.get("createdAt"),
                "updatedAt": supervisor_doc.get("updatedAt", lecturer.get("updatedAt")) if supervisor_doc else lecturer.get("updatedAt"),
                "lecturer_name": lecturer_name,
                "lecturer_email": lecturer.get("email", ""),
                "lecturer_phone": lecturer.get("phone"),
                "lecturer_position": lecturer.get("position"),
                "lecturer_title": lecturer.get("title", ""),
                "lecturer_bio": lecturer.get("bio"),
                "lecturer_office_hours": lecturer.get("officeHours"),
                "lecturer_office_location": lecturer.get("officeLocation"),
                "lecturer_image": lecturer.get("image"),
                "academic_id": lecturer.get("academicId", ""),
                "lecturer_department": lecturer.get("department", "Computer Science"),
                "lecturer_specialization": project_area or lecturer.get("specialization", "")
            }
            supervisors_with_details.append(supervisor_with_details)

        next_cursor = None
        if len(lecturers) == limit:
            next_cursor = str(lecturers[-1]["_id"])

        return {
            "items": supervisors_with_details,
            "next_cursor": next_cursor
        }

    async def get_lecturer_by_supervisor_id(self, supervisor_id: str):
        supervisor = await self.collection.find_one({"_id": ObjectId(supervisor_id)})
        if not supervisor:
            raise HTTPException(status_code=404, detail="Supervisor not found")

        lecturer = await self.db["lecturers"].find_one({"_id": supervisor.get("lecturer_id")})
        if not lecturer:
            raise HTTPException(status_code=404, detail="Lecturer not found")

        return lecturer

    async def get_supervisors_by_academic_year(self, academic_year_id: str):
        checkin = await self.db["fypcheckins"].find_one({"academicYear": academic_year_id})
        if not checkin:
            return []

        fyps = await self.db["fyps"].find({"checkin": checkin["_id"]}).to_list(None)

        supervisor_ids = list({fyp["supervisor"] for fyp in fyps if fyp.get("supervisor")})

        supervisors = []
        for supervisor_id in supervisor_ids:
            supervisor_doc = await self.collection.find_one({"_id": supervisor_id})
            if not supervisor_doc:
                continue

            lecturer = await self.db["lecturers"].find_one({"_id": supervisor_doc.get("lecturer_id")})
            if not lecturer:
                continue

            student_count = len([fyp for fyp in fyps if fyp.get("supervisor") == supervisor_id])

            supervisors.append({
                "_id": supervisor_doc["_id"],
                "lecturer_id": lecturer["_id"],
                "max_students": supervisor_doc.get("max_students", lecturer.get("max_students")),
                "project_student_count": student_count,
                "createdAt": supervisor_doc.get("createdAt", lecturer.get("createdAt")),
                "updatedAt": supervisor_doc.get("updatedAt", lecturer.get("updatedAt")),
                "academic_id": lecturer.get("academicId"),
            })

        return supervisors

    async def get_supervisors_by_academic_year_detailed(self, academic_year_id: str):
        # Get basic supervisors for this academic year
        supervisors = await self.get_supervisors_by_academic_year(academic_year_id)

        # Get academic year details
        academic_year = await self.db["academic_years"].find_one({"_id": ObjectId(academic_year_id)})

        detailed_supervisors = []
        for supervisor in supervisors:
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
                    "createdAt": supervisor.get("createdAt"),
                    "updatedAt": supervisor.get("updatedAt")
                },
                "lecturer": {
                    "lecturer_id": str(lecturer["_id"]) if lecturer else None,
                    "name": f"{lecturer.get('surname', '')} {lecturer.get('otherNames', '')}".strip() if lecturer else None,
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
                    "createdAt": supervisor.get("createdAt"),
                    "updatedAt": supervisor.get("updatedAt")
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
        """
        Get supervisor details for a specific student by their academic ID
        """

        #  Find the student by academicId
        student = await self.db["students"].find_one({"academicId": student_id})
        if not student:
            raise HTTPException(status_code=404, detail=f"Student {student_id} not found")

        #  Find the most recent FYP assignment for this student
        fyp = await self.db["fyps"].find_one(
            {"student": str(student["_id"])},
            sort=[("createdAt", -1)]
        )
        
        print(fyp)
        if not fyp or not fyp.get("supervisor"):
            raise HTTPException(status_code=404, detail=f"No supervisor assigned to student {student_id}")

        #  Get the supervisor document
        supervisor_doc = await self.db["supervisors"].find_one({"_id": ObjectId(fyp["supervisor"])})
        if not supervisor_doc:
            raise HTTPException(status_code=404, detail="Supervisor record not found")

        #  Ensure the linked lecturer exists
        lecturer = await self.db["lecturers"].find_one({"_id": supervisor_doc["lecturer_id"]})
        if not lecturer:
            raise HTTPException(status_code=404, detail="Lecturer not found for this supervisor")

        #  Count total students supervised by this lecturer
        total_students = await self.db["fyps"].count_documents({"supervisor": supervisor_doc["_id"]})

        #  Get FYP details
        fyp_details = {
            "fyp_id": str(fyp["_id"]),
            "createdAt": fyp.get("createdAt"),
            "updatedAt": fyp.get("updatedAt"),
            "checkin_id": str(fyp["checkin"]) if fyp.get("checkin") else None,
            "project_area_id": str(fyp["projectArea"]) if fyp.get("projectArea") else None
        }

        #  Get project area details (if available)
        project_area = None
        if fyp.get("projectArea"):
            pa = await self.db["project_areas"].find_one({"_id": ObjectId(fyp["projectArea"])})
            if pa:
                project_area = {
                    "project_area_id": str(pa["_id"]),
                    "title": pa.get("title", ""),
                    "description": pa.get("description", ""),
                    "image": pa.get("image", "")
                }

        #  Format supervisor name
        supervisor_name = f"{lecturer.get('surname', '')} {lecturer.get('otherNames', '')}".strip()

        #  Return structured response
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
                "supervisor_id": str(supervisor_doc["_id"]),
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
                "max_students": supervisor_doc.get("max_students", lecturer.get("max_students", 0)),
                "total_students_supervised": total_students,
                "specialization": lecturer.get("specialization", "")
            },
            "assignment": fyp_details,
            "project_area": project_area
        }
