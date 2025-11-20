from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException


class FypController:
    """
    Controller for managing Final Year Projects (FYPs).
    
    FYPs are associated with groups of students and include project areas,
    supervisors, checkins, and deliverables tracking.
    """
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db["fyps"]
        self.project_areas_collection = db["project_areas"]

    def _validate_object_id(self, id_str: str, field_name: str = "ID") -> ObjectId:
        """Validate and convert string to ObjectId, raising appropriate error if invalid."""
        if not ObjectId.is_valid(id_str):
            raise HTTPException(status_code=400, detail=f"Invalid {field_name}: {id_str}")
        return ObjectId(id_str)

    async def get_all_fyps(self, limit: int = 10, cursor: str | None = None):
        query = {}
        if cursor:
            try:
                query["_id"] = {"$gt": self._validate_object_id(cursor, "cursor")}
            except HTTPException:
                raise HTTPException(status_code=400, detail=f"Invalid cursor: {cursor}")

        fyps = await self.collection.find(query).limit(limit).to_list(limit)

        next_cursor = None
        if len(fyps) == limit:
            next_cursor = str(fyps[-1]["_id"])

        return {
            "items": fyps,
            "next_cursor": next_cursor
        }

    async def get_fyp_by_id(self, fyp_id: str):
        try:
            fyp_oid = self._validate_object_id(fyp_id, "FYP ID")
        except HTTPException:
            raise

        fyp = await self.collection.find_one({"_id": fyp_oid})
        if not fyp:
            raise HTTPException(status_code=404, detail="FYP not found")
        return fyp

    async def create_fyp(self, fyp_data: dict):
        fyp_data["createdAt"] = datetime.utcnow()
        fyp_data["updatedAt"] = datetime.utcnow()

        # Normalize group field - handle both ObjectId and string
        group_field = fyp_data.get("group")
        if not group_field:
            raise HTTPException(status_code=400, detail="Group is required")
        
        # If it's a string, try to find group by name first, then by ObjectId
        if isinstance(group_field, str):
            if ObjectId.is_valid(group_field):
                group = await self.db["groups"].find_one({"_id": ObjectId(group_field)})
                if not group:
                    raise HTTPException(status_code=404, detail=f"Group with ID {group_field} not found")
                fyp_data["group"] = group["_id"]
            else:
                # Try to find by name
                group = await self.db["groups"].find_one({"name": group_field})
                if not group:
                    raise HTTPException(status_code=404, detail=f"Group with name '{group_field}' not found")
                fyp_data["group"] = group["_id"]
        elif isinstance(group_field, ObjectId):
            # Verify group exists
            group = await self.db["groups"].find_one({"_id": group_field})
            if not group:
                raise HTTPException(status_code=404, detail=f"Group with ID {group_field} not found")

        # Check if group already has an FYP - handle both ObjectId and string forms
        group_oid = fyp_data.get("group")
        if group_oid:
            existing_fyp = await self.collection.find_one(
                {
                    "$or": [
                        {"group": group_oid},
                        {"group": str(group_oid)}
                    ]
                }
            )
            if existing_fyp:
                raise HTTPException(status_code=400, detail="Group already has an FYP assigned")

        group = await self.db["groups"].find_one({"_id": group_oid})
        if not group:
            raise HTTPException(status_code=404, detail=f"Group with ID {group_oid} not found")
        fyp_data["supervisor"] = group.get("supervisor")

        # Normalize projectArea field if present
        project_area_field = fyp_data.get("projectArea")
        if project_area_field and isinstance(project_area_field, str):
            if ObjectId.is_valid(project_area_field):
                project_area_oid = ObjectId(project_area_field)
                # Verify project area exists
                project_area = await self.project_areas_collection.find_one({"_id": project_area_oid})
                if not project_area:
                    raise HTTPException(status_code=404, detail=f"Project area {project_area_field} not found")
                fyp_data["projectArea"] = project_area_oid
            else:
                raise HTTPException(status_code=400, detail=f"Invalid project area ID: {project_area_field}")
        elif project_area_field and isinstance(project_area_field, ObjectId):
            # Verify project area exists
            project_area = await self.project_areas_collection.find_one({"_id": project_area_field})
            if not project_area:
                raise HTTPException(status_code=404, detail=f"Project area with ID {project_area_field} not found")

        result = await self.collection.insert_one(fyp_data)
        created_fyp = await self.collection.find_one({"_id": result.inserted_id})
        return created_fyp

    async def update_fyp(self, fyp_id: str, update_data: dict):
        try:
            fyp_oid = self._validate_object_id(fyp_id, "FYP ID")
        except HTTPException:
            raise

        update_data = {k: v for k, v in update_data.items() if v is not None}

        if not update_data:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        # Normalize group field if being updated
        if "group" in update_data:
            group_field = update_data["group"]
            if isinstance(group_field, str):
                if ObjectId.is_valid(group_field):
                    group = await self.db["groups"].find_one({"_id": ObjectId(group_field)})
                    if not group:
                        raise HTTPException(status_code=404, detail=f"Group with ID {group_field} not found")
                    update_data["group"] = group["_id"]
                else:
                    # Try to find by name
                    group = await self.db["groups"].find_one({"name": group_field})
                    if not group:
                        raise HTTPException(status_code=404, detail=f"Group with name '{group_field}' not found")
                    update_data["group"] = group["_id"]
            elif isinstance(group_field, ObjectId):
                group = await self.db["groups"].find_one({"_id": group_field})
                if not group:
                    raise HTTPException(status_code=404, detail=f"Group with ID {group_field} not found")

            # Check if another FYP already exists for this group (excluding current FYP)
            group_oid = update_data["group"]
            existing_fyp = await self.collection.find_one(
                {
                    "_id": {"$ne": fyp_oid},
                    "$or": [
                        {"group": group_oid},
                        {"group": str(group_oid)}
                    ]
                }
            )
            if existing_fyp:
                raise HTTPException(status_code=400, detail="Group already has an FYP assigned")

        # Normalize supervisor field if being updated
        if "supervisor" in update_data:
            supervisor_field = update_data["supervisor"]
            if isinstance(supervisor_field, str):
                lecturer = await self.db["lecturers"].find_one({"academicId": supervisor_field})
                if not lecturer and ObjectId.is_valid(supervisor_field):
                    lecturer = await self.db["lecturers"].find_one({"_id": ObjectId(supervisor_field)})
                if not lecturer:
                    raise HTTPException(status_code=404, detail=f"Supervisor {supervisor_field} not found")
                update_data["supervisor"] = lecturer["_id"]
            elif isinstance(supervisor_field, ObjectId):
                lecturer = await self.db["lecturers"].find_one({"_id": supervisor_field})
                if not lecturer:
                    raise HTTPException(status_code=404, detail=f"Supervisor with ID {supervisor_field} not found")

        # Normalize projectArea field if being updated
        if "projectArea" in update_data:
            project_area_field = update_data["projectArea"]
            if isinstance(project_area_field, str):
                if ObjectId.is_valid(project_area_field):
                    project_area_oid = ObjectId(project_area_field)
                    project_area = await self.project_areas_collection.find_one({"_id": project_area_oid})
                    if not project_area:
                        raise HTTPException(status_code=404, detail=f"Project area {project_area_field} not found")
                    update_data["projectArea"] = project_area_oid
                else:
                    raise HTTPException(status_code=400, detail=f"Invalid project area ID: {project_area_field}")
            elif isinstance(project_area_field, ObjectId):
                project_area = await self.project_areas_collection.find_one({"_id": project_area_field})
                if not project_area:
                    raise HTTPException(status_code=404, detail=f"Project area with ID {project_area_field} not found")

        update_data["updatedAt"] = datetime.utcnow()

        result = await self.collection.update_one(
            {"_id": fyp_oid},
            {"$set": update_data}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="FYP not found")

        updated_fyp = await self.collection.find_one({"_id": fyp_oid})
        return updated_fyp

    async def delete_fyp(self, fyp_id: str):
        try:
            fyp_oid = self._validate_object_id(fyp_id, "FYP ID")
        except HTTPException:
            raise

        result = await self.collection.delete_one({"_id": fyp_oid})

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="FYP not found")

        return {"message": "FYP deleted successfully"}

    async def get_fyps_by_group(self, group_id: str):
        # Accept either group name or a Mongo ObjectId string
        if ObjectId.is_valid(group_id):
            group = await self.db["groups"].find_one({"_id": ObjectId(group_id)})
        else:
            # Try to find by name
            group = await self.db["groups"].find_one({"name": group_id})
        
        if not group:
            raise HTTPException(status_code=404, detail=f"Group {group_id} not found")

        # There should be at most one FYP per group; pick most recent if multiple
        # Handle both storage forms: ObjectId and stringified ObjectId
        group_oid = group["_id"]
        fyp = await self.collection.find_one(
            {
                "$or": [
                    {"group": group_oid},
                    {"group": str(group_oid)}
                ]
            },
            sort=[("createdAt", -1)]
        )
        if not fyp:
            raise HTTPException(status_code=404, detail=f"No FYP found for group {group_id}")

        # Populate single projectArea document in place of ObjectId
        project_area_id = fyp.get("projectArea")
        if project_area_id:
            if isinstance(project_area_id, str) and ObjectId.is_valid(project_area_id):
                project_area_id = ObjectId(project_area_id)
            project_area_doc = await self.project_areas_collection.find_one({"_id": project_area_id})
            if project_area_doc:
                fyp["projectArea"] = project_area_doc

        return fyp

    async def get_fyps_by_student(self, student_id: str):
        """
        Get Final Year Project (FYP) for a student by finding their group first.
        
        This method looks up the student's group and then retrieves the FYP
        associated with that group.
        """
        # Accept either academicId (e.g., CS2025001) or a Mongo ObjectId string
        student = await self.db["students"].find_one({"academicId": student_id})
        if not student and ObjectId.is_valid(student_id):
            student = await self.db["students"].find_one({"_id": ObjectId(student_id)})
        if not student:
            raise HTTPException(status_code=404, detail=f"Student {student_id} not found")

        student_oid = student["_id"]

        # Find group(s) the student belongs to
        groups = await self.db["groups"].find({
            "students": {"$in": [student_oid, str(student_oid)]}
        }).to_list(None)

        if not groups:
            raise HTTPException(status_code=404, detail=f"Student {student_id} is not in any group")

        # Use the first group (assuming one student can only be in one active group)
        group_oid = groups[0]["_id"]

        # Get FYP for the group
        fyp = await self.collection.find_one(
            {
                "$or": [
                    {"group": group_oid},
                    {"group": str(group_oid)}
                ]
            },
            sort=[("createdAt", -1)]
        )
        if not fyp:
            raise HTTPException(status_code=404, detail=f"No FYP found for student {student_id}'s group")

        # Populate single projectArea document in place of ObjectId
        project_area_id = fyp.get("projectArea")
        if project_area_id:
            if isinstance(project_area_id, str) and ObjectId.is_valid(project_area_id):
                project_area_id = ObjectId(project_area_id)
            project_area_doc = await self.project_areas_collection.find_one({"_id": project_area_id})
            if project_area_doc:
                fyp["projectArea"] = project_area_doc

        return fyp

    async def get_fyps_by_supervisor(self, supervisor_id: str):
        try:
            supervisor_oid = self._validate_object_id(supervisor_id, "Supervisor ID")
        except HTTPException:
            # Try to find supervisor by academicId (lecturer)
            lecturer = await self.db["lecturers"].find_one({"academicId": supervisor_id})
            if not lecturer:
                raise HTTPException(status_code=404, detail=f"Supervisor {supervisor_id} not found")
            # Find supervisor linked to lecturer
            supervisor = await self.db["supervisors"].find_one({"lecturer_id": lecturer["_id"]})
            if not supervisor:
                raise HTTPException(status_code=404, detail=f"Supervisor not found for lecturer {supervisor_id}")
            supervisor_oid = supervisor["_id"]
        
        # Handle both ObjectId and string forms
        fyps = await self.collection.find({
            "$or": [
                {"supervisor": supervisor_oid},
                {"supervisor": str(supervisor_oid)}
            ]
        }).to_list(None)
        return fyps

    async def get_fyps_by_project_area(self, project_area_id: str):
        try:
            project_area_oid = self._validate_object_id(project_area_id, "Project Area ID")
        except HTTPException:
            raise

        # Handle both ObjectId and string forms
        fyps = await self.collection.find({
            "$or": [
                {"projectArea": project_area_oid},
                {"projectArea": str(project_area_oid)}
            ]
        }).to_list(None)
        return fyps

    async def get_fyps_by_checkin(self, checkin_id: str):
        try:
            checkin_oid = self._validate_object_id(checkin_id, "Checkin ID")
        except HTTPException:
            raise

        # Handle both ObjectId and string forms
        fyps = await self.collection.find({
            "$or": [
                {"checkin": checkin_oid},
                {"checkin": str(checkin_oid)}
            ]
        }).to_list(None)
        return fyps

    async def get_dashboard_by_student(self, student_id: str):
        """
        Get comprehensive dashboard data for a student's Final Year Project (FYP).
        
        Aggregates data from FYP, deliverables, submissions, reminders, and related collections.
        Returns supervisor info, project area details, progress stages, deadlines, and calendar events.
        """
        from datetime import datetime
        from app.controllers.deliverables import DeliverableController
        from app.controllers.reminders import ReminderController
        
        # Step 1: Get FYP for student
        fyp = await self.get_fyps_by_student(student_id)
        if not fyp:
            raise HTTPException(status_code=404, detail=f"No FYP found for student {student_id}")

        # Step 2: Get group details and find student
        group_oid = fyp.get("group")
        if isinstance(group_oid, str) and ObjectId.is_valid(group_oid):
            group_oid = ObjectId(group_oid)
        elif not isinstance(group_oid, ObjectId):
            raise HTTPException(status_code=404, detail="FYP group not found")
        
        group = await self.db["groups"].find_one({"_id": group_oid})
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")

        # Find the student in the group
        student_oid = None
        if ObjectId.is_valid(student_id):
            student_oid = ObjectId(student_id)
        else:
            # Find student by academicId
            student = await self.db["students"].find_one({"academicId": student_id})
            if not student:
                raise HTTPException(status_code=404, detail="Student not found")
            student_oid = student["_id"]
        
        # Verify student is in the group - handle both ObjectId and string forms
        group_students = group.get("students", [])
        student_in_group = any(
            s == student_oid or (isinstance(s, ObjectId) and s == student_oid) or 
            (isinstance(s, str) and ObjectId.is_valid(s) and ObjectId(s) == student_oid) or
            str(s) == str(student_oid)
            for s in group_students
        )
        if not student_in_group:
            raise HTTPException(status_code=404, detail="Student is not in this FYP's group")
        
        student = await self.db["students"].find_one({"_id": student_oid})
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

        # Step 3: Get supervisor details
        supervisor_info = {}
        supervisor_oid = fyp.get("supervisor")
        if supervisor_oid:
            if isinstance(supervisor_oid, str) and ObjectId.is_valid(supervisor_oid):
                supervisor_oid = ObjectId(supervisor_oid)
            
            # Try to find lecturer directly
            lecturer = await self.db["lecturers"].find_one({"_id": supervisor_oid})
            
            # If not found, try through supervisors collection
            if not lecturer:
                supervisor = await self.db["supervisors"].find_one({"_id": supervisor_oid})
                if supervisor and supervisor.get("lecturer_id"):
                    lecturer = await self.db["lecturers"].find_one({"_id": supervisor["lecturer_id"]})
            
            if lecturer:
                # Resolve project areas if they're ObjectIds
                project_areas_list = lecturer.get("projectAreas", [])
                if project_areas_list and isinstance(project_areas_list[0] if project_areas_list else None, (ObjectId, str)):
                    # Resolve ObjectIds to titles
                    from app.controllers.lecturers import LecturerController
                    lecturer_controller = LecturerController(self.db)
                    project_areas_list = await lecturer_controller._resolve_project_area_titles(lecturer)
                
                area_of_interest = ", ".join(project_areas_list) if isinstance(project_areas_list, list) else str(project_areas_list or "")
                
                supervisor_info = {
                    "name": f"{lecturer.get('title', '')} {lecturer.get('surname', '')} {lecturer.get('otherNames', '')}".strip(),
                    "academicId": lecturer.get("academicId"),
                    "areaOfInterest": area_of_interest,
                    "email": lecturer.get("email"),
                    "title": lecturer.get("title"),
                    "department": lecturer.get("department", "Computer Science")
                }

        # Step 4: Get project area details
        project_area_info = {}
        project_area_id = fyp.get("projectArea")
        if project_area_id:
            if isinstance(project_area_id, dict):
                # Already populated
                project_area_info = {
                    "title": project_area_id.get("title", ""),
                    "description": project_area_id.get("description"),
                    "topic": fyp.get("topic")  # Topic might be stored in FYP
                }
            else:
                if isinstance(project_area_id, str) and ObjectId.is_valid(project_area_id):
                    project_area_id = ObjectId(project_area_id)
                project_area = await self.project_areas_collection.find_one({"_id": project_area_id})
                if project_area:
                    project_area_info = {
                        "title": project_area.get("title", ""),
                        "description": project_area.get("description"),
                        "topic": fyp.get("topic")  # Topic might be stored in FYP
                    }

        # Step 5: Get deliverables for student (this method handles group lookup internally)
        deliverable_controller = DeliverableController(self.db)
        deliverables_data = await deliverable_controller.get_deliverables_for_student(
            student.get("academicId") or str(student["_id"])
        )
        deliverables = deliverables_data.get("deliverables", [])

        # Step 6: Map deliverables to project stages and calculate progress
        stage_names = ["Proposal", "Chapter 1", "Chapter 2", "Chapter 3", "Chapter 4", "Chapter 5", "Final Doc"]
        stages = []
        stage_status_map = {}
        current_time = datetime.utcnow()

        # Helper function to parse datetime
        def parse_datetime(dt_value):
            if isinstance(dt_value, datetime):
                return dt_value
            if isinstance(dt_value, str):
                try:
                    return datetime.fromisoformat(dt_value.replace('Z', '+00:00'))
                except:
                    try:
                        return datetime.strptime(dt_value, "%Y-%m-%dT%H:%M:%S")
                    except:
                        return None
            return None
        
        # Helper function to determine deliverable status
        def get_deliverable_status(deliverable):
            end_date = parse_datetime(deliverable.get("end_date"))
            if not end_date:
                return "Not Started"
            
            has_submission = deliverable.get("student_submitted", False)
            start_date = parse_datetime(deliverable.get("start_date"))
            
            if has_submission and end_date < current_time:
                return "Completed"
            elif has_submission or (end_date >= current_time and start_date and start_date <= current_time):
                return "In Progress"
            else:
                return "Not Started"

        # Map deliverables to stages
        for deliverable in deliverables:
            name_lower = deliverable.get("name", "").lower()
            status = get_deliverable_status(deliverable)
            
            # Map deliverable to stage
            for i, stage_name in enumerate(stage_names):
                if "proposal" in name_lower and i == 0:
                    stage_status_map[stage_name] = status
                    break
                elif i > 0 and i < len(stage_names) - 1:  # Chapters 1-5
                    chapter_num = i  # i=1 for "Chapter 1", i=2 for "Chapter 2", etc.
                    if f"chapter {chapter_num}" in name_lower or f"chapter{chapter_num}" in name_lower:
                        stage_status_map[stage_name] = status
                        break
                elif "final" in name_lower and i == len(stage_names) - 1:
                    stage_status_map[stage_name] = status
                    break

        # Build stages list
        current_stage_index = -1
        for i, stage_name in enumerate(stage_names):
            status = stage_status_map.get(stage_name, "not_started")
            completed = status == "Completed"
            
            # Determine if locked (all previous stages must be completed)
            if i > 0 and current_stage_index == -1:
                prev_completed = all(
                    stage_status_map.get(stage_names[j], "not_started") == "Completed" 
                    for j in range(i)
                )
                if not prev_completed and status == "not_started":
                    status = "locked"
            
            if status in ["In Progress", "Completed"]:
                current_stage_index = i
            
            stages.append({
                "name": stage_name,
                "status": status,
                "completed": completed
            })

        # Calculate completion percentage
        completed_count = sum(1 for s in stages if s["status"] == "Completed")
        completion_percentage = (completed_count / len(stages)) * 100 if stages else 0

        # Find next deadline
        next_deadline = None
        upcoming_deadlines = []
        for deliverable in deliverables:
            end_date = parse_datetime(deliverable.get("end_date"))
            if not end_date:
                continue
            
            status = get_deliverable_status(deliverable)
            if status != "Completed" and end_date > current_time:
                upcoming_deadlines.append(end_date)
        
        if upcoming_deadlines:
            next_deadline = min(upcoming_deadlines)

        # Step 7: Build project progress list
        project_progress = []
        for deliverable in deliverables:
            end_date = parse_datetime(deliverable.get("end_date"))
            if not end_date:
                continue
            
            project_progress.append({
                "name": deliverable.get("name", ""),
                "deadline": end_date,
                "status": get_deliverable_status(deliverable)
            })

        # Step 8: Get reminders
        reminder_controller = ReminderController(self.db)
        upcoming_reminders = await reminder_controller.get_upcoming_reminders(limit=10)
        
        reminders = []
        for reminder in upcoming_reminders:
            date_time = parse_datetime(reminder.get("date_time"))
            if not date_time:
                continue
            
            # Format reminder date
            formatted = f"{date_time.strftime('%d %b').upper()}: {reminder.get('title', '')}, {date_time.strftime('%A, %I:%M %p').lower()}"
            
            reminders.append({
                "title": reminder.get("title", ""),
                "date": date_time,
                "formatted": formatted
            })

        # Step 9: Build calendar highlighted dates
        highlighted_dates = set()
        
        # Add deliverable deadlines
        for deliverable in deliverables:
            end_date = parse_datetime(deliverable.get("end_date"))
            if end_date:
                highlighted_dates.add(end_date.strftime("%Y-%m-%d"))
        
        # Add reminder dates
        for reminder in upcoming_reminders:
            date_time = parse_datetime(reminder.get("date_time"))
            if date_time:
                highlighted_dates.add(date_time.strftime("%Y-%m-%d"))

        # Step 10: Return aggregated dashboard data
        return {
            "supervisor": supervisor_info,
            "projectArea": project_area_info,
            "projectOverview": {
                "stages": stages,
                "completionPercentage": round(completion_percentage, 1),
                "nextDeadline": next_deadline
            },
            "projectProgress": project_progress,
            "calendar": {
                "highlightedDates": sorted(list(highlighted_dates)),
                "month": current_time.month,
                "year": current_time.year
            },
            "reminders": reminders
        }