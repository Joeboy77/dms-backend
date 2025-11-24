from datetime import datetime, date, time
from typing import Optional, List, Dict
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException


class DefensePanelController:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db["defense_panels"]

    async def create_panel(self, panel_data: dict, created_by: str):
        if not panel_data.get("lecturer_ids") or len(panel_data["lecturer_ids"]) == 0:
            raise HTTPException(status_code=400, detail="Panel must have at least one lecturer")
        
        for lecturer_id in panel_data["lecturer_ids"]:
            lecturer = await self.db["lecturers"].find_one({"_id": ObjectId(lecturer_id) if isinstance(lecturer_id, str) else lecturer_id})
            if not lecturer:
                raise HTTPException(status_code=404, detail=f"Lecturer with ID {lecturer_id} not found")
        
        panel_data["lecturer_ids"] = [
            ObjectId(lid) if isinstance(lid, str) else lid
            for lid in panel_data["lecturer_ids"]
        ]
        
        panel_data["createdAt"] = datetime.utcnow()
        panel_data["updatedAt"] = datetime.utcnow()
        panel_data["created_by"] = created_by
        
        result = await self.collection.insert_one(panel_data)
        return await self.get_panel_by_id(str(result.inserted_id))

    async def get_panel_by_id(self, panel_id: str):
        panel = await self.collection.find_one({"_id": ObjectId(panel_id)})
        if not panel:
            raise HTTPException(status_code=404, detail="Panel not found")
        
        lecturer_ids = panel.get("lecturer_ids", [])
        lecturers = await self.db["lecturers"].find(
            {"_id": {"$in": lecturer_ids}}
        ).to_list(None)
        
        panel["lecturer_ids"] = [str(lid) if isinstance(lid, ObjectId) else lid for lid in lecturer_ids]
        
        panel["lecturers"] = [
            {
                "_id": str(l["_id"]),
                "name": f"{l.get('title', '')} {l.get('surname', '')} {l.get('otherNames', '')}".strip(),
                "academicId": l.get("academicId", ""),
                "email": l.get("email", ""),
            }
            for l in lecturers
        ]
        
        return panel

    async def get_all_panels(self, limit: int = 100, cursor: Optional[str] = None):
        query = {}
        if cursor:
            query["_id"] = {"$gt": ObjectId(cursor)}

        panels = await self.collection.find(query).sort("createdAt", -1).limit(limit).to_list(limit)
        
        for panel in panels:
            panel["_id"] = str(panel["_id"])
            lecturer_ids = panel.get("lecturer_ids", [])
            panel["lecturer_ids"] = [str(lid) if isinstance(lid, ObjectId) else lid for lid in lecturer_ids]
            
            lecturers = await self.db["lecturers"].find(
                {"_id": {"$in": [ObjectId(lid) if isinstance(lid, str) else lid for lid in lecturer_ids]}}
            ).to_list(None)
            
            panel["lecturers"] = [
                {
                    "_id": str(l["_id"]),
                    "name": f"{l.get('title', '')} {l.get('surname', '')} {l.get('otherNames', '')}".strip(),
                    "academicId": l.get("academicId", ""),
                    "email": l.get("email", ""),
                }
                for l in lecturers
            ]
        
        next_cursor = None
        if len(panels) == limit:
            next_cursor = str(panels[-1]["_id"])

        return {
            "items": panels,
            "next_cursor": next_cursor
        }

    async def update_panel(self, panel_id: str, update_data: dict):
        panel = await self.collection.find_one({"_id": ObjectId(panel_id)})
        if not panel:
            raise HTTPException(status_code=404, detail="Panel not found")
        
        if "lecturer_ids" in update_data and update_data["lecturer_ids"]:
            if len(update_data["lecturer_ids"]) == 0:
                raise HTTPException(status_code=400, detail="Panel must have at least one lecturer")
            
            for lecturer_id in update_data["lecturer_ids"]:
                lecturer = await self.db["lecturers"].find_one({"_id": ObjectId(lecturer_id) if isinstance(lecturer_id, str) else lecturer_id})
                if not lecturer:
                    raise HTTPException(status_code=404, detail=f"Lecturer with ID {lecturer_id} not found")
            
            update_data["lecturer_ids"] = [
                ObjectId(lid) if isinstance(lid, str) else lid
                for lid in update_data["lecturer_ids"]
            ]
        
        update_data["updatedAt"] = datetime.utcnow()
        await self.collection.update_one(
            {"_id": ObjectId(panel_id)},
            {"$set": update_data}
        )
        
        return await self.get_panel_by_id(panel_id)

    async def delete_panel(self, panel_id: str):
        panel = await self.collection.find_one({"_id": ObjectId(panel_id)})
        if not panel:
            raise HTTPException(status_code=404, detail="Panel not found")
        
        existing_schedules = await self.db["defense_schedules"].count_documents({"panel_id": ObjectId(panel_id), "status": {"$ne": "cancelled"}})
        if existing_schedules > 0:
            raise HTTPException(status_code=400, detail="Cannot delete panel with active defense schedules")
        
        await self.collection.delete_one({"_id": ObjectId(panel_id)})
        return {"message": "Panel deleted successfully"}


