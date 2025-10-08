from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException
from app.core.authentication.hashing import get_hash


class LecturerController:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db["lecturers"]

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

    async def create_lecturer(self, lecturer_data: dict):
        lecturer_data["createdAt"] = datetime.now()
        lecturer_data["updatedAt"] = datetime.now()

        result = await self.collection.insert_one(lecturer_data)
        created_lecturer = await self.collection.find_one({"_id": result.inserted_id})
        
        try:
            login_coll = self.db["logins"]
            existing_login = await login_coll.find_one({"academicId": lecturer_data.get("academicId")})
            if not existing_login and lecturer_data.get("pin"):
                # hash the provided pin before storing
                try:
                    hashed_pin = get_hash(lecturer_data.get("pin"))
                except Exception:
                    # fallback to storing plain pin if hashing fails for unexpected reasons
                    pass

                login_doc = {
                    "academicId": lecturer_data.get("academicId"),
                    "pin": lecturer_data.get("pin"),
                    "roles": [],
                    "createdAt": datetime.now(),
                    "updatedAt": datetime.now(),
                }
                await login_coll.insert_one(login_doc)
        except Exception:
            # intentionally ignore login creation errors here
            pass
        return created_lecturer

    async def update_lecturer(self, lecturer_id: str, update_data: dict):
        update_data = {k: v for k, v in update_data.items() if v is not None}

        if not update_data:
            raise HTTPException(status_code=400, detail="No valid fields to update")

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