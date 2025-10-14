from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException
from typing import List, Dict, Optional


class EnhancedSupervisorInterestController:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.project_areas_collection = db["project_areas"]
        self.lecturer_project_areas_collection = db["lecturer_project_areas"]
        self.lecturers_collection = db["lecturers"]
        self.supervisors_collection = db["supervisors"]

    async def get_supervisor_interest_profile(self, supervisor_id: str, academic_year_id: str = None):
        """Get comprehensive interest profile for a supervisor"""
        # Get supervisor details
        supervisor = await self.supervisors_collection.find_one({"_id": ObjectId(supervisor_id)})
        if not supervisor:
            raise HTTPException(status_code=404, detail="Supervisor not found")

        # Get lecturer details
        lecturer = await self.lecturers_collection.find_one({"_id": supervisor["lecturer_id"]})
        if not lecturer:
            raise HTTPException(status_code=404, detail="Lecturer not found")

        # Get lecturer's project areas for specific academic year
        query = {"lecturer": supervisor["lecturer_id"]}
        if academic_year_id:
            query["academicYear"] = ObjectId(academic_year_id)

        lpa_records = await self.lecturer_project_areas_collection.find(query).to_list(None)

        # Get detailed project area information
        project_areas = []
        for lpa in lpa_records:
            for pa_id in lpa.get("projectAreas", []):
                pa = await self.project_areas_collection.find_one({"_id": pa_id})
                if pa:
                    # Get student interest count for this area
                    student_interests = await self.db["student_interests"].count_documents({
                        "projectAreas": pa_id,
                        "academicYear": lpa["academicYear"]
                    })

                    project_area_info = {
                        "project_area_id": str(pa["_id"]),
                        "title": pa.get("title", ""),
                        "description": pa.get("description", ""),
                        "image": pa.get("image", ""),
                        "academic_year_id": str(lpa["academicYear"]),
                        "interested_students_count": student_interests,
                        "created_at": lpa.get("createdAt"),
                        "updated_at": lpa.get("updatedAt")
                    }
                    project_areas.append(project_area_info)

        # Get current student count
        current_students = await self.db["fyps"].count_documents({"supervisor": ObjectId(supervisor_id)})

        # Get capacity utilization
        max_students = supervisor.get("max_students", 5)
        capacity_utilization = (current_students / max_students) * 100 if max_students > 0 else 0

        return {
            "supervisor": {
                "supervisor_id": str(supervisor["_id"]),
                "lecturer_id": str(supervisor["lecturer_id"]),
                "max_students": max_students,
                "current_students": current_students,
                "capacity_utilization": round(capacity_utilization, 2),
                "available_slots": max_students - current_students
            },
            "lecturer": {
                "lecturer_id": str(lecturer["_id"]),
                "name": f"{lecturer.get('surname', '')} {lecturer.get('otherNames', '')}".strip(),
                "email": lecturer.get("email", ""),
                "position": lecturer.get("position", ""),
                "bio": lecturer.get("bio", ""),
                "office_hours": lecturer.get("officeHours", ""),
                "office_location": lecturer.get("officeLocation", "")
            },
            "project_areas": project_areas,
            "total_project_areas": len(project_areas),
            "total_interested_students": sum(pa["interested_students_count"] for pa in project_areas)
        }

    async def add_supervisor_interest(self, supervisor_id: str, project_area_id: str, academic_year_id: str):
        """Add a project area interest for a supervisor"""
        # Verify supervisor exists
        supervisor = await self.supervisors_collection.find_one({"_id": ObjectId(supervisor_id)})
        if not supervisor:
            raise HTTPException(status_code=404, detail="Supervisor not found")

        # Verify project area exists
        project_area = await self.project_areas_collection.find_one({"_id": ObjectId(project_area_id)})
        if not project_area:
            raise HTTPException(status_code=404, detail="Project area not found")

        # Check if lecturer already has this project area for this academic year
        existing_lpa = await self.lecturer_project_areas_collection.find_one({
            "lecturer": supervisor["lecturer_id"],
            "academicYear": ObjectId(academic_year_id),
            "projectAreas": ObjectId(project_area_id)
        })

        if existing_lpa:
            raise HTTPException(status_code=400, detail="Supervisor already interested in this project area for this academic year")

        # Add to lecturer_project_areas collection
        lpa_record = await self.lecturer_project_areas_collection.find_one({
            "lecturer": supervisor["lecturer_id"],
            "academicYear": ObjectId(academic_year_id)
        })

        if lpa_record:
            # Update existing record
            await self.lecturer_project_areas_collection.update_one(
                {"_id": lpa_record["_id"]},
                {
                    "$push": {"projectAreas": ObjectId(project_area_id)},
                    "$set": {"updatedAt": datetime.now()}
                }
            )
        else:
            # Create new record
            lpa_data = {
                "lecturer": supervisor["lecturer_id"],
                "academicYear": ObjectId(academic_year_id),
                "projectAreas": [ObjectId(project_area_id)],
                "createdAt": datetime.now(),
                "updatedAt": datetime.now()
            }
            await self.lecturer_project_areas_collection.insert_one(lpa_data)

        # Also add to project_areas interested_staff if not already there
        await self.project_areas_collection.update_one(
            {"_id": ObjectId(project_area_id)},
            {
                "$addToSet": {"interested_staff": supervisor["lecturer_id"]},
                "$set": {"updatedAt": datetime.now()}
            }
        )

        return {"message": "Supervisor interest added successfully"}

    async def remove_supervisor_interest(self, supervisor_id: str, project_area_id: str, academic_year_id: str):
        """Remove a project area interest for a supervisor"""
        # Verify supervisor exists
        supervisor = await self.supervisors_collection.find_one({"_id": ObjectId(supervisor_id)})
        if not supervisor:
            raise HTTPException(status_code=404, detail="Supervisor not found")

        # Remove from lecturer_project_areas collection
        await self.lecturer_project_areas_collection.update_one(
            {
                "lecturer": supervisor["lecturer_id"],
                "academicYear": ObjectId(academic_year_id)
            },
            {
                "$pull": {"projectAreas": ObjectId(project_area_id)},
                "$set": {"updatedAt": datetime.now()}
            }
        )

        # Remove from project_areas interested_staff
        await self.project_areas_collection.update_one(
            {"_id": ObjectId(project_area_id)},
            {
                "$pull": {"interested_staff": supervisor["lecturer_id"]},
                "$set": {"updatedAt": datetime.now()}
            }
        )

        return {"message": "Supervisor interest removed successfully"}

    async def get_supervisor_matching_students(self, supervisor_id: str, academic_year_id: str = None):
        """Get students who are interested in areas that this supervisor is interested in"""
        # Get supervisor's project areas
        query = {"lecturer": (await self.supervisors_collection.find_one({"_id": ObjectId(supervisor_id)}))["lecturer_id"]}
        if academic_year_id:
            query["academicYear"] = ObjectId(academic_year_id)

        lpa_records = await self.lecturer_project_areas_collection.find(query).to_list(None)

        if not lpa_records:
            return []

        # Get all project areas this supervisor is interested in
        supervisor_project_areas = set()
        for lpa in lpa_records:
            for pa_id in lpa.get("projectAreas", []):
                supervisor_project_areas.add(pa_id)

        # Find students interested in these project areas
        matching_students = []
        for project_area_id in supervisor_project_areas:
            student_interests = await self.db["student_interests"].find({
                "projectAreas": project_area_id
            }).to_list(None)

            for interest in student_interests:
                # Check if this is for the right academic year
                if academic_year_id and interest["academicYear"] != ObjectId(academic_year_id):
                    continue

                # Get student details
                student = await self.db["students"].find_one({"_id": interest["student"]})
                if not student:
                    continue

                # Get program details
                program = None
                if student.get("program"):
                    program = await self.db["programs"].find_one({"_id": student["program"]})

                # Get project area details
                project_area = await self.project_areas_collection.find_one({"_id": project_area_id})

                # Calculate match score
                match_score = self._calculate_supervisor_student_match_score(
                    interest, student, project_area
                )

                student_info = {
                    "student_id": str(student["_id"]),
                    "student_name": f"{student.get('surname', '')} {student.get('otherNames', '')}".strip(),
                    "academic_id": student.get("academicId", ""),
                    "email": student.get("email", ""),
                    "program": program.get("title", "") if program else None,
                    "project_area": {
                        "id": str(project_area["_id"]),
                        "title": project_area.get("title", ""),
                        "description": project_area.get("description", "")
                    },
                    "student_preference": {
                        "rank": interest.get("preference_rank", 0),
                        "level": interest.get("interest_level", "MEDIUM"),
                        "notes": interest.get("notes", "")
                    },
                    "match_score": match_score,
                    "interest_created_at": interest.get("createdAt")
                }
                matching_students.append(student_info)

        # Sort by match score (highest first)
        matching_students.sort(key=lambda x: x["match_score"], reverse=True)

        # Remove duplicates (same student, different project areas)
        seen_students = set()
        unique_matches = []
        for match in matching_students:
            student_id = match["student_id"]
            if student_id not in seen_students:
                seen_students.add(student_id)
                unique_matches.append(match)

        return unique_matches

    def _calculate_supervisor_student_match_score(self, interest: dict, student: dict, project_area: dict) -> float:
        """Calculate match score between supervisor and student interest"""
        score = 0.0

        # Base score from student preference rank (inverted - lower rank = higher score)
        rank = interest.get("preference_rank", 0)
        if rank > 0:
            score += (10 - rank) * 10  # Rank 1 = 90 points, Rank 2 = 80 points, etc.

        # Interest level bonus
        interest_level = interest.get("interest_level", "MEDIUM")
        if interest_level == "HIGH":
            score += 20
        elif interest_level == "MEDIUM":
            score += 10

        # Project area popularity bonus (less popular = higher score for better distribution)
        # This would need to be calculated based on overall statistics
        # For now, we'll use a base score

        # Student academic performance bonus (if available)
        # This could be based on GPA, previous project success, etc.
        # For now, we'll use a placeholder

        return round(score, 2)

    async def get_supervisor_interest_analytics(self, academic_year_id: str = None):
        """Get analytics about supervisor interests and matching patterns"""
        query = {}
        if academic_year_id:
            query["academicYear"] = ObjectId(academic_year_id)

        # Get all lecturer project area records
        lpa_records = await self.lecturer_project_areas_collection.find(query).to_list(None)

        analytics = {
            "total_supervisors": 0,
            "supervisors_with_interests": 0,
            "average_interests_per_supervisor": 0,
            "most_popular_areas_for_supervisors": {},
            "supervisor_capacity_utilization": {},
            "matching_statistics": {}
        }

        if not lpa_records:
            return analytics

        # Get all supervisors
        all_supervisors = await self.supervisors_collection.find({}).to_list(None)
        analytics["total_supervisors"] = len(all_supervisors)

        # Analyze supervisor interests
        supervisor_interests = {}
        project_area_counts = {}
        total_interests = 0

        for lpa in lpa_records:
            lecturer_id = lpa["lecturer"]
            project_areas = lpa.get("projectAreas", [])
            
            supervisor = await self.supervisors_collection.find_one({"lecturer_id": lecturer_id})
            if supervisor:
                supervisor_id = str(supervisor["_id"])
                supervisor_interests[supervisor_id] = len(project_areas)
                total_interests += len(project_areas)

                # Count project area popularity
                for pa_id in project_areas:
                    pa_id_str = str(pa_id)
                    project_area_counts[pa_id_str] = project_area_counts.get(pa_id_str, 0) + 1

        analytics["supervisors_with_interests"] = len(supervisor_interests)
        analytics["average_interests_per_supervisor"] = round(
            total_interests / len(supervisor_interests) if supervisor_interests else 0, 2
        )

        # Get project area titles
        project_area_titles = {}
        for pa_id in project_area_counts.keys():
            pa = await self.project_areas_collection.find_one({"_id": ObjectId(pa_id)})
            if pa:
                project_area_titles[pa_id] = pa.get("title", "")

        # Most popular areas for supervisors
        most_popular = sorted(
            [(pa_id, count, project_area_titles.get(pa_id, "")) for pa_id, count in project_area_counts.items()],
            key=lambda x: x[1],
            reverse=True
        )[:5]

        analytics["most_popular_areas_for_supervisors"] = [
            {"project_area_id": pa_id, "title": title, "supervisor_count": count}
            for pa_id, count, title in most_popular
        ]

        # Supervisor capacity utilization
        for supervisor in all_supervisors:
            supervisor_id = str(supervisor["_id"])
            current_students = await self.db["fyps"].count_documents({"supervisor": supervisor["_id"]})
            max_students = supervisor.get("max_students", 5)
            utilization = (current_students / max_students) * 100 if max_students > 0 else 0

            analytics["supervisor_capacity_utilization"][supervisor_id] = {
                "current_students": current_students,
                "max_students": max_students,
                "utilization_percentage": round(utilization, 2),
                "available_slots": max_students - current_students
            }

        return analytics

    async def get_optimal_supervisor_student_matches(self, academic_year_id: str = None):
        """Get optimal matches between supervisors and students based on interests and capacity"""
        # This would implement a more sophisticated matching algorithm
        # For now, we'll return a basic implementation
        
        # Get all students with interests
        query = {}
        if academic_year_id:
            query["academicYear"] = ObjectId(academic_year_id)

        student_interests = await self.db["student_interests"].find(query).to_list(None)
        
        matches = []
        for interest in student_interests:
            student_id = interest["student"]
            project_areas = interest.get("projectAreas", [])
            
            # Find supervisors interested in these project areas
            for project_area_id in project_areas:
                # Get supervisors interested in this project area
                lpa_records = await self.lecturer_project_areas_collection.find({
                    "projectAreas": project_area_id,
                    "academicYear": interest["academicYear"]
                }).to_list(None)

                for lpa in lpa_records:
                    supervisor = await self.supervisors_collection.find_one({
                        "lecturer_id": lpa["lecturer"]
                    })
                    
                    if supervisor:
                        # Check capacity
                        current_students = await self.db["fyps"].count_documents({
                            "supervisor": supervisor["_id"]
                        })
                        max_students = supervisor.get("max_students", 5)
                        
                        if current_students < max_students:
                            # Calculate match score
                            match_score = self._calculate_supervisor_student_match_score(
                                interest, 
                                await self.db["students"].find_one({"_id": student_id}),
                                await self.project_areas_collection.find_one({"_id": project_area_id})
                            )
                            
                            matches.append({
                                "student_id": str(student_id),
                                "supervisor_id": str(supervisor["_id"]),
                                "project_area_id": str(project_area_id),
                                "match_score": match_score,
                                "supervisor_capacity": max_students - current_students
                            })

        # Sort by match score
        matches.sort(key=lambda x: x["match_score"], reverse=True)
        
        return matches