class DefenseScheduleController:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db["defense_schedules"]

    def _parse_time(self, time_str: str) -> time:
        return datetime.strptime(time_str, "%H:%M").time()
    
    def _time_to_minutes(self, time_str: str) -> int:
        t = self._parse_time(time_str)
        return t.hour * 60 + t.minute
    
    def _check_time_overlap(self, start1: str, end1: str, start2: str, end2: str) -> bool:
        start1_min = self._time_to_minutes(start1)
        end1_min = self._time_to_minutes(end1)
        start2_min = self._time_to_minutes(start2)
        end2_min = self._time_to_minutes(end2)
        return not (end1_min <= start2_min or end2_min <= start1_min)
    
    async def create_schedule(self, schedule_data: dict, created_by: str, academic_year_id: Optional[str] = None):
        panel_id = schedule_data.get("panel_id")
        if isinstance(panel_id, str):
            panel_id = ObjectId(panel_id)
        
        panel = await self.db["defense_panels"].find_one({"_id": panel_id})
        if not panel:
            raise HTTPException(status_code=404, detail="Panel not found")
        
        panel_lecturer_ids = set(panel.get("lecturer_ids", []))
        
        student_ids = schedule_data.get("student_ids", [])
        group_ids = schedule_data.get("group_ids", [])
        time_slots = schedule_data.get("time_slots", [])
        
        if not student_ids and not group_ids:
            raise HTTPException(status_code=400, detail="Must select at least one student or group")
        
        if not time_slots or len(time_slots) == 0:
            raise HTTPException(status_code=400, detail="Must provide time slots for each student/group")
        
        defense_date = schedule_data.get("defense_date")
        if isinstance(defense_date, str):
            defense_date = datetime.fromisoformat(defense_date).date()
        
        if defense_date < date.today():
            raise HTTPException(status_code=400, detail="Cannot schedule defense in the past")
        
        defense_date_datetime = datetime.combine(defense_date, datetime.min.time())
        
        all_student_ids = set()
        selected_entities = set()
        
        for slot in time_slots:
            if slot.get("student_id"):
                student_id_obj = ObjectId(slot["student_id"]) if isinstance(slot["student_id"], str) else slot["student_id"]
                selected_entities.add(("student", str(student_id_obj)))
            elif slot.get("group_id"):
                group_id_obj = ObjectId(slot["group_id"]) if isinstance(slot["group_id"], str) else slot["group_id"]
                selected_entities.add(("group", str(group_id_obj)))
            
            start_time = slot.get("start_time")
            end_time = slot.get("end_time")
            
            if not start_time or not end_time:
                raise HTTPException(status_code=400, detail="Each time slot must have both start_time and end_time")
            
            if self._time_to_minutes(start_time) >= self._time_to_minutes(end_time):
                raise HTTPException(status_code=400, detail="Start time must be before end time")
        
        expected_entities = set()
        if student_ids:
            for student_id in student_ids:
                student_id_obj = ObjectId(student_id) if isinstance(student_id, str) else student_id
                expected_entities.add(("student", str(student_id_obj)))
        if group_ids:
            for group_id in group_ids:
                group_id_obj = ObjectId(group_id) if isinstance(group_id, str) else group_id
                expected_entities.add(("group", str(group_id_obj)))
        
        if selected_entities != expected_entities:
            raise HTTPException(status_code=400, detail="Time slots must include all selected students/groups")
        
        if student_ids:
            for student_id in student_ids:
                student_id_obj = ObjectId(student_id) if isinstance(student_id, str) else student_id
                student = await self.db["students"].find_one({"_id": student_id_obj})
                if not student:
                    raise HTTPException(status_code=404, detail=f"Student {student_id} not found")
                
                fyp = await self.db["fyps"].find_one({"student": student_id_obj})
                if fyp and fyp.get("supervisor"):
                    supervisor_id = fyp["supervisor"]
                    if isinstance(supervisor_id, str):
                        supervisor_id = ObjectId(supervisor_id)
                    if supervisor_id not in panel_lecturer_ids:
                        raise HTTPException(status_code=400, detail=f"Student's supervisor must be in the selected panel")
                
                all_student_ids.add(student_id_obj)
        
        if group_ids:
            for group_id in group_ids:
                group_id_obj = ObjectId(group_id) if isinstance(group_id, str) else group_id
                group = await self.db["groups"].find_one({"_id": group_id_obj})
                if not group:
                    raise HTTPException(status_code=404, detail=f"Group {group_id} not found")
                
                if group.get("supervisor"):
                    supervisor_id = group["supervisor"]
                    if isinstance(supervisor_id, str):
                        supervisor_id = ObjectId(supervisor_id)
                    if supervisor_id not in panel_lecturer_ids:
                        raise HTTPException(status_code=400, detail=f"Group's supervisor must be in the selected panel")
                
                group_members = group.get("members", []) or group.get("students", [])
                for member_id in group_members:
                    member_id_obj = ObjectId(member_id) if isinstance(member_id, str) else member_id
                    all_student_ids.add(member_id_obj)
        
        existing_schedules = await self.collection.find({
            "panel_id": panel_id,
            "status": {"$in": ["scheduled", "in_progress"]},
            "defense_date": defense_date_datetime
        }).to_list(None)
        
        for existing in existing_schedules:
            existing_slots = existing.get("time_slots", [])
            for existing_slot in existing_slots:
                existing_start = existing_slot.get("start_time")
                existing_end = existing_slot.get("end_time")
                if not existing_start or not existing_end:
                    continue
                
                for new_slot in time_slots:
                    new_start = new_slot.get("start_time")
                    new_end = new_slot.get("end_time")
                    if not new_start or not new_end:
                        continue
                    
                    if self._check_time_overlap(existing_start, existing_end, new_start, new_end):
                        raise HTTPException(
                            status_code=400,
                            detail=f"Time slot {new_start}-{new_end} conflicts with existing schedule {existing_start}-{existing_end} for this panel"
                        )
        
        all_other_panels = await self.db["defense_panels"].find({
            "_id": {"$ne": panel_id},
            "lecturer_ids": {"$in": list(panel_lecturer_ids)}
        }, {"_id": 1, "lecturer_ids": 1}).to_list(None)
        
        other_panel_ids = [p["_id"] for p in all_other_panels]
        
        if other_panel_ids:
            existing_lecturer_schedules = await self.collection.find({
                "panel_id": {"$in": other_panel_ids},
                "status": {"$in": ["scheduled", "in_progress"]},
                "defense_date": defense_date_datetime
            }).to_list(None)
            
            for existing_schedule in existing_lecturer_schedules:
                existing_slots = existing_schedule.get("time_slots", [])
                for existing_slot in existing_slots:
                    existing_start = existing_slot.get("start_time")
                    existing_end = existing_slot.get("end_time")
                    if not existing_start or not existing_end:
                        continue
                    
                    for new_slot in time_slots:
                        new_start = new_slot.get("start_time")
                        new_end = new_slot.get("end_time")
                        if not new_start or not new_end:
                            continue
                        
                        if self._check_time_overlap(existing_start, existing_end, new_start, new_end):
                            conflicting_panel = await self.db["defense_panels"].find_one({"_id": existing_schedule["panel_id"]})
                            conflicting_lecturer_ids = set(conflicting_panel.get("lecturer_ids", [])) if conflicting_panel else set()
                            common_lecturers = panel_lecturer_ids.intersection(conflicting_lecturer_ids)
                            if common_lecturers:
                                lecturer_id = list(common_lecturers)[0]
                                lecturer = await self.db["lecturers"].find_one({"_id": lecturer_id})
                                lecturer_name = f"{lecturer.get('title', '')} {lecturer.get('surname', '')} {lecturer.get('otherNames', '')}".strip() if lecturer else "Unknown"
                                raise HTTPException(
                                    status_code=400,
                                    detail=f"Panel member {lecturer_name} already has a defense scheduled at {existing_start}-{existing_end}. Time slot {new_start}-{new_end} conflicts."
                                )
        
        processed_time_slots = []
        for slot in time_slots:
            processed_slot = {
                "start_time": slot.get("start_time"),
                "end_time": slot.get("end_time")
            }
            if slot.get("student_id"):
                processed_slot["student_id"] = ObjectId(slot["student_id"]) if isinstance(slot["student_id"], str) else slot["student_id"]
            if slot.get("group_id"):
                processed_slot["group_id"] = ObjectId(slot["group_id"]) if isinstance(slot["group_id"], str) else slot["group_id"]
            processed_time_slots.append(processed_slot)
        
        if academic_year_id:
            if isinstance(academic_year_id, str):
                academic_year_id = ObjectId(academic_year_id)
            schedule_data["academic_year_id"] = academic_year_id
        
        schedule_data["panel_id"] = panel_id
        schedule_data["student_ids"] = list(all_student_ids)
        schedule_data["group_ids"] = [ObjectId(gid) if isinstance(gid, str) else gid for gid in group_ids]
        schedule_data["defense_date"] = defense_date_datetime
        schedule_data["time_slots"] = processed_time_slots
        schedule_data["status"] = "scheduled"
        schedule_data["createdAt"] = datetime.utcnow()
        schedule_data["updatedAt"] = datetime.utcnow()
        schedule_data["created_by"] = created_by
        
        result = await self.collection.insert_one(schedule_data)
        
        await self.db["activity_logs"].insert_one({
            "description": f"Created defense schedule for {len(all_student_ids)} student(s) on {defense_date}",
            "action": "defense_schedule_created",
            "user_name": created_by,
            "user_id": created_by,
            "type": "coordinator_action",
            "timestamp": datetime.utcnow(),
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
            "details": {
                "message": f"Created defense schedule for {len(all_student_ids)} student(s)",
                "status": "success",
                "defense_date": str(defense_date),
                "time_slots_count": len(processed_time_slots),
                "student_count": len(all_student_ids)
            }
        })
        
        return await self.get_schedule_by_id(str(result.inserted_id))

    async def get_schedule_by_id(self, schedule_id: str):
        schedule = await self.collection.find_one({"_id": ObjectId(schedule_id)})
        if not schedule:
            raise HTTPException(status_code=404, detail="Defense schedule not found")
        
        return await self._enrich_schedule(schedule)

    async def _enrich_schedule(self, schedule: dict):
        schedule["_id"] = str(schedule["_id"])
        
        panel = await self.db["defense_panels"].find_one({"_id": schedule.get("panel_id")})
        if panel:
            lecturers = await self.db["lecturers"].find(
                {"_id": {"$in": panel.get("lecturer_ids", [])}}
            ).to_list(None)
            
            schedule["panel"] = {
                "_id": str(panel["_id"]),
                "name": panel.get("name", ""),
                "lecturers": [
                    {
                        "_id": str(l["_id"]),
                        "name": f"{l.get('title', '')} {l.get('surname', '')} {l.get('otherNames', '')}".strip(),
                        "academicId": l.get("academicId", ""),
                        "email": l.get("email", ""),
                    }
                    for l in lecturers
                ]
            }
        
        schedule["panel_id"] = str(schedule.get("panel_id"))
        schedule["student_ids"] = [str(sid) if isinstance(sid, ObjectId) else sid for sid in schedule.get("student_ids", [])]
        schedule["group_ids"] = [str(gid) if isinstance(gid, ObjectId) else gid for gid in schedule.get("group_ids", [])]
        
        student_ids = schedule.get("student_ids", [])
        if student_ids:
            students = await self.db["students"].find(
                {"_id": {"$in": [ObjectId(sid) if isinstance(sid, str) else sid for sid in student_ids]}}
            ).to_list(None)
            
            schedule["students"] = [
                {
                    "_id": str(s["_id"]),
                    "name": f"{s.get('surname', '')} {s.get('otherNames', '')}".strip(),
                    "academicId": s.get("academicId", ""),
                    "program": str(s.get("program")) if isinstance(s.get("program"), ObjectId) else (s.get("program") if s.get("program") else ""),
                }
                for s in students
            ]
        
        group_ids = schedule.get("group_ids", [])
        if group_ids:
            groups = await self.db["groups"].find(
                {"_id": {"$in": [ObjectId(gid) if isinstance(gid, str) else gid for gid in group_ids]}}
            ).to_list(None)
            
            schedule["groups"] = [
                {
                    "_id": str(g["_id"]),
                    "name": g.get("name", ""),
                    "project_title": g.get("project_title", ""),
                    "members": [str(m) if isinstance(m, ObjectId) else m for m in g.get("members", []) or g.get("students", [])],
                    "member_count": len(g.get("members", []) or g.get("students", [])),
                }
                for g in groups
            ]
        
        time_slots = schedule.get("time_slots", [])
        enriched_time_slots = []
        for slot in time_slots:
            enriched_slot = {
                "start_time": slot.get("start_time", ""),
                "end_time": slot.get("end_time", ""),
            }
            
            if slot.get("student_id"):
                student_id = slot["student_id"]
                student_id_obj = ObjectId(student_id) if isinstance(student_id, str) else student_id
                student = await self.db["students"].find_one({"_id": student_id_obj})
                if student:
                    enriched_slot["student_id"] = str(student_id_obj)
                    program_id = student.get("program")
                    enriched_slot["student"] = {
                        "_id": str(student["_id"]),
                        "name": f"{student.get('surname', '')} {student.get('otherNames', '')}".strip(),
                        "academicId": student.get("academicId", ""),
                        "program": str(program_id) if isinstance(program_id, ObjectId) else (program_id if program_id else ""),
                    }
                else:
                    enriched_slot["student_id"] = str(student_id_obj) if isinstance(student_id_obj, ObjectId) else str(student_id)
            
            if slot.get("group_id"):
                group_id = slot["group_id"]
                group_id_obj = ObjectId(group_id) if isinstance(group_id, str) else group_id
                group = await self.db["groups"].find_one({"_id": group_id_obj})
                if group:
                    enriched_slot["group_id"] = str(group_id_obj)
                    enriched_slot["group"] = {
                        "_id": str(group["_id"]),
                        "name": group.get("name", ""),
                        "project_title": group.get("project_title", ""),
                        "member_count": len(group.get("members", []) or group.get("students", [])),
                    }
                else:
                    enriched_slot["group_id"] = str(group_id_obj) if isinstance(group_id_obj, ObjectId) else str(group_id)
            
            enriched_time_slots.append(enriched_slot)
        
        schedule["time_slots"] = enriched_time_slots
        
        if schedule.get("academic_year_id"):
            academic_year_id = schedule["academic_year_id"]
            schedule["academic_year_id"] = str(academic_year_id) if isinstance(academic_year_id, ObjectId) else academic_year_id
            academic_year = await self.db["academic_years"].find_one({"_id": academic_year_id})
            if academic_year:
                schedule["academic_year"] = {
                    "_id": str(academic_year["_id"]),
                    "title": academic_year.get("title", ""),
                    "year": academic_year.get("year", ""),
                }
        
        defense_date = schedule.get("defense_date")
        if isinstance(defense_date, datetime):
            schedule["defense_date"] = defense_date.date()
        
        return schedule

    async def get_all_schedules(self, limit: int = 50, cursor: Optional[str] = None, academic_year_id: Optional[str] = None, status: Optional[str] = None, panel_id: Optional[str] = None):
        query = {}
        if cursor:
            query["_id"] = {"$gt": ObjectId(cursor)}
        
        if academic_year_id:
            query["academic_year_id"] = ObjectId(academic_year_id) if isinstance(academic_year_id, str) else academic_year_id
        
        if status:
            query["status"] = status
        
        if panel_id:
            query["panel_id"] = ObjectId(panel_id) if isinstance(panel_id, str) else panel_id

        schedules = await self.collection.find(query).sort([("defense_date", 1), ("time_slots.start_time", 1)]).limit(limit).to_list(limit)
        
        enriched_schedules = []
        for schedule in schedules:
            enriched_schedules.append(await self._enrich_schedule(schedule))
        
        next_cursor = None
        if len(schedules) == limit:
            next_cursor = str(schedules[-1]["_id"])

        return {
            "items": enriched_schedules,
            "next_cursor": next_cursor
        }

    async def get_schedules_by_date(self, target_date: date, academic_year_id: Optional[str] = None):
        start_datetime = datetime.combine(target_date, datetime.min.time())
        end_datetime = datetime.combine(target_date, datetime.max.time())
        
        query = {
            "defense_date": {
                "$gte": start_datetime,
                "$lte": end_datetime
            }
        }
        
        if academic_year_id:
            query["academic_year_id"] = ObjectId(academic_year_id) if isinstance(academic_year_id, str) else academic_year_id
        
        schedules = await self.collection.find(query).sort("time_slots.start_time", 1).to_list(None)
        
        enriched_schedules = []
        for schedule in schedules:
            enriched_schedules.append(await self._enrich_schedule(schedule))
        
        return enriched_schedules

    async def get_calendar_markers(self, start_date: date, end_date: date, academic_year_id: Optional[str] = None):
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
        
        query = {
            "defense_date": {
                "$gte": start_datetime,
                "$lte": end_datetime
            }
        }
        
        if academic_year_id:
            query["academic_year_id"] = ObjectId(academic_year_id) if isinstance(academic_year_id, str) else academic_year_id
        
        schedules = await self.collection.find(query, {"defense_date": 1, "time_slots": 1, "status": 1}).to_list(None)
        
        markers = {}
        for schedule in schedules:
            defense_date = schedule.get("defense_date")
            if isinstance(defense_date, datetime):
                date_str = defense_date.date().isoformat()
            elif isinstance(defense_date, date):
                date_str = defense_date.isoformat()
            else:
                date_str = str(defense_date)
            
            if date_str not in markers:
                markers[date_str] = []
            
            time_slots = schedule.get("time_slots", [])
            if time_slots:
                for slot in time_slots:
                    markers[date_str].append({
                        "time": f"{slot.get('start_time', '')}-{slot.get('end_time', '')}",
                        "status": schedule.get("status", "scheduled")
                    })
            else:
                markers[date_str].append({
                    "time": "",
                    "status": schedule.get("status", "scheduled")
                })
        
        return markers

    async def update_schedule(self, schedule_id: str, update_data: dict, updated_by: str):
        schedule = await self.collection.find_one({"_id": ObjectId(schedule_id)})
        if not schedule:
            raise HTTPException(status_code=404, detail="Defense schedule not found")
        
        if "defense_date" in update_data:
            defense_date = update_data["defense_date"]
            if isinstance(defense_date, str):
                defense_date = datetime.fromisoformat(defense_date).date()
            
            if defense_date < date.today():
                raise HTTPException(status_code=400, detail="Cannot schedule defense in the past")
            
            defense_date_datetime = datetime.combine(defense_date, datetime.min.time())
            update_data["defense_date"] = defense_date_datetime
        
        if "panel_id" in update_data:
            panel_id = update_data["panel_id"]
            if isinstance(panel_id, str):
                panel_id = ObjectId(panel_id)
            
            panel = await self.db["defense_panels"].find_one({"_id": panel_id})
            if not panel:
                raise HTTPException(status_code=404, detail="Panel not found")
            
            update_data["panel_id"] = panel_id
        
        update_data["updatedAt"] = datetime.utcnow()
        await self.collection.update_one(
            {"_id": ObjectId(schedule_id)},
            {"$set": update_data}
        )
        
        await self.db["activity_logs"].insert_one({
            "description": f"Updated defense schedule {schedule_id}",
            "action": "defense_schedule_updated",
            "user_name": updated_by,
            "user_id": updated_by,
            "type": "coordinator_action",
            "timestamp": datetime.utcnow(),
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
            "details": {
                "message": f"Updated defense schedule",
                "status": "success",
                "schedule_id": schedule_id
            }
        })
        
        return await self.get_schedule_by_id(schedule_id)

    async def cancel_schedule(self, schedule_id: str, cancelled_by: str):
        schedule = await self.collection.find_one({"_id": ObjectId(schedule_id)})
        if not schedule:
            raise HTTPException(status_code=404, detail="Defense schedule not found")
        
        if schedule.get("status") == "cancelled":
            raise HTTPException(status_code=400, detail="Schedule is already cancelled")
        
        await self.collection.update_one(
            {"_id": ObjectId(schedule_id)},
            {"$set": {"status": "cancelled", "updatedAt": datetime.utcnow()}}
        )
        
        await self.db["activity_logs"].insert_one({
            "description": f"Cancelled defense schedule {schedule_id}",
            "action": "defense_schedule_cancelled",
            "user_name": cancelled_by,
            "user_id": cancelled_by,
            "type": "coordinator_action",
            "timestamp": datetime.utcnow(),
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
            "details": {
                "message": f"Cancelled defense schedule",
                "status": "success",
                "schedule_id": schedule_id
            }
        })
        
        return {"message": "Defense schedule cancelled successfully"}

    async def get_students_for_panel(self, panel_id: str, academic_year_id: Optional[str] = None):
        panel = await self.db["defense_panels"].find_one({"_id": ObjectId(panel_id)})
        if not panel:
            raise HTTPException(status_code=404, detail="Panel not found")
        
        panel_lecturer_ids = set(panel.get("lecturer_ids", []))
        
        checkin_id = None
        if academic_year_id:
            academic_year = await self.db["academic_years"].find_one({"_id": ObjectId(academic_year_id) if isinstance(academic_year_id, str) else academic_year_id})
            if academic_year:
                checkin = await self.db["fypcheckins"].find_one({"academicYear": academic_year["_id"]})
                if checkin:
                    checkin_id = checkin["_id"]
        
        fyp_query = {"supervisor": {"$in": list(panel_lecturer_ids)}}
        if checkin_id:
            fyp_query["checkin"] = checkin_id
        
        fyps = await self.db["fyps"].find(fyp_query).to_list(None)
        
        student_ids = set()
        for fyp in fyps:
            student_id = fyp.get("student")
            if student_id:
                student_ids.add(ObjectId(student_id) if isinstance(student_id, str) else student_id)
        
        groups = await self.db["groups"].find({
            "supervisor": {"$in": list(panel_lecturer_ids)},
            "status": {"$ne": "inactive"}
        }).to_list(None)
        
        group_ids = set()
        for group in groups:
            group_ids.add(group["_id"])
        
        students_data = []
        if student_ids:
            students = await self.db["students"].find({"_id": {"$in": list(student_ids)}}).to_list(None)
            
            for student in students:
                is_in_group = await self.db["groups"].find_one({
                    "$or": [
                        {"members": student["_id"]},
                        {"students": student["_id"]}
                    ],
                    "status": {"$ne": "inactive"}
                })
                
                if not is_in_group:
                    program = None
                    if student.get("program"):
                        program_field = student["program"]
                        if isinstance(program_field, str) and ObjectId.is_valid(program_field):
                            program = await self.db["programs"].find_one({"_id": ObjectId(program_field)})
                        elif isinstance(program_field, ObjectId):
                            program = await self.db["programs"].find_one({"_id": program_field})
                    
                    students_data.append({
                        "_id": str(student["_id"]),
                        "name": f"{student.get('surname', '')} {student.get('otherNames', '')}".strip(),
                        "academicId": student.get("academicId", ""),
                        "program": program.get("title", "") if program else "N/A",
                        "type": "individual"
                    })
        
        groups_data = []
        if group_ids:
            for group in groups:
                members = group.get("members", []) or group.get("students", [])
                member_names = []
                if members:
                    member_students = await self.db["students"].find({"_id": {"$in": members}}).to_list(None)
                    member_names = [
                        f"{s.get('surname', '')} {s.get('otherNames', '')}".strip()
                        for s in member_students
                    ]
                
                groups_data.append({
                    "_id": str(group["_id"]),
                    "name": group.get("name", ""),
                    "project_title": group.get("project_title", ""),
                    "members": member_names,
                    "member_count": len(members),
                    "type": "group"
                })
        
        scheduled_student_ids = set()
        scheduled_group_ids = set()
        
        existing_schedules = await self.collection.find({
            "status": {"$in": ["scheduled", "in_progress"]}
        }, {"student_ids": 1, "group_ids": 1}).to_list(None)
        
        for schedule in existing_schedules:
            scheduled_student_ids.update([ObjectId(sid) if isinstance(sid, str) else sid for sid in schedule.get("student_ids", [])])
            scheduled_group_ids.update([ObjectId(gid) if isinstance(gid, str) else gid for gid in schedule.get("group_ids", [])])
        
        available_students = [s for s in students_data if ObjectId(s["_id"]) not in scheduled_student_ids]
        available_groups = [g for g in groups_data if ObjectId(g["_id"]) not in scheduled_group_ids]
        
        return {
            "students": available_students,
            "groups": available_groups
        }

