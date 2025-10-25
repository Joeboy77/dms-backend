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
        student_data["createdAt"] = datetime.now()
        student_data["updatedAt"] = None

        # Check if academicId already exists
        existing_student = await self.collection.find_one(
            {"academicId": student_data.get("academicId")}
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

        # use camelCase updatedAt to match other documents/schemas
        update_data["updatedAt"] = datetime.now()

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
        students = await self.collection.find({"program": major}).to_list(None)
        return students

    async def get_students_by_year(self, year: int):
        students = await self.collection.find({"year": year}).to_list(None)
        return students

    async def get_total_student_count(self):
        count = await self.collection.count_documents({})
        return {"total_students": count}


    async def get_students_by_project_area(self, project_area_id: str):
        print("Searching FYPs for projectArea:", project_area_id)

        # Build query that matches both string and ObjectId
        query = {"$or": [{"projectArea": project_area_id}]}
        try:
            query["$or"].append({"projectArea": ObjectId(project_area_id)})
        except Exception as e:
            print("Invalid ObjectId format:", e)

        fyps = await self.db["fyps"].find(query).to_list(None)
        print(f"Found {len(fyps)} FYP(s)")
        if fyps:
            print("Example FYP:", fyps[0])

        students_data = []
        for fyp in fyps:
            student_id = fyp.get("student")
            if not student_id:
                continue

            # Convert student_id safely
            try:
                student_obj_id = ObjectId(student_id)
            except Exception:
                student_obj_id = student_id

            student = await self.collection.find_one({"_id": student_obj_id})
            if not student:
                print(f"No student found for FYP {fyp['_id']}")
                continue

            # Convert program_id safely
            program = None
            if student.get("program"):
                try:
                    program_obj_id = ObjectId(student["program"])
                except Exception:
                    program_obj_id = student["program"]
                program = await self.db["programs"].find_one({"_id": program_obj_id})

            # Convert supervisor_id safely
            supervisor_doc = None
            if fyp.get("supervisor"):
                try:
                    supervisor_obj_id = ObjectId(fyp["supervisor"])
                except Exception:
                    supervisor_obj_id = fyp["supervisor"]
                supervisor_doc = await self.db["supervisors"].find_one({"_id": supervisor_obj_id})

            supervisor = None
            if supervisor_doc:
                try:
                    lecturer_obj_id = ObjectId(supervisor_doc["lecturer_id"])
                except Exception:
                    lecturer_obj_id = supervisor_doc["lecturer_id"]
                supervisor = await self.db["lecturers"].find_one({"_id": lecturer_obj_id})

            # Assemble final student info
            students_data.append({
                "student_id": str(student["_id"]),
                "student_name": f"{student.get('surname', '')} {student.get('otherNames', '')}".strip(),
                "program": program.get("title", "") if program else None,
                "supervisor": f"{supervisor.get('surname', '')} {supervisor.get('otherNames', '')}".strip() if supervisor else None,
                "fyp_id": str(fyp["_id"]),
            })

        print("Returning", len(students_data), "students")
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
                    "academicId": student.get("academicId", ""),
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



    async def assign_students_to_supervisor(self, student_ids: list[str], academic_year_id: str, supervisor_id: str):
        # Get the checkin record
        checkin = await self.db["fypcheckins"].find_one({"academicYear": academic_year_id})
        if not checkin:
            raise HTTPException(status_code=404, detail="FYP checkin not found for the academic year")

        checkin_id = checkin["_id"]

        # Fetch supervisor and linked lecturer
        supervisor = await self.db["supervisors"].find_one({"_id": ObjectId(supervisor_id)})
        if not supervisor:
            raise HTTPException(status_code=404, detail="Supervisor not found")

        lecturer = await self.db["lecturers"].find_one({"_id": ObjectId(supervisor["lecturer_id"])})
        if not lecturer:
            raise HTTPException(status_code=404, detail="Lecturer for supervisor not found")

        created_assignments = []
        assignment_errors = []

        # Assign students
        for student_id in student_ids:
            try:
                # Verify student exists
                student = await self.collection.find_one({"academicId": student_id})
                if not student:
                    assignment_errors.append(f"Student {student_id} not found")
                    continue

                # Check if already assigned
                existing_fyp = await self.db["fyps"].find_one({
                    "student": student["_id"],
                    "checkin": checkin_id
                })
                if existing_fyp:
                    assignment_errors.append(f"Student {student_id} already assigned to a supervisor for this academic year")
                    continue

                # Create assignment
                fyp_data = {
                    "student": student["_id"],
                    "checkin": checkin_id,
                    "supervisor": ObjectId(supervisor_id),
                    "projectArea": None,
                    "createdAt": datetime.utcnow(),
                    "updatedAt": datetime.utcnow()
                }

                result = await self.db["fyps"].insert_one(fyp_data)
                created_fyp = await self.db["fyps"].find_one({"_id": result.inserted_id})

                created_assignments.append({
                    "fyp_id": str(created_fyp["_id"]),
                    "student_id": str(created_fyp["student"]),
                    "supervisor_id": str(created_fyp["supervisor"]),
                    "checkin_id": str(created_fyp["checkin"]),
                    "project_area_id": str(created_fyp["projectArea"]) if created_fyp["projectArea"] else None,
                    "created_at": created_fyp["createdAt"],
                    "updated_at": created_fyp["updatedAt"]
                })

            except Exception as e:
                assignment_errors.append(f"Error assigning student {student_id}: {str(e)}")

        # Log activity after all assignments
        if created_assignments:
            try:
                await self.db["activity_logs"].insert_one({
                    "description": f"Assigned {len(created_assignments)} student(s) to Supervisor {lecturer.get('title', '')} {lecturer.get('surname', '')} {lecturer.get('otherNames', '')}.",
                    "action": "student_assignment",
                    "user_name": lecturer.get("academicId"),
                    "user_id": str(supervisor["_id"]),
                    "type": "assignment",
                    "timestamp": datetime.utcnow(),
                    "createdAt": datetime.utcnow(),
                    "updatedAt": datetime.utcnow(),
                    "details": {
                        "student_count": len(created_assignments),
                        "supervisor_name": f"{lecturer.get('title', '')} {lecturer.get('surname', '')} {lecturer.get('otherNames', '')}".strip(),
                        "project_area": None,
                        "assigned_students": student_ids
                    }
                })
            except Exception as log_error:
                print("Failed to log activity:", log_error)

        # Return response
        return {
            "message": "Assignment process completed",
            "successful_assignments": len(created_assignments),
            "failed_assignments": len(assignment_errors),
            "created_assignments": created_assignments,
            "errors": assignment_errors
        }



    async def get_all_students_with_details(self, limit: int = 10, cursor: str | None = None):
        query = {"deleted": {"$ne": True}}
        if cursor:
            query["_id"] = {"$gt": ObjectId(cursor)}

        students = await self.collection.find(query).limit(limit).to_list(limit)

        detailed_students = []
        for student in students:
            # Get program details
            program = None
            if student.get("program"):
                program = await self.db["programs"].find_one({"title": student["program"]})

            # Get student's FYP to find supervisor and project area
            fyp = await self.db["fyps"].find_one({"student": str(student["_id"])})

            supervisor = None
            project_area = None

            if fyp:
                # Get supervisor details
                if fyp.get("supervisor"):
                    supervisor_lecturer = await self.db["supervisors"].find_one({"_id": ObjectId(fyp["supervisor"])})
                    lecturer = await self.db["lecturers"].find_one({"_id": supervisor_lecturer["lecturer_id"]})
                    if supervisor_lecturer:
                        # Create full name from surname and otherNames
                        supervisor_name = f"{lecturer.get('surname', '')} {lecturer.get('otherNames', '')}".strip()
                        supervisor = {
                            "supervisor_id": str(lecturer["_id"]),
                            "name": supervisor_name,
                            "email": lecturer.get("email", ""),
                            "phone": lecturer.get("phone", ""),
                            "position": lecturer.get("position", ""),
                            "title": lecturer.get("title", ""),
                            "bio": lecturer.get("bio", ""),
                            "academic_id": lecturer.get("academicId", ""),
                            "office_hours": lecturer.get("officeHours", ""),
                            "office_location": lecturer.get("officeLocation", "")
                        }

                # Get project area details
                if fyp.get("projectArea"):
                    project_area_doc = await self.db["project_areas"].find_one({"_id": ObjectId(fyp["projectArea"])})
                    if project_area_doc:
                        project_area = {
                            "project_area_id": str(project_area_doc["_id"]),
                            "title": project_area_doc.get("title", ""),
                            "description": project_area_doc.get("description", ""),
                            "image": project_area_doc.get("image", "")
                        }

            # Format student name
            student_name = f"{student.get('surname', '')} {student.get('otherNames', '')}".strip()
            # print(lecturer)

            detailed_student = {
                "student": {
                    "student_id": str(student["_id"]),
                    "student_name": student_name,
                    "title": student.get("title", ""),
                    "surname": student.get("surname", ""),
                    "otherNames": student.get("otherNames", ""),
                    "email": student.get("email", ""),
                    "phone": student.get("phone", ""),
                    "academic_id": student.get("academicId", ""),
                    "image": student.get("image", ""),
                    "type": student.get("type", "UNDERGRADUATE"),
                    "deleted": student.get("deleted", False),
                    "created_at": student.get("createdAt"),
                    "updated_at": student.get("updatedAt")
                },
                "program": {
                    "program_id": str(program["_id"]) if program else None,
                    "title": program.get("title", "") if program else "N/A",
                    "tag": program.get("tag", "") if program else "N/A",
                    "description": program.get("description", "") if program else "N/A"
                } if program else {
                    "program_id": None,
                    "title": "N/A",
                    "tag": "N/A",
                    "description": "N/A"
                },
                "supervisor": supervisor if supervisor else {
                    "supervisor_id": None,
                    "name": "N/A",
                    "email": "N/A",
                    "phone": "N/A",
                    "position": "N/A",
                    "title": "N/A",
                    "bio": "N/A",
                    "academic_id": "N/A",
                    "office_hours": "N/A",
                    "office_location": "N/A"
                },
                "project_area": project_area if project_area else {
                    "project_area_id": None,
                    "title": "N/A",
                    "description": "N/A",
                    "image": "N/A"
                },
                "fyp_details": {
                    "fyp_id": str(fyp["_id"]) if fyp else None,
                    "checkin_id": str(fyp["checkin"]) if fyp and fyp.get("checkin") else None,
                    "created_at": fyp.get("createdAt") if fyp else None,
                    "updated_at": fyp.get("updatedAt") if fyp else None
                } if fyp else {
                    "fyp_id": None,
                    "checkin_id": None,
                    "created_at": None,
                    "updated_at": None
                }
            }
            detailed_students.append(detailed_student)

        next_cursor = None
        if len(students) == limit:
            next_cursor = str(students[-1]["_id"])

        return {
            "items": detailed_students,
            "next_cursor": next_cursor
        }
