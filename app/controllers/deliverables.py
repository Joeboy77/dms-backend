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
        # Find supervisor in supervisors collection and get associated lecturer
        if "supervisor_id" in deliverable_data:
            try:
                supervisor_id = (
                    ObjectId(deliverable_data["supervisor_id"])
                    if isinstance(deliverable_data["supervisor_id"], str)
                    else deliverable_data["supervisor_id"]
                )
                
                # Find supervisor and their associated lecturer
                supervisor = await self.db["supervisors"].find_one({"_id": ObjectId(supervisor_id)})
                if not supervisor:
                    raise HTTPException(status_code=404, detail="Supervisor not found")
                
                # Get lecturer details - this is the actual supervisor_id we'll store
                lecturer = await self.db["lecturers"].find_one({"_id": supervisor["lecturer_id"]})
                if not lecturer:
                    raise HTTPException(status_code=404, detail="Associated lecturer not found")

                # Store supervisor._id as supervisor_id in deliverable
                deliverable_data["supervisor_id"] = supervisor["_id"]
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid supervisor_id format or not found: {str(e)}")

        # Auto-populate group_ids if not provided
        if not deliverable_data.get("group_ids"):
            supervisor_id = deliverable_data["supervisor_id"]

            # Get all FYPs for this supervisor
            fyps = await self.db["fyps"].find({
                "$or": [
                    {"supervisor": supervisor_id},
                    {"supervisor": str(supervisor_id)}
                ]
            }).to_list(None)
            
            print(f"Found {len(fyps)} FYPs for supervisor {supervisor_id}")

            # Only include students that actually exist
            group_ids = []
            for fyp in fyps:
                if fyp.get("group"):
                    # Verify group exists
                    group = await self.db["groups"].find_one({
                        "$or": [
                            {"_id": ObjectId(fyp["group"])},
                            {"_id": fyp["group"]}
                        ]
                    })
                    if group:
                        group_ids.append(group["_id"])
            deliverable_data["group_ids"] = group_ids
        else:
            # Convert group_ids to ObjectIds
            group_ids = []
            for group_id in deliverable_data["group_ids"]:
                try:
                    group_ids.append(
                        ObjectId(group_id)
                        if isinstance(group_id, str)
                        else group_id
                    )
                except Exception:
                    continue
            deliverable_data["group_ids"] = group_ids
        # Add timestamps and initialize submissions count
        deliverable_data["createdAt"] = datetime.now()
        deliverable_data["updatedAt"] = datetime.now()
        deliverable_data["total_submissions"] = 0

        # Insert and return
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


    async def get_deliverables_for_student(self, student_id: str):
        """Get all deliverables for a specific student"""

        # 1. Find the student
        student = await self.db["students"].find_one({"academicId": student_id})
        if not student:
            raise HTTPException(404, f"Student {student_id} not found")

        student_oid = student["_id"]

        # 2. Find group(s) the student belongs to
        groups = await self.db["groups"].find({
            "students": {"$in": [student_oid, str(student_oid)]}
        }).to_list(None)

        group_oid = None
        if groups:
            group_oid = groups[0]["_id"]

        # 3. Find FYP for this student
        fyp_query = {
            "$or": [
                {"student": student_oid},
                {"student": str(student_oid)}
            ]
        }

        # include group FYPs if group exists
        if group_oid:
            fyp_query["$or"].append({"group": group_oid})
            fyp_query["$or"].append({"group": str(group_oid)})

        fyp = await self.db["fyps"].find_one(fyp_query, sort=[("createdAt", -1)])
        if not fyp:
            raise HTTPException(404, f"No FYP found for student {student_id}")

        # 4. Resolve supervisor
        supervisor = None
        if fyp.get("supervisor"):
            try:
                supervisor = await self.db["supervisors"].find_one({"_id": ObjectId(fyp["supervisor"])})
            except:
                supervisor = await self.db["supervisors"].find_one({"_id": fyp["supervisor"]})

        lecturer = None
        if supervisor:
            lecturer = await self.db["lecturers"].find_one({"_id": supervisor["lecturer_id"]})

        # 5. Build deliverables query
        deliverables_query = {
            "$or": []
        }

        # supervisor-based deliverables
        if supervisor:
            deliverables_query["$or"].append({"supervisor_id": supervisor["_id"]})
            deliverables_query["$or"].append({"supervisor_id": str(supervisor["_id"])})

        # group deliverables
        if group_oid:
            deliverables_query["$or"].append({"group_ids": {"$in": [group_oid, str(group_oid)]}})

        # ENFORCE at least one query
        if not deliverables_query["$or"]:
            deliverables_query["$or"].append({"_id": None})  # forces empty result, avoids crash

        # 6. Fetch deliverables
        deliverables = await self.collection.find(deliverables_query).sort("start_date", -1).to_list(None)

        # 7. Enrich with submissions
        for deliverable in deliverables:
            # Total submissions
            total = await self.db["submissions"].count_documents({"deliverable_id": deliverable["_id"]})
            deliverable["total_submissions"] = total

            # Student submission
            student_sub = await self.db["submissions"].find_one({
                "deliverable_id": deliverable["_id"],
                "$or": [
                    {"student_id": student_oid},
                    {"student_id": str(student_oid)}
                ]
            })

            deliverable["student_submitted"] = student_sub is not None
            if student_sub:
                deliverable["student_submission_date"] = student_sub.get("submitted_at")
                deliverable["student_submission_id"] = str(student_sub["_id"])

        # 8. Build response
        student_info = {
            "student_id": str(student_oid),
            "academic_id": student.get("academicId"),
            "student_name": f"{student.get('surname', '')} {student.get('otherNames', '')}".strip(),
            "email": student.get("email", "")
        }

        supervisor_info = {}
        if lecturer and supervisor:
            supervisor_info = {
                "lecturer_id": str(lecturer["_id"]),
                "supervisor_id": str(supervisor["_id"]),
                "academic_id": lecturer.get("academicId"),
                "title": lecturer.get("title"),
                "name": f"{lecturer.get('surname', '')} {lecturer.get('otherNames', '')}".strip(),
                "email": lecturer.get("email", ""),
                "position": lecturer.get("position", ""),
                "department": lecturer.get("department", "Computer Science")
            }

        return {
            "student": student_info,
            "supervisor": supervisor_info,
            "deliverables": convert_objectid_to_str(deliverables),
            "total_deliverables": len(deliverables)
        }
