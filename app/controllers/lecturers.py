from datetime import datetime
from typing import Optional, List, Dict
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException
from app.core.authentication.hashing import get_hash


class LecturerController:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db["lecturers"]
        
        
    async def _get_or_create_project_area(self, title: str, lecturer_id: Optional[ObjectId] = None) -> ObjectId:
        title = (title or "").strip()
        if not title:
            raise ValueError("empty project area title")
        pa = await self.db["project_areas"].find_one({"title": title})
        now = datetime.utcnow()
        if pa:
            # add lecturer to interested_staff if provided
            if lecturer_id:
                await self.db["project_areas"].update_one(
                    {"_id": pa["_id"]},
                    {"$addToSet": {"interested_staff": lecturer_id}, "$set": {"updatedAt": now}}
                )
            return pa["_id"]
        # create new project area and record interested staff if provided
        res = await self.db["project_areas"].insert_one({
            "title": title,
            "description": "",
            "image": None,
            "interested_staff": [lecturer_id] if lecturer_id else [],
            "createdAt": now,
            "updatedAt": now
        })
        return res.inserted_id
    
    
    async def _sync_project_area_interested_staff(self, lecturer_id: ObjectId, new_pa_ids: List[ObjectId], old_pa_ids: Optional[List[ObjectId]] = None):
        """
        Ensure project_areas.interested_staff reflects lecturer membership:
         - add lecturer_id to any project areas in new_pa_ids
         - remove lecturer_id from any project areas in old_pa_ids that are not in new_pa_ids
        """
        new_set = {str(x) for x in (new_pa_ids or [])}
        old_set = {str(x) for x in (old_pa_ids or [])}

        to_add = [ObjectId(x) for x in new_set - old_set]
        to_remove = [ObjectId(x) for x in old_set - new_set]

        now = datetime.utcnow()
        for pa_oid in to_add:
            await self.db["project_areas"].update_one(
                {"_id": pa_oid},
                {"$addToSet": {"interested_staff": lecturer_id}, "$set": {"updatedAt": now}}
            )
        for pa_oid in to_remove:
            await self.db["project_areas"].update_one(
                {"_id": pa_oid},
                {"$pull": {"interested_staff": lecturer_id}, "$set": {"updatedAt": now}}
            )
    
    
    async def _normalize_project_areas_field(self, data: dict):
        """
        Convert data['projectAreas'] (list of titles or ids) into list of ObjectId refs.
        Creates missing project_area docs for string titles.
        """
        if "projectAreas" not in data or not data["projectAreas"]:
            data["projectAreas"] = []
            return

        new_ids = []
        for item in data["projectAreas"]:
            if isinstance(item, ObjectId):
                new_ids.append(item)
                continue
            # try as ObjectId string
            try:
                new_ids.append(ObjectId(item))
                continue
            except Exception:
                pass
            # treat as title -> create/lookup (no lecturer id here)
            pa_id = await self._get_or_create_project_area(str(item))
            new_ids.append(pa_id)

        data["projectAreas"] = new_ids
        
        
    async def _resolve_project_area_titles(self, lecturer_doc: dict) -> list:
        ids = lecturer_doc.get("projectAreas") or []
        if not ids:
            return []
        # ensure ObjectId list
        lookup_ids = []
        for i in ids:
            try:
                lookup_ids.append(i if isinstance(i, ObjectId) else ObjectId(i))
            except Exception:
                # skip invalid id
                continue
        pas = await self.db["project_areas"].find({"_id": {"$in": lookup_ids}}).to_list(None)
        # preserve order loosely by matching ids
        id_to_title = {str(p["_id"]): p.get("title", "") for p in pas}
        return [id_to_title.get(str(i), None) for i in lookup_ids if id_to_title.get(str(i))]
    

    async def get_all_lecturers(self, limit: int = 10, cursor: Optional[str] = None):
        query = {}
        if cursor:
            query["_id"] = {"$gt": ObjectId(cursor)}

        lecturers = await self.collection.find(query).limit(limit).to_list(limit)

        next_cursor = None
        if len(lecturers) == limit:
            next_cursor = str(lecturers[-1]["_id"])

        return {
            "items": lecturers,
            "next_cursor": next_cursor
        }
        
        

    async def get_lecturer_by_id(self, lecturer_id: str):
        lecturer = await self.collection.find_one({"_id": ObjectId(lecturer_id)})
        if not lecturer:
            raise HTTPException(status_code=404, detail="Lecturer not found")
        return lecturer

    async def get_lecturer_by_academic_id(self, academic_id: str):
        lecturer = await self.collection.find_one({"academicId": academic_id})
        if not lecturer:
            raise HTTPException(status_code=404, detail="Lecturer not found")
        return lecturer


    async def create_lecturer(self, lecturer_data: dict):
        lecturer_data["createdAt"] = datetime.now()
        lecturer_data["updatedAt"] = datetime.now()

        # Normalize project areas if present (convert titles -> ids; does NOT set interested_staff yet)
        if "projectAreas" in lecturer_data:
            await self._normalize_project_areas_field(lecturer_data)

        # --- NEW LOGIC: Ensure only one Project Coordinator exists ---
        position = lecturer_data.get("position", "").lower().strip()
        if position == "project coordinator":
            existing_coordinator = await self.collection.find_one({"position": "project coordinator"})
            if existing_coordinator:
                raise HTTPException(
                    status_code=400,
                    detail="A Project Coordinator already exists. Only one coordinator is allowed."
                )

        result = await self.collection.insert_one(lecturer_data)
        created_lecturer = await self.collection.find_one({"_id": result.inserted_id})

        try:
            raw_pa_ids = created_lecturer.get("projectAreas") or []
            await self._sync_project_area_interested_staff(created_lecturer["_id"], raw_pa_ids, old_pa_ids=[])
        except Exception:
            # don't fail creation on sync error
            pass

        # Resolve project area names for API response (after sync)
        if "projectAreas" in created_lecturer:
            created_lecturer["projectAreas"] = await self._resolve_project_area_titles(created_lecturer)

        return created_lecturer


    async def update_lecturer(self, lecturer_id: str, update_data: dict, current_pin: Optional[str] = None):
        update_data = {k: v for k, v in update_data.items() if v is not None}

        if not update_data:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        # If PIN is being updated, verify current PIN first
        if "pin" in update_data:
            if not current_pin:
                raise HTTPException(status_code=400, detail="Current PIN is required to change PIN")
            
            # Get current lecturer to verify PIN
            lecturer = await self.collection.find_one({"_id": ObjectId(lecturer_id)})
            if not lecturer:
                raise HTTPException(status_code=404, detail="Lecturer not found")
            

        update_data["updatedAt"] = datetime.now()

        result = await self.collection.update_one(
            {"_id": ObjectId(lecturer_id)},
            {"$set": update_data}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Lecturer not found")

        updated_lecturer = await self.collection.find_one({"_id": ObjectId(lecturer_id)})
        return updated_lecturer

    async def delete_lecturer(self, lecturer_id: str):
        result = await self.collection.delete_one({"_id": ObjectId(lecturer_id)})

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Lecturer not found")

        return {"message": "Lecturer deleted successfully"}

    async def search_lecturers_by_name(self, name: str):
        lecturers = await self.collection.find(
            {"name": {"$regex": name, "$options": "i"}}
        ).to_list(None)
        return lecturers

    async def get_lecturers_by_department(self, department: str):
        lecturers = await self.collection.find({"department": department}).to_list(None)
        return lecturers