from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException

import os
import shutil
from fastapi import UploadFile
from datetime import datetime

UPLOAD_DIR = "uploads/submissions"
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024  # 10MB
class SubmissionController:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db["submissions"]
        self.submission_files_collection = db["submission_files"]

    async def get_all_submissions(self, limit: int = 10, cursor: str | None = None):
        query = {}
        if cursor:
            query["_id"] = {"$gt": ObjectId(cursor)}

        submissions = await self.collection.find(query).sort("createdAt", -1).limit(limit).to_list(limit)

        next_cursor = None
        if len(submissions) == limit:
            next_cursor = str(submissions[-1]["_id"])

        return {
            "items": submissions,
            "next_cursor": next_cursor
        }

    async def get_submission_by_id(self, submission_id: str):
        submission = await self.collection.find_one({"_id": ObjectId(submission_id)})
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")
        return submission

    async def create_submission(self, submission_data: dict):
        # ----------------------------------------------------
        # 1. Convert IDs to ObjectId
        # ----------------------------------------------------
        if "deliverable_id" in submission_data and isinstance(submission_data["deliverable_id"], str):
            submission_data["deliverable_id"] = ObjectId(submission_data["deliverable_id"])

        if "group_id" in submission_data and isinstance(submission_data["group_id"], str):
            submission_data["group_id"] = ObjectId(submission_data["group_id"])

        if "project_id" in submission_data and isinstance(submission_data["project_id"], str):
            submission_data["project_id"] = ObjectId(submission_data["project_id"])

        # ----------------------------------------------------
        # 2. Prevent duplicate submissions from the same group
        # ----------------------------------------------------
        existing_submission = await self.collection.find_one({
            "deliverable_id": submission_data["deliverable_id"],
            "group_id": submission_data["group_id"]
        })

        if existing_submission:
            raise HTTPException(
                status_code=400,
                detail="This group has already submitted for this deliverable"
            )

        # ----------------------------------------------------
        # 3. Setup timestamps
        # ----------------------------------------------------
        now = datetime.utcnow()

        submission_data["submitted_at"] = now
        submission_data["created_at"] = now
        submission_data["updated_at"] = now

        # Group submissions do not use attempt_number
        submission_data["file_count"] = submission_data.get("file_count", 0)

        # ----------------------------------------------------
        # 4. Insert submission
        # ----------------------------------------------------
        result = await self.collection.insert_one(submission_data)

        created_submission = await self.collection.find_one({"_id": result.inserted_id})

        return {
            "data": created_submission,
            "message": "Submission created successfully"
        }
    
    async def review_submission(self, submission_id: str, approved: bool, feedback: str = None):
        submission = await self.get_submission_by_id(submission_id)
        
        if approved:
            submission.status = "approved"
            submission.lecturer_feedback = feedback
            submission.updatedAt = datetime.now()
            await self.collection.replace_one({"_id": ObjectId(submission_id)}, submission)
        else:
            submission.status = "changes_requested"
            submission.lecturer_feedback = feedback
            submission.updatedAt = datetime.now()
            await self.collection.replace_one({"_id": ObjectId(submission_id)}, submission)
            
        
        return {"data": submission, "message": "Submission reviewed successfully"}
    
    
    async def save_new_file(submission_id: str, file: UploadFile) -> dict:
        """
        Saves file locally, enforces size limit, returns metadata.
        """

        # ---------------- SIZE CHECK ----------------
        file.file.seek(0, os.SEEK_END)   # Move cursor to end of file
        file_size = file.file.tell()
        file.file.seek(0)                # Reset cursor to beginning

        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Max size is {MAX_FILE_SIZE_MB}MB"
            )

        # ---------------- FOLDER SETUP ----------------
        submission_folder = os.path.join(UPLOAD_DIR, str(submission_id))
        os.makedirs(submission_folder, exist_ok=True)

        # ---------------- FILENAME ----------------
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        ext = os.path.splitext(file.filename)[1]
        new_filename = f"{timestamp}{ext}"
        file_path = os.path.join(submission_folder, new_filename)

        # ---------------- SAVE FILE ----------------
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # ---------------- METADATA ----------------
        file_data = {
            "submission_id": submission_id,
            "file_name": new_filename,
            "file_path": file_path,
            "file_type": file.content_type,
            "file_size": file_size,
        }

        return file_data
    
        
    async def resubmit_submission(self, submission_id: str, file: UploadFile):
        submission = await self.get_submission_by_id(submission_id)

        if submission.status != "changes_requested":
            raise HTTPException(status_code=400, detail="Submission is not eligible for resubmission")
        

        # Save file and get metadata
        file_data = await self.save_new_file(submission_id, file)

        # Insert into SubmissionFile collection
        await self.submission_files_collection.insert_one(file_data)

        # Update submission
        await self.collection.update_one(
            {"_id": ObjectId(submission_id)},
            {
                "$set": {
                    "status": "PENDING_REVIEW",
                    "lecturer_feedback": None
                },
                "$inc": {
                    "attempt_number": 1
                }
            }
        )

        return {"message": "Resubmission successful"}

        
    async def update_submission(self, submission_id: str, update_data: dict):
        update_data = {k: v for k, v in update_data.items() if v is not None}

        if not update_data:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        update_data["updatedAt"] = datetime.now()

        result = await self.collection.update_one(
            {"_id": ObjectId(submission_id)},
            {"$set": update_data}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Submission not found")

        updated_submission = await self.collection.find_one({"_id": ObjectId(submission_id)})
        return updated_submission


    async def delete_submission(self, submission_id: str):
        result = await self.collection.delete_one({"_id": ObjectId(submission_id)})

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Submission not found")

        return {"message": "Submission deleted successfully"}

    async def get_submissions_by_deliverable(self, deliverable_id: str):
        submissions = await self.collection.find(
            {"deliverable_id": ObjectId(deliverable_id)}
        ).sort("createdAt", -1).to_list(None)
        return submissions


    async def get_submissions_by_student(self, student_id: str):
        submissions = await self.collection.find(
            {"student_id": ObjectId(student_id)}
        ).sort("createdAt", -1).to_list(None)
        return submissions

    async def get_students_who_submitted_to_deliverable(self, deliverable_id: str):
        # Get all submissions for this deliverable
        submissions = await self.collection.find(
            {"deliverable_id": ObjectId(deliverable_id)}
        ).sort("createdAt", -1).to_list(None)

        student_submissions = []
        for submission in submissions:
            # Get student details
            student = await self.db["students"].find_one({"_id": submission["student_id"]})
            if student:
                # Combine student name from surname and otherNames
                student_name = f"{student.get('surname', '')} {student.get('otherNames', '')}".strip()

                student_info = {
                    "student_id": str(student["_id"]),
                    "student_name": student_name,
                    "student_email": student.get("email", ""),
                    "student_image": student.get("image", ""),
                    "submission": submission,
                    "submission_status": submission.get("status", "pending_review")
                }
                student_submissions.append(student_info)

        return student_submissions

    async def check_student_submission_status(self, deliverable_id: str, student_id: str):
        submission = await self.collection.find_one({
            "deliverable_id": ObjectId(deliverable_id),
            "student_id": ObjectId(student_id)
        })

        return {
            "has_submitted": submission is not None,
            "submission": submission if submission else None
        }

    async def get_submission_details_with_group_and_files(self, submission_id: str):
        # Get submission
        submission = await self.collection.find_one({"_id": ObjectId(submission_id)})
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")

        # Get group details
        group = await self.db["groups"].find_one({"_id": submission["group_id"]})
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")

        # Get students with their details
        students = []
        for student_id in group.get("student_ids", []):
            student = await self.db["students"].find_one({"_id": student_id})
            if student:
                # Get program details
                program = None
                if student.get("program"):
                    program = await self.db["programs"].find_one({"_id": student["program"]})

                student_name = f"{student.get('surname', '')} {student.get('otherNames', '')}".strip()
                students.append({
                    "student_id": str(student["_id"]),
                    "student_name": student_name,
                    "student_email": student.get("email", ""),
                    "student_image": student.get("image", ""),
                    "program": program
                })

        # Get files for this submission
        files = await self.db["submission_files"].find(
            {"submission_id": ObjectId(submission_id)}
        ).sort("createdAt", -1).to_list(None)

        # Add uploader details to each file
        for file in files:
            uploader = await self.db["students"].find_one({"_id": file["uploaded_by"]})
            if uploader:
                uploader_name = f"{uploader.get('surname', '')} {uploader.get('otherNames', '')}".strip()
                file["uploader_name"] = uploader_name

        # Count files for submission
        submission["file_count"] = len(files)

        return {
            "submission": submission,
            "group": {
                "group_id": str(group["_id"]),
                "group_name": group.get("name", ""),
                "group_description": group.get("description", ""),
                "student_count": len(group.get("student_ids", []))
            },
            "students": students,
            "files": files
        }

    async def get_groups_who_submitted_to_deliverable(self, deliverable_id: str):
        # Get deliverable details
        deliverable = await self.db["deliverables"].find_one({"_id": ObjectId(deliverable_id)})
        if not deliverable:
            raise HTTPException(status_code=404, detail="Deliverable not found")

        # Get all submissions for this deliverable
        submissions = await self.collection.find(
            {"deliverable_id": ObjectId(deliverable_id)}
        ).sort("createdAt", -1).to_list(None)

        group_submissions = []
        for submission in submissions:
            # Get group details
            group = await self.db["groups"].find_one({"_id": submission["group_id"]})
            if group:
                # Get files for this submission
                files = await self.db["submission_files"].find(
                    {"submission_id": submission["_id"]}
                ).sort("createdAt", -1).to_list(None)

                # Get the most recent file if any
                latest_file = files[0] if files else None

                group_info = {
                    "deliverable_name": deliverable.get("title", ""),
                    "group_id": str(group["_id"]),
                    "group_name": group.get("name", ""),
                    "group_description": group.get("description", ""),
                    "student_count": len(group.get("student_ids", [])),
                    "submission": {
                        "submission_id": str(submission["_id"]),
                        "status": submission.get("status", "in_progress"),
                        "comments": submission.get("comments", ""),
                        "submitted_at": submission.get("createdAt"),
                        "updated_at": submission.get("updatedAt"),
                        "file_count": len(files)
                    },
                    "latest_file": {
                        "file_name": latest_file.get("file_name", "") if latest_file else None,
                        "file_path": latest_file.get("file_path", "") if latest_file else None,
                        "file_status": latest_file.get("status", "") if latest_file else None,
                        "uploaded_at": latest_file.get("createdAt") if latest_file else None
                    } if latest_file else None
                }
                group_submissions.append(group_info)

        return group_submissions

    async def get_submission_details_with_group_and_files_by_group(self, group_id: str):
        # Get group details first
        group = await self.db["groups"].find_one({"_id": ObjectId(group_id)})
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")

        # Get the most recent submission for this group
        submission = await self.collection.find_one(
            {"group_id": ObjectId(group_id)}
        )
        if not submission:
            raise HTTPException(status_code=404, detail="No submission found for this group")

        # Get students with their details
        students = []
        for student_id in group.get("student_ids", []):
            student = await self.db["students"].find_one({"_id": student_id})
            if student:
                # Get program details
                program = None
                if student.get("program"):
                    program = await self.db["programs"].find_one({"_id": student["program"]})

                student_name = f"{student.get('surname', '')} {student.get('otherNames', '')}".strip()
                students.append({
                    "student_id": str(student["_id"]),
                    "student_name": student_name,
                    "student_email": student.get("email", ""),
                    "student_image": student.get("image", ""),
                    "program": program
                })

        # Get files for this submission
        files = await self.db["submission_files"].find(
            {"submission_id": submission["_id"]}
        ).sort("createdAt", -1).to_list(None)

        # Add uploader details to each file
        for file in files:
            uploader = await self.db["students"].find_one({"_id": file["uploaded_by"]})
            if uploader:
                uploader_name = f"{uploader.get('surname', '')} {uploader.get('otherNames', '')}".strip()
                file["uploader_name"] = uploader_name

        # Count files for submission
        submission["file_count"] = len(files)

        return {
            "submission": submission,
            "group": {
                "group_id": str(group["_id"]),
                "group_name": group.get("name", ""),
                "group_description": group.get("description", ""),
                "student_count": len(group.get("student_ids", []))
            },
            "students": students,
            "files": files
        }


