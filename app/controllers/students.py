from datetime import datetime

from bson import ObjectId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase


class StudentController:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db["students"]

    async def get_all_students(self, limit: int = 10, cursor: str | None = None):
        query = {}
        if cursor:
            query["_id"] = {"$gt": ObjectId(cursor)}

        students = await self.collection.find(query).limit(limit).to_list(limit)

        next_cursor = None
        if len(students) == limit:
            next_cursor = str(students[-1]["_id"])

        return {"items": students, "next_cursor": next_cursor}

    async def get_student_by_id(self, student_id: str):
        student = await self.collection.find_one({"_id": ObjectId(student_id)})
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        return student

    async def create_student(self, student_data: dict):
        student_data["created_at"] = datetime.now()
        student_data["updated_at"] = None

        # Check if student_id already exists
        existing_student = await self.collection.find_one(
            {"student_id": student_data["student_id"]}
        )
        if existing_student:
            raise HTTPException(status_code=400, detail="Student ID already exists")

        result = await self.collection.insert_one(student_data)
        created_student = await self.collection.find_one({"_id": result.inserted_id})
        return created_student

    async def update_student(self, student_id: str, update_data: dict):
        # Remove None values from update_data
        update_data = {k: v for k, v in update_data.items() if v is not None}

        if not update_data:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        update_data["updated_at"] = datetime.now()

        result = await self.collection.update_one(
            {"_id": ObjectId(student_id)}, {"$set": update_data}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Student not found")

        updated_student = await self.collection.find_one({"_id": ObjectId(student_id)})
        return updated_student

    async def delete_student(self, student_id: str):
        result = await self.collection.delete_one({"_id": ObjectId(student_id)})

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Student not found")

        return {"message": "Student deleted successfully"}

    async def get_students_by_major(self, major: str):
        students = await self.collection.find({"major": major}).to_list(None)
        return students

    async def get_students_by_year(self, year: int):
        students = await self.collection.find({"year": year}).to_list(None)
        return students

    async def get_total_student_count(self):
        count = await self.collection.count_documents({})
        return {"total_students": count}

    async def get_students_by_project_area(self, project_area_id: str):
        # Get all FYPs that use this project area
        fyps = (
            await self.db["fyps"]
            .find({"projectArea": ObjectId(project_area_id)})
            .to_list(None)
        )

        students_data = []
        for fyp in fyps:
            # Get student details
            student = await self.collection.find_one({"_id": fyp["student"]})
            if student:
                # Get program details
                program = None
                if student.get("program"):
                    program = await self.db["programs"].find_one(
                        {"_id": student["program"]}
                    )

                # Get supervisor details
                supervisor = None
                if fyp.get("supervisor"):
                    supervisor = await self.db["lecturers"].find_one(
                        {"_id": fyp["supervisor"]}
                    )

                student_name = f"{student.get('surname', '')} {student.get('otherNames', '')}".strip()

                student_info = {
                    "student_id": str(student["_id"]),
                    "student_name": student_name,
                    "surname": student.get("surname", ""),
                    "otherNames": student.get("otherNames", ""),
                    "email": student.get("email", ""),
                    "phone": student.get("phone", ""),
                    "student_image": student.get("image", ""),
                    "academicId": student.get(
                        "academicId", student.get("studentID", "")
                    ),
                    "program": (
                        {
                            "program_id": str(program["_id"]) if program else None,
                            "title": program.get("title", "") if program else None,
                            "tag": program.get("tag", "") if program else None,
                            "description": (
                                program.get("description", "") if program else None
                            ),
                        }
                        if program
                        else None
                    ),
                    "supervisor": (
                        {
                            "supervisor_id": (
                                str(supervisor["_id"]) if supervisor else None
                            ),
                            "name": supervisor.get("name", "") if supervisor else None,
                            "email": (
                                supervisor.get("email", "") if supervisor else None
                            ),
                            "department": (
                                supervisor.get("department", "") if supervisor else None
                            ),
                            "title": (
                                supervisor.get("title", "") if supervisor else None
                            ),
                        }
                        if supervisor
                        else None
                    ),
                    "fyp_details": {
                        "fyp_id": str(fyp["_id"]),
                        "checkin": str(fyp["checkin"]) if fyp.get("checkin") else None,
                        "created_at": fyp.get("createdAt"),
                        "updated_at": fyp.get("updatedAt"),
                    },
                }
                students_data.append(student_info)

        return students_data


    async def get_students_by_supervisor(self, supervisor: str):
        # Get all FYPs that use this supervisor
        fyps = (
            await self.db["fyps"].find({"supervisor": ObjectId(supervisor)}).to_list(None)
        )

        students_data = []
        for fyp in fyps:
            # Get student details
            student = await self.collection.find_one({"_id": fyp["student"]})
            if student:
                # Get program details
                program = None
                if student.get("program"):
                    program = await self.db["programs"].find_one(
                        {"_id": student["program"]}
                    )

                # Get supervisor details
                supervisor = None
                if fyp.get("supervisor"):
                    supervisor = await self.db["lecturers"].find_one(
                        {"_id": fyp["supervisor"]}
                    )

                student_name = (
                    f"{student.get('surname', '')} {student.get('otherNames', '')}".strip()
                )

                student_info = {
                    "student_id": str(student["_id"]),
                    "student_name": student_name,
                    "surname": student.get("surname", ""),
                    "otherNames": student.get("otherNames", ""),
                    "email": student.get("email", ""),
                    "phone": student.get("phone", ""),
                    "student_image": student.get("image", ""),
                    "academicId": student.get("academicId", student.get("studentID", "")),
                    "program": (
                        {
                            "program_id": str(program["_id"]) if program else None,
                            "title": program.get("title", "") if program else None,
                            "tag": program.get("tag", "") if program else None,
                            "description": (
                                program.get("description", "") if program else None
                            ),
                        }
                        if program
                        else None
                    ),
                    "supervisor": (
                        {
                            "supervisor_id": str(supervisor["_id"]) if supervisor else None,
                            "name": supervisor.get("name", "") if supervisor else None,
                            "email": supervisor.get("email", "") if supervisor else None,
                            "department": (
                                supervisor.get("department", "") if supervisor else None
                            ),
                            "title": supervisor.get("title", "") if supervisor else None,
                        }
                        if supervisor
                        else None
                    ),
                }
                
                students_data.append(student_info)

        return students_data
