from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException

from app.schemas.announcements import AnnouncementCreate, AnnouncementUpdate, AnnouncementPublic


class AnnouncementController:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db["announcements"]

    async def create_announcement(self, announcement_data: AnnouncementCreate, supervisor_id: str):
        supervisor = await self.db["supervisors"].find_one({"_id": ObjectId(supervisor_id)})
        if not supervisor:
            raise HTTPException(status_code=404, detail="Supervisor not found")
        
        lecturer = await self.db["lecturers"].find_one({"_id": supervisor.get("lecturer_id")})
        if not lecturer:
            raise HTTPException(status_code=404, detail="Lecturer not found")
        
        supervisor_lecturer_id = lecturer["_id"]
        
        # Collect students from multiple sources
        all_student_ids = []
        
        # 1. FYP assignments (FYPs store lecturer's _id as "supervisor")
        fyp_assignments = await self.db["fyps"].find(
            {"supervisor": supervisor_lecturer_id},
            {"student": 1}
        ).to_list(length=None)
        
        student_ids_from_fyps = [fyp["student"] for fyp in fyp_assignments if fyp.get("student")]
        all_student_ids.extend(student_ids_from_fyps)
        
        # 2. Groups (groups also use lecturer_id as supervisor)
        supervisor_groups = await self.db["groups"].find(
            {"supervisor": supervisor_lecturer_id, "status": "active"},
            {"members": 1}
        ).to_list(length=None)
        
        for group in supervisor_groups:
            members = group.get("members", [])
            all_student_ids.extend(members)
        
        # Deduplicate student IDs while preserving ObjectId type
        seen = set()
        deduped_student_ids = []
        for sid in all_student_ids:
            sid_str = str(sid)
            if sid_str not in seen:
                seen.add(sid_str)
                deduped_student_ids.append(sid)
        
        valid_student_ids_set = seen
        
        # Debug logging
        print(f"[DEBUG Announcement] Supervisor ID: {supervisor_id}")
        print(f"[DEBUG Announcement] Lecturer ID: {supervisor_lecturer_id}")
        print(f"[DEBUG Announcement] Students from FYPs: {len(student_ids_from_fyps)}")
        print(f"[DEBUG Announcement] Groups found: {len(supervisor_groups)}")
        print(f"[DEBUG Announcement] Total unique students: {len(deduped_student_ids)}")
        
        # If no recipients provided, target ALL supervised students
        recipient_ids = []
        if not announcement_data.recipient_ids or len(announcement_data.recipient_ids) == 0:
            recipient_ids = deduped_student_ids.copy()
        else:
            for rid in announcement_data.recipient_ids:
                rid_str = str(rid)
                if rid_str in valid_student_ids_set:
                    try:
                        matching_id = None
                        for sid in deduped_student_ids:
                            if str(sid) == rid_str:
                                matching_id = sid
                                break
                        if matching_id:
                            recipient_ids.append(matching_id)
                    except Exception:
                        continue
        
        if not recipient_ids:
            raise HTTPException(
                status_code=400, 
                detail="No students assigned to this supervisor. Please assign students before sending announcements."
            )
        
        announcement_doc = {
            "subject": announcement_data.subject,
            "content": announcement_data.content,
            "sender_id": supervisor_lecturer_id,
            "recipient_ids": recipient_ids,
            "priority": announcement_data.priority,
            "attachments": announcement_data.attachments or [],
            "created_at": datetime.now(),
            "updated_at": None
        }
        
        result = await self.collection.insert_one(announcement_doc)
        announcement = await self.collection.find_one({"_id": result.inserted_id})
        return await self._format_announcement(announcement)

    async def get_supervisor_announcements(
        self,
        supervisor_id: str,
        limit: int = 20,
        cursor: str | None = None
    ):
        supervisor = await self.db["supervisors"].find_one({"_id": ObjectId(supervisor_id)})
        if not supervisor:
            raise HTTPException(status_code=404, detail="Supervisor not found")
        
        lecturer = await self.db["lecturers"].find_one({"_id": supervisor.get("lecturer_id")})
        if not lecturer:
            raise HTTPException(status_code=404, detail="Lecturer not found")
        
        query = {"sender_id": lecturer["_id"]}
        if cursor:
            query["_id"] = {"$lt": ObjectId(cursor)}
        
        announcements_docs = await self.collection.find(query).sort("created_at", -1).limit(limit).to_list(limit)
        
        announcements = []
        for doc in announcements_docs:
            announcement = await self._format_announcement(doc)
            announcements.append(announcement)
        
        next_cursor = None
        if len(announcements_docs) == limit:
            next_cursor = str(announcements_docs[-1]["_id"])
        
        return {
            "items": announcements,
            "next_cursor": next_cursor
        }

    async def get_student_announcements(
        self,
        student_id: str,
        limit: int = 20,
        cursor: str | None = None
    ):
        fyp = await self.db["fyps"].find_one(
            {"student": ObjectId(student_id)},
            sort=[("createdAt", -1)]
        )
        
        if not fyp or not fyp.get("supervisor"):
            return {"items": [], "next_cursor": None}
        
        supervisor = await self.db["supervisors"].find_one({"_id": fyp["supervisor"]})
        if not supervisor:
            return {"items": [], "next_cursor": None}
        
        lecturer = await self.db["lecturers"].find_one({"_id": supervisor.get("lecturer_id")})
        if not lecturer:
            return {"items": [], "next_cursor": None}
        
        query = {
            "sender_id": lecturer["_id"],
            "recipient_ids": {"$in": [ObjectId(student_id)]}
        }
        
        if cursor:
            query["_id"] = {"$lt": ObjectId(cursor)}
        
        announcements_docs = await self.collection.find(query).sort("created_at", -1).limit(limit).to_list(limit)
        
        announcements = []
        for doc in announcements_docs:
            announcement = await self._format_announcement(doc)
            announcements.append(announcement)
        
        next_cursor = None
        if len(announcements_docs) == limit:
            next_cursor = str(announcements_docs[-1]["_id"])
        
        return {
            "items": announcements,
            "next_cursor": next_cursor
        }

    async def get_announcement_by_id(self, announcement_id: str):
        announcement = await self.collection.find_one({"_id": ObjectId(announcement_id)})
        if not announcement:
            raise HTTPException(status_code=404, detail="Announcement not found")
        
        return await self._format_announcement(announcement)

    async def update_announcement(self, announcement_id: str, update_data: AnnouncementUpdate, supervisor_id: str):
        announcement = await self.collection.find_one({"_id": ObjectId(announcement_id)})
        if not announcement:
            raise HTTPException(status_code=404, detail="Announcement not found")
        
        supervisor = await self.db["supervisors"].find_one({"_id": ObjectId(supervisor_id)})
        if not supervisor:
            raise HTTPException(status_code=404, detail="Supervisor not found")
        
        lecturer = await self.db["lecturers"].find_one({"_id": supervisor.get("lecturer_id")})
        if not lecturer:
            raise HTTPException(status_code=404, detail="Lecturer not found")
        
        if announcement["sender_id"] != lecturer["_id"]:
            raise HTTPException(status_code=403, detail="Not authorized to update this announcement")
        
        update_doc = {}
        if update_data.subject is not None:
            update_doc["subject"] = update_data.subject
        if update_data.content is not None:
            update_doc["content"] = update_data.content
        if update_data.priority is not None:
            update_doc["priority"] = update_data.priority
        if update_data.attachments is not None:
            update_doc["attachments"] = update_data.attachments
        
        update_doc["updated_at"] = datetime.now()
        
        await self.collection.update_one(
            {"_id": ObjectId(announcement_id)},
            {"$set": update_doc}
        )
        
        updated_announcement = await self.collection.find_one({"_id": ObjectId(announcement_id)})
        return await self._format_announcement(updated_announcement)

    async def delete_announcement(self, announcement_id: str, supervisor_id: str):
        announcement = await self.collection.find_one({"_id": ObjectId(announcement_id)})
        if not announcement:
            raise HTTPException(status_code=404, detail="Announcement not found")
        
        supervisor = await self.db["supervisors"].find_one({"_id": ObjectId(supervisor_id)})
        if not supervisor:
            raise HTTPException(status_code=404, detail="Supervisor not found")
        
        lecturer = await self.db["lecturers"].find_one({"_id": supervisor.get("lecturer_id")})
        if not lecturer:
            raise HTTPException(status_code=404, detail="Lecturer not found")
        
        if announcement["sender_id"] != lecturer["_id"]:
            raise HTTPException(status_code=403, detail="Not authorized to delete this announcement")
        
        await self.collection.delete_one({"_id": ObjectId(announcement_id)})
        return {"message": "Announcement deleted successfully"}

    async def _format_announcement(self, doc: dict) -> dict:
        lecturer = await self.db["lecturers"].find_one({"_id": doc["sender_id"]})
        sender_name = f"{lecturer.get('surname', '')} {lecturer.get('otherNames', '')}".strip() if lecturer else "Unknown"
        sender_email = lecturer.get("email", "") if lecturer else ""
        
        recipients = []
        for recipient_id in doc.get("recipient_ids", []):
            student = await self.db["students"].find_one({"_id": recipient_id})
            if student:
                recipients.append({
                    "id": str(student["_id"]),
                    "name": f"{student.get('surname', '')} {student.get('otherNames', '')}".strip(),
                    "academic_id": student.get("academicId", "")
                })
        
        return {
            "id": str(doc["_id"]),
            "subject": doc.get("subject", ""),
            "content": doc.get("content", ""),
            "sender_id": str(doc["sender_id"]),
            "sender_name": sender_name,
            "sender_email": sender_email,
            "recipient_ids": [str(rid) for rid in doc.get("recipient_ids", [])],
            "recipients": recipients,
            "priority": doc.get("priority", "normal"),
            "attachments": doc.get("attachments", []),
            "created_at": doc.get("created_at"),
            "updated_at": doc.get("updated_at")
        }

