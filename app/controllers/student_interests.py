from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException
from typing import List, Dict, Optional


class StudentInterestController:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db["student_interests"]
        self.project_areas_collection = db["project_areas"]

    async def get_all_student_interests(self, limit: int = 10, cursor: str | None = None):
        """Get all student interests with pagination"""
        query = {}
        if cursor:
            query["_id"] = {"$gt": ObjectId(cursor)}

        interests = await self.collection.find(query).limit(limit).to_list(limit)

        next_cursor = None
        if len(interests) == limit:
            next_cursor = str(interests[-1]["_id"])

        return {
            "items": interests,
            "next_cursor": next_cursor
        }

    async def get_student_interest_by_id(self, interest_id: str):
        """Get specific student interest by ID"""
        interest = await self.collection.find_one({"_id": ObjectId(interest_id)})
        if not interest:
            raise HTTPException(status_code=404, detail="Student interest not found")
        return interest

    async def create_student_interest(self, interest_data: dict):
        """Create new student interest record"""
        # Convert IDs to ObjectId if they're strings
        if "student" in interest_data and isinstance(interest_data["student"], str):
            interest_data["student"] = ObjectId(interest_data["student"])
        if "academicYear" in interest_data and isinstance(interest_data["academicYear"], str):
            interest_data["academicYear"] = interest_data["academicYear"]
        # if "projectAreas" in interest_data:
        #     interest_data["projectAreas"] = [
        #         ObjectId(pa_id) if isinstance(pa_id, str) else pa_id
        #         for pa_id in interest_data["projectAreas"]
        #     ]
            
        if "projectAreas" in interest_data:
            project_areas = []
            for pa_id in interest_data["projectAreas"]:
                pa_obj_id = ObjectId(pa_id) if isinstance(pa_id, str) else pa_id
                # Validate project area exists
                if not await self.project_areas_collection.find_one({"_id": pa_obj_id}):
                    raise HTTPException(status_code=400, detail=f"Project area {pa_id} not found")
                project_areas.append(pa_obj_id)
            interest_data["projectAreas"] = project_areas

        interest_data["createdAt"] = datetime.now()
        interest_data["updatedAt"] = datetime.now()

        result = await self.collection.insert_one(interest_data)
        created_interest = await self.collection.find_one({"_id": result.inserted_id})
        return created_interest

    async def update_student_interest(self, interest_id: str, update_data: dict):
        """Update student interest record"""
        update_data = {k: v for k, v in update_data.items() if v is not None}

        if not update_data:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        # Convert IDs to ObjectId if they're strings
        if "student" in update_data and isinstance(update_data["student"], str):
            update_data["student"] = ObjectId(update_data["student"])
        if "academicYear" in update_data and isinstance(update_data["academicYear"], str):
            update_data["academicYear"] = ObjectId(update_data["academicYear"])
        
        # Validate project areas exist before updating interest
        if "projectAreas" in update_data:
            validated_project_areas = []
            for pa_id in update_data["projectAreas"]:
                pa_obj_id = ObjectId(pa_id) if isinstance(pa_id, str) else pa_id
                # Check if project area exists
                project_area = await self.project_areas_collection.find_one({"_id": pa_obj_id})
                if not project_area:
                    raise HTTPException(status_code=400, detail=f"Project area {pa_id} not found")
                validated_project_areas.append(pa_obj_id)
            update_data["projectAreas"] = validated_project_areas

        update_data["updatedAt"] = datetime.now()

        result = await self.collection.update_one(
            {"_id": ObjectId(interest_id)},
            {"$set": update_data}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Student interest not found")

        updated_interest = await self.collection.find_one({"_id": ObjectId(interest_id)})
        return updated_interest

    async def delete_student_interest(self, interest_id: str):
        """Delete student interest record"""
        result = await self.collection.delete_one({"_id": ObjectId(interest_id)})

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Student interest not found")

        return {"message": "Student interest deleted successfully"}

    async def get_student_interests_by_student(self, student_id: str):
        """Get all interests for a specific student"""
        if not ObjectId.is_valid(student_id):
            raise HTTPException(status_code=400, detail="Invalid student ID format")

        # Step 1: Find all interests for this student
        interests = await self.collection.find({"student": ObjectId(student_id)}).to_list(None)

        # Step 2: Populate each project's details
        for interest in interests:
            populated_areas = []
            for pa_id in interest.get("projectAreas", []):
                # ensure pa_id is an ObjectId
                if isinstance(pa_id, str) and ObjectId.is_valid(pa_id):
                    pa_id = ObjectId(pa_id)
                project_area = await self.project_areas_collection.find_one({"_id": pa_id})
                if project_area:
                    populated_areas.append(project_area)
            interest["projectAreas"] = populated_areas

        return interests

    async def get_student_interests_by_academic_year(self, academic_year_id: str):
        """Get all student interests for a specific academic year"""
        interests = await self.collection.find({"academicYear": ObjectId(academic_year_id)}).to_list(None)
        return interests

    async def get_students_interested_in_project_area(self, project_area_id: str, academic_year_id: str = None):
        """Get all students interested in a specific project area"""
        query = {"projectAreas": ObjectId(project_area_id)}
        if academic_year_id:
            query["academicYear"] = ObjectId(academic_year_id)

        interests = await self.collection.find(query).to_list(None)
        
        # Get student details for each interest
        students_data = []
        for interest in interests:
            student = await self.db["students"].find_one({"_id": interest["student"]})
            if student:
                # Get program details
                program = None
                if student.get("program"):
                    program = await self.db["programs"].find_one({"_id": student["program"]})

                student_info = {
                    "interest_id": str(interest["_id"]),
                    "student_id": str(student["_id"]),
                    "student_name": f"{student.get('surname', '')} {student.get('otherNames', '')}".strip(),
                    "academic_id": student.get("academicId", ""),
                    "email": student.get("email", ""),
                    "phone": student.get("phone", ""),
                    "program": program.get("title", "") if program else None,
                    "preference_rank": interest.get("preference_rank", 0),
                    "interest_level": interest.get("interest_level", "MEDIUM"),
                    "notes": interest.get("notes", ""),
                    "created_at": interest.get("createdAt"),
                    "updated_at": interest.get("updatedAt")
                }
                students_data.append(student_info)

        return students_data

    async def update_student_preference_ranking(self, student_id: str, project_area_id: str, rank: int):
        """Update student's preference ranking for a project area"""
        result = await self.collection.update_one(
            {
                "student": ObjectId(student_id),
                "projectAreas": ObjectId(project_area_id)
            },
            {
                "$set": {
                    "preference_rank": rank,
                    "updatedAt": datetime.now()
                }
            }
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Student interest not found")

        return {"message": "Preference ranking updated successfully"}

    async def get_student_supervisor_matches(self, student_id: str, academic_year_id: str = None):
        """Find potential supervisor matches based on student interests"""
        # Get student interests
        query = {"student": ObjectId(student_id)}
        if academic_year_id:
            query["academicYear"] = ObjectId(academic_year_id)

        student_interests = await self.collection.find(query).to_list(None)
        if not student_interests:
            return []

        # Get all project areas the student is interested in
        interested_project_areas = set()
        for interest in student_interests:
            for pa_id in interest.get("projectAreas", []):
                interested_project_areas.add(pa_id)

        # Find supervisors interested in these project areas
        matches = []
        for project_area_id in interested_project_areas:
            # Get lecturers interested in this project area
            project_area = await self.db["project_areas"].find_one({"_id": project_area_id})
            if not project_area:
                continue

            interested_staff = project_area.get("interested_staff", [])
            for lecturer_id in interested_staff:
                # Get lecturer details
                lecturer = await self.db["lecturers"].find_one({"_id": lecturer_id})
                if not lecturer:
                    continue

                # Check if lecturer is a supervisor
                supervisor = await self.db["supervisors"].find_one({"lecturer_id": lecturer_id})
                if not supervisor:
                    continue

                # Get student's preference for this project area
                student_preference = None
                for interest in student_interests:
                    if project_area_id in interest.get("projectAreas", []):
                        student_preference = {
                            "rank": interest.get("preference_rank", 0),
                            "level": interest.get("interest_level", "MEDIUM"),
                            "notes": interest.get("notes", "")
                        }
                        break

                match_info = {
                    "project_area": {
                        "id": str(project_area["_id"]),
                        "title": project_area.get("title", ""),
                        "description": project_area.get("description", "")
                    },
                    "supervisor": {
                        "supervisor_id": str(supervisor["_id"]),
                        "lecturer_id": str(lecturer["_id"]),
                        "name": f"{lecturer.get('surname', '')} {lecturer.get('otherNames', '')}".strip(),
                        "email": lecturer.get("email", ""),
                        "position": lecturer.get("position", ""),
                        "bio": lecturer.get("bio", ""),
                        "max_students": supervisor.get("max_students"),
                        "current_students": await self.db["fyps"].count_documents({"supervisor": supervisor["_id"]})
                    },
                    "student_preference": student_preference,
                    "match_score": self._calculate_match_score(student_preference, lecturer, supervisor)
                }
                matches.append(match_info)

        # Sort by match score (highest first)
        matches.sort(key=lambda x: x["match_score"], reverse=True)
        return matches

    def _calculate_match_score(self, student_preference: dict, lecturer: dict, supervisor: dict) -> float:
        """Calculate match score between student and supervisor"""
        score = 0.0

        # Base score from student preference rank (inverted - lower rank = higher score)
        if student_preference:
            rank = student_preference.get("rank", 0)
            if rank > 0:
                score += (10 - rank) * 10  # Rank 1 = 90 points, Rank 2 = 80 points, etc.

            # Interest level bonus
            interest_level = student_preference.get("level", "MEDIUM")
            if interest_level == "HIGH":
                score += 20
            elif interest_level == "MEDIUM":
                score += 10

        # Supervisor capacity bonus (prefer supervisors with available slots)
        max_students = supervisor.get("max_students", 5)
        current_students = supervisor.get("current_students", 0)
        if current_students < max_students:
            capacity_ratio = (max_students - current_students) / max_students
            score += capacity_ratio * 30

        # Lecturer experience bonus (based on bio length and position)
        bio = lecturer.get("bio", "")
        position = lecturer.get("position", "")
        if len(bio) > 100:  # More detailed bio indicates more experience
            score += 10
        if "professor" in position.lower() or "senior" in position.lower():
            score += 15

        return round(score, 2)

    async def get_interest_statistics(self, academic_year_id: str = None):
        """Get statistics about student interests"""
        query = {}
        if academic_year_id:
            query["academicYear"] = ObjectId(academic_year_id)

        interests = await self.collection.find(query).to_list(None)

        stats = {
            "total_interests": len(interests),
            "unique_students": len(set(interest["student"] for interest in interests)),
            "project_area_popularity": {},
            "interest_level_distribution": {},
            "preference_rank_distribution": {}
        }

        # Calculate project area popularity
        for interest in interests:
            for pa_id in interest.get("projectAreas", []):
                pa_id_str = str(pa_id)
                stats["project_area_popularity"][pa_id_str] = stats["project_area_popularity"].get(pa_id_str, 0) + 1

        # Calculate interest level distribution
        for interest in interests:
            level = interest.get("interest_level", "MEDIUM")
            stats["interest_level_distribution"][level] = stats["interest_level_distribution"].get(level, 0) + 1

        # Calculate preference rank distribution
        for interest in interests:
            rank = interest.get("preference_rank", 0)
            stats["preference_rank_distribution"][str(rank)] = stats["preference_rank_distribution"].get(str(rank), 0) + 1

        # Get project area titles
        project_area_titles = {}
        for pa_id in stats["project_area_popularity"].keys():
            pa = await self.db["project_areas"].find_one({"_id": ObjectId(pa_id)})
            if pa:
                project_area_titles[pa_id] = pa.get("title", "")

        stats["project_area_titles"] = project_area_titles

        return stats

    async def bulk_import_student_interests(self, interests_data: List[dict]):
        """Bulk import student interests from external data"""
        imported_count = 0
        errors = []

        for interest_data in interests_data:
            try:
                await self.create_student_interest(interest_data)
                imported_count += 1
            except Exception as e:
                errors.append({
                    "data": interest_data,
                    "error": str(e)
                })

        return {
            "imported_count": imported_count,
            "error_count": len(errors),
            "errors": errors
        }
