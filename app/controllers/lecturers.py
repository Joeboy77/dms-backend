from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException
from app.core.authentication.hashing import get_hash


class LecturerController:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db["lecturers"]
        
        
    async def _get_or_create_project_area(self, title: str) -> ObjectId:
        title = (title or "").strip()
        if not title:
            raise ValueError("empty project area title")
        pa = await self.db["project_areas"].find_one({"title": title})
        if pa:
            return pa["_id"]
        now = datetime.utcnow()
        res = await self.db["project_areas"].insert_one({
            "title": title,
            "description": "",
            "image": None,
            "createdAt": now,
            "updatedAt": now
        })
        return res.inserted_id
    
    
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
            # treat as title -> create/lookup
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
    

    async def get_all_lecturers(self, limit: int = 10, cursor: str | None = None):
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

        # Normalize project areas if present
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

        # Default all lecturers to supervisors
        # if not position:
        #     lecturer_data["position"] = "supervisor"

        # Insert the new lecturer
        result = await self.collection.insert_one(lecturer_data)
        created_lecturer = await self.collection.find_one({"_id": result.inserted_id})

        # Resolve project area names if present
        if "projectAreas" in created_lecturer:
            created_lecturer["projectAreas"] = await self._resolve_project_area_titles(created_lecturer)

        return created_lecturer


    async def update_lecturer(self, lecturer_id: str, update_data: dict, current_pin: str | None = None):
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
            
            stored_pin = lecturer.get("pin", "")
            
            # Verify current PIN
            from app.core.authentication.hashing import hash_verify
            try:
                is_valid = hash_verify(current_pin, stored_pin)
            except Exception:
                # Fallback to plain text comparison
                is_valid = current_pin == stored_pin
            
            if not is_valid:
                raise HTTPException(status_code=400, detail="Current PIN is incorrect")
            
            # Hash the new PIN
            update_data["pin"] = get_hash(update_data["pin"])

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