from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException


class SupervisorController:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db["supervisors"]

    async def get_all_supervisors(self, limit: int = 10, cursor: str | None = None):
        # Use the dedicated supervisors collection with aggregation to get lecturer details
        skip_count = int(cursor) if cursor else 0
        
        pipeline = [
            {"$skip": skip_count},
            {"$limit": limit + 1},  # Get one extra to check if there's a next page
            {
                "$lookup": {
                    "from": "lecturers",
                    "localField": "lecturer_id",
                    "foreignField": "_id",
                    "as": "lecturer"
                }
            },
            {"$unwind": "$lecturer"},
            {
                "$match": {
                    "lecturer.deleted": {"$ne": True}
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "lecturer_id": 1,
                    "max_students": 1,
                    "project_student_count": 1,
                    "createdAt": 1,
                    "updatedAt": 1,
                    "academic_id": "$lecturer.academicId"
                }
            }
        ]
        
        supervisors = await self.collection.aggregate(pipeline).to_list(length=limit + 1)
        
        # Check if there's a next page
        next_cursor = None
        if len(supervisors) > limit:
            supervisors = supervisors[:limit]  # Remove the extra item
            next_cursor = str(skip_count + limit)

        return {
            "items": supervisors,
            "next_cursor": next_cursor
        }

    async def get_supervisor_by_id(self, supervisor_id: str):
        # Get supervisor from the dedicated supervisors collection
        pipeline = [
            {"$match": {"_id": ObjectId(supervisor_id)}},
            {
                "$lookup": {
                    "from": "lecturers",
                    "localField": "lecturer_id",
                    "foreignField": "_id",
                    "as": "lecturer"
                }
            },
            {"$unwind": "$lecturer"},
            {
                "$match": {
                    "lecturer.deleted": {"$ne": True}
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "lecturer_id": 1,
                    "max_students": 1,
                    "project_student_count": 1,
                    "createdAt": 1,
                    "updatedAt": 1,
                    "academic_id": "$lecturer.academicId"
                }
            }
        ]
        
        result = await self.collection.aggregate(pipeline).to_list(length=1)
        if not result:
            raise HTTPException(status_code=404, detail="Supervisor not found")
        
        return result[0]

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
        if created_supervisor:
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
        if updated_supervisor:
            count = await self.db["fyps"].count_documents({"supervisor": updated_supervisor["lecturer_id"]})
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
        # Use the dedicated supervisors collection with aggregation to get full lecturer details
        skip_count = int(cursor) if cursor else 0
        
        pipeline = [
            {"$skip": skip_count},
            {"$limit": limit + 1},  # Get one extra to check if there's a next page
            {
                "$lookup": {
                    "from": "lecturers",
                    "localField": "lecturer_id",
                    "foreignField": "_id",
                    "as": "lecturer"
                }
            },
            {"$unwind": "$lecturer"},
            {
                "$match": {
                    "lecturer.deleted": {"$ne": True}
                }
            },
            {
                "$project": {
                    "_id": {"$toString": "$_id"},
                    "lecturer_id": {"$toString": "$lecturer_id"},
                    "max_students": 1,
                    "project_student_count": 1,
                    "createdAt": 1,
                    "updatedAt": 1,
                    "lecturer_name": {
                        "$trim": {
                            "input": {
                                "$concat": [
                                    {"$ifNull": ["$lecturer.surname", ""]},
                                    " ",
                                    {"$ifNull": ["$lecturer.otherNames", ""]}
                                ]
                            }
                        }
                    },
                    "lecturer_email": "$lecturer.email",
                    "lecturer_phone": "$lecturer.phone",
                    "lecturer_position": "$lecturer.position",
                    "lecturer_title": "$lecturer.title",
                    "lecturer_bio": "$lecturer.bio",
                    "lecturer_office_hours": "$lecturer.officeHours",
                    "lecturer_office_location": "$lecturer.officeLocation",
                    "academic_id": "$lecturer.academicId"
                }
            }
        ]
        
        supervisors_with_details = await self.collection.aggregate(pipeline).to_list(length=limit + 1)
        
        # Check if there's a next page
        next_cursor = None
        if len(supervisors_with_details) > limit:
            supervisors_with_details = supervisors_with_details[:limit]  # Remove the extra item
            next_cursor = str(skip_count + limit)

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