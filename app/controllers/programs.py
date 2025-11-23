from datetime import datetime
from typing import Optional, List, Dict
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException


class ProgramController:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db["programs"]

    async def get_all_programs(self, limit: int = 10, cursor: Optional[str] = None):
        query = {}
        if cursor:
            query["_id"] = {"$gt": ObjectId(cursor)}

        programs = await self.collection.find(query).limit(limit).to_list(limit)

        next_cursor = None
        if len(programs) == limit:
            next_cursor = str(programs[-1]["_id"])

        return {
            "items": programs,
            "next_cursor": next_cursor
        }

    async def get_program_by_id(self, program_id: str):
        program = await self.collection.find_one({"_id": ObjectId(program_id)})
        if not program:
            raise HTTPException(status_code=404, detail="Program not found")
        return program

    async def create_program(self, program_data: dict):
        program_data["createdAt"] = datetime.now()
        program_data["updatedAt"] = datetime.now()

        result = await self.collection.insert_one(program_data)
        created_program = await self.collection.find_one({"_id": result.inserted_id})
        return created_program

    async def update_program(self, program_id: str, update_data: dict):
        update_data = {k: v for k, v in update_data.items() if v is not None}

        if not update_data:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        update_data["updatedAt"] = datetime.now()

        result = await self.collection.update_one(
            {"_id": ObjectId(program_id)},
            {"$set": update_data}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Program not found")

        updated_program = await self.collection.find_one({"_id": ObjectId(program_id)})
        return updated_program

    async def delete_program(self, program_id: str):
        result = await self.collection.delete_one({"_id": ObjectId(program_id)})

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Program not found")

        return {"message": "Program deleted successfully"}

    async def search_programs_by_title(self, title: str):
        programs = await self.collection.find(
            {"title": {"$regex": title, "$options": "i"}}
        ).to_list(None)
        return programs

    
    async def get_all_student_dashboard(self):
        """
        Return dashboard summary for all students.
        Each item has the same shape as get_student_dashboard:
        { student_id, student_image, program, progress_status }
        """
        students = await self.db["students"].find({"deleted": {"$ne": True}}).to_list(None)

        out = []
        for student in students:
            # resolve program (title stored or ObjectId)
            program = None
            if student.get("program"):
                try:
                    program = await self.collection.find_one({"_id": ObjectId(student["program"])})
                except Exception:
                    program = await self.collection.find_one({"title": student["program"]})

            # find latest FYP for the student (handle ObjectId or string storage)
            fyp = await self.db["fyps"].find_one(
                {"$or": [{"student": student["_id"]}, {"student": str(student["_id"])}]},
                sort=[("createdAt", -1)]
            )

            progress_status = "not_started"
            if fyp:
                # explicit completion signals
                status_val = (fyp.get("status") or "").lower()
                completed_statuses = {"completed", "finished", "approved", "graded", "passed"}
                has_final_submission = bool(fyp.get("finalSubmission") or fyp.get("submitted") or fyp.get("final_submission"))
                has_grade = fyp.get("grade") is not None
                defence_done = bool(
                    fyp.get("defenceCompleted")
                    or (isinstance(fyp.get("defence"), dict) and fyp["defence"].get("status") in ["completed", "done"])
                )

                is_completed = (
                    (status_val in completed_statuses)
                    or has_final_submission
                    or has_grade
                    or defence_done
                )

                if is_completed:
                    progress_status = "completed"
                else:
                    # fallback to checkin active or presence of fyp -> in_progress
                    checkin = None
                    if fyp.get("checkin"):
                        try:
                            checkin = await self.db["fypcheckins"].find_one({"_id": ObjectId(fyp["checkin"])})
                        except Exception:
                            checkin = await self.db["fypcheckins"].find_one({"_id": fyp["checkin"]})
                    if checkin and (checkin.get("active") or checkin.get("status") == "active"):
                        progress_status = "in_progress"
                    else:
                        progress_status = "in_progress"

            out.append({
                "student_id": str(student["_id"]),
                "student_image": student.get("image", ""),
                "program": program,
                "progress_status": progress_status
            })

        return out
    
    
    async def get_student_dashboard(self, student_id: str):
        # Get student details
        # student = await self.db["students"].find_one({"_id": ObjectId(student_id)})
        student = await self.db["students"].find_one({"academicId": student_id})
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

        # Get program details
        program = None
        if student.get("program"):
            program = await self.collection.find_one({"title": student["program"]})

        # Get FYP details to determine progress
        # fyp = await self.db["fyps"].find_one({"student": ObjectId(student_id)})
        fyp = await self.db["fyps"].find_one({"student": str(student["_id"])})

        progress_status = "not_started"
        if fyp:
            # Get checkin details
            checkin = await self.db["fypcheckins"].find_one({"_id": ObjectId(fyp["checkin"])})
            if checkin and checkin.get("checkin") and checkin.get("active"):
                progress_status = "in_progress"

        return {
            "student_id": str(student["_id"]),
            "student_image": student.get("image", ""),
            "program": program,
            "progress_status": progress_status
        }
        
