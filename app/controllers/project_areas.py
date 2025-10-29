from datetime import datetime

from bson import ObjectId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase


class ProjectAreaController:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db["project_areas"]

    async def get_all_project_areas(self, limit: int = 10, cursor: str | None = None):
        query = {}
        if cursor:
            query["_id"] = {"$gt": ObjectId(cursor)}

        project_areas = await self.collection.find(query).limit(limit).to_list(limit)

        # Add interested staff count for each project area
        for project_area in project_areas:
            interested_staff = project_area.get("interested_staff", [])
            project_area["interested_staff_count"] = len(interested_staff)

        next_cursor = None
        if len(project_areas) == limit:
            next_cursor = str(project_areas[-1]["_id"])

        return {
            "items": project_areas,
            "next_cursor": next_cursor
        }

    async def get_project_area_by_id(self, project_area_id: str):
        project_area = await self.collection.find_one({"_id": ObjectId(project_area_id)})
        if not project_area:
            raise HTTPException(status_code=404, detail="Project area not found")

        # Add interested staff count
        interested_staff = project_area.get("interested_staff", [])
        project_area["interested_staff_count"] = len(interested_staff)

        return project_area

    async def create_project_area(self, project_area_data: dict):
        # Convert interested_staff to ObjectIds if they're strings
        if "interested_staff" in project_area_data:
            project_area_data["interested_staff"] = [
                ObjectId(staff_id) if isinstance(staff_id, str) else staff_id
                for staff_id in project_area_data["interested_staff"]
            ]

        project_area_data["createdAt"] = datetime.now()
        project_area_data["updatedAt"] = datetime.now()

        result = await self.collection.insert_one(project_area_data)
        created_project_area = await self.collection.find_one({"_id": result.inserted_id})

        # Add interested staff count
        interested_staff = created_project_area.get("interested_staff", [])
        created_project_area["interested_staff_count"] = len(interested_staff)

        return created_project_area

    async def update_project_area(self, project_area_id: str, update_data: dict):
        update_data = {k: v for k, v in update_data.items() if v is not None}

        if not update_data:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        # Convert interested_staff to ObjectIds if they're strings
        if "interested_staff" in update_data:
            update_data["interested_staff"] = [
                ObjectId(staff_id) if isinstance(staff_id, str) else staff_id
                for staff_id in update_data["interested_staff"]
            ]

        update_data["updatedAt"] = datetime.now()

        result = await self.collection.update_one(
            {"_id": ObjectId(project_area_id)},
            {"$set": update_data}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Project area not found")

        updated_project_area = await self.collection.find_one({"_id": ObjectId(project_area_id)})

        # Add interested staff count
        interested_staff = updated_project_area.get("interested_staff", [])
        updated_project_area["interested_staff_count"] = len(interested_staff)

        return updated_project_area

    async def delete_project_area(self, project_area_id: str):
        result = await self.collection.delete_one({"_id": ObjectId(project_area_id)})

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Project area not found")

        return {"message": "Project area deleted successfully"}

    async def search_project_areas_by_title(self, title: str):
        project_areas = await self.collection.find(
            {"title": {"$regex": title, "$options": "i"}}
        ).to_list(None)
        return project_areas


    async def get_all_project_area_with_interested_lecturers(self):
        # Fetch all project areas
        project_areas = await self.collection.find({}).to_list(None)

        for project_area in project_areas:
            lecturer_ids = project_area.get("interested_staff", [])
            detailed_lecturers = []

            for lecturer_id in lecturer_ids:
                # Convert to ObjectId safely
                try:
                    lecturer_obj_id = ObjectId(lecturer_id)
                except Exception:
                    continue  # skip invalid IDs

                lecturer = await self.db["lecturers"].find_one({"_id": lecturer_obj_id})
                if lecturer:
                    detailed_lecturers.append({
                        "lecturer_id": str(lecturer["_id"]),
                        "name": f"{lecturer.get('surname', '')} {lecturer.get('otherNames', '')}".strip(),
                        "email": lecturer.get("email", ""),
                        "department": lecturer.get("department", ""),
                        "title": lecturer.get("title", ""),
                        "specialization": lecturer.get("specialization", "")
                    })

            # Replace with enriched lecturer list
            project_area["interested_staff"] = detailed_lecturers
            project_area["interested_staff_count"] = len(detailed_lecturers)

            # Optional: ensure consistent string IDs for _id fields
            project_area["_id"] = str(project_area["_id"])

        return {"project_areas": project_areas}


   
    async def get_project_area_with_interested_lecturers(self, project_area_id: str):
        try:
            pa_oid = ObjectId(project_area_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid project area id")

        project_area = await self.collection.find_one({"_id": pa_oid})
        if not project_area:
            raise HTTPException(status_code=404, detail="Project area not found")

        lecturer_ids = project_area.get("interested_staff", []) or []
        detailed_lecturers = []

        for lecturer_id in lecturer_ids:
            # try to normalize to ObjectId, skip if impossible
            try:
                lid = lecturer_id if isinstance(lecturer_id, ObjectId) else ObjectId(lecturer_id)
            except Exception:
                # skip non-id values
                continue

            lecturer = await self.db["lecturers"].find_one({"_id": lid})
            if not lecturer:
                continue

            detailed_lecturers.append({
                "lecturer_id": str(lecturer["_id"]),
                "name": f"{lecturer.get('title','').strip()} {lecturer.get('surname','')} {lecturer.get('otherNames','')}".strip(),
                "email": lecturer.get("email", ""),
                "department": lecturer.get("department", "Computer Science"),
                "title": lecturer.get("title", ""),
                "specialization": lecturer.get("specialization", ""),
                "academicId": lecturer.get("academicId", "")
            })

        # Replace interested_staff with enriched list and set counts/ids consistently
        project_area["interested_staff"] = detailed_lecturers
        project_area["interested_staff_count"] = len(detailed_lecturers)
        project_area["id"] = str(project_area["_id"])
        project_area["_id"] = str(project_area["_id"])

        return {
            "project_area": project_area,
            "lecturers": detailed_lecturers
        }
        

    async def add_interested_lecturer(self, project_area_id: str, lecturer_id: str):
        # Check if lecturer exists
        lecturer = await self.db["lecturers"].find_one({"_id": ObjectId(lecturer_id)})
        if not lecturer:
            raise HTTPException(status_code=404, detail="Lecturer not found")

        # Check if lecturer is already interested
        project_area = await self.collection.find_one({"_id": ObjectId(project_area_id)})
        if not project_area:
            raise HTTPException(status_code=404, detail="Project area not found")

        interested_staff = project_area.get("interested_staff", [])
        if ObjectId(lecturer_id) in interested_staff:
            raise HTTPException(status_code=400, detail="Lecturer is already interested in this project area")

        # Add lecturer to interested staff
        result = await self.collection.update_one(
            {"_id": ObjectId(project_area_id)},
            {
                "$push": {"interested_staff": ObjectId(lecturer_id)},
                "$set": {"updatedAt": datetime.now()}
            }
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Project area not found")

        updated_project_area = await self.collection.find_one({"_id": ObjectId(project_area_id)})
        interested_staff = updated_project_area.get("interested_staff", [])
        updated_project_area["interested_staff_count"] = len(interested_staff)

        return updated_project_area

    async def remove_interested_lecturer(self, project_area_id: str, lecturer_id: str):
        result = await self.collection.update_one(
            {"_id": ObjectId(project_area_id)},
            {
                "$pull": {"interested_staff": ObjectId(lecturer_id)},
                "$set": {"updatedAt": datetime.now()}
            }
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Project area not found")

        updated_project_area = await self.collection.find_one({"_id": ObjectId(project_area_id)})
        interested_staff = updated_project_area.get("interested_staff", [])
        updated_project_area["interested_staff_count"] = len(interested_staff)

        return updated_project_area
