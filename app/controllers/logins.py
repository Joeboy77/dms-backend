from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException


class LoginController:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db["logins"]

    async def get_all_logins(self, limit: int = 10, cursor: str | None = None):
        query = {}
        if cursor:
            query["_id"] = {"$gt": ObjectId(cursor)}

        logins = await self.collection.find(query).limit(limit).to_list(limit)

        next_cursor = None
        if len(logins) == limit:
            next_cursor = str(logins[-1]["_id"])

        return {
            "items": logins,
            "next_cursor": next_cursor
        }

    async def get_login_by_id(self, login_id: str):
        login = await self.collection.find_one({"_id": ObjectId(login_id)})
        if not login:
            raise HTTPException(status_code=404, detail="Login not found")
        return login

    async def get_login_by_academic_id(self, academic_id: str):
        login = await self.collection.find_one({"academicId": academic_id})
        if not login:
            raise HTTPException(status_code=404, detail="Login not found for academic ID")
        return login

    async def create_login(self, login_data: dict):
        login_data["createdAt"] = datetime.now()
        login_data["updatedAt"] = datetime.now()

        # Check if academic ID already exists
        existing_login = await self.collection.find_one({"academicId": login_data["academicId"]})
        if existing_login:
            raise HTTPException(status_code=400, detail="Login already exists for this academic ID")

        result = await self.collection.insert_one(login_data)
        created_login = await self.collection.find_one({"_id": result.inserted_id})
        return created_login

    async def update_login(self, login_id: str, update_data: dict):
        update_data = {k: v for k, v in update_data.items() if v is not None}

        if not update_data:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        update_data["updatedAt"] = datetime.now()

        result = await self.collection.update_one(
            {"_id": ObjectId(login_id)},
            {"$set": update_data}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Login not found")

        updated_login = await self.collection.find_one({"_id": ObjectId(login_id)})
        return updated_login

    async def delete_login(self, login_id: str):
        result = await self.collection.delete_one({"_id": ObjectId(login_id)})

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Login not found")

        return {"message": "Login deleted successfully"}

    async def check_user_has_role(self, academic_id: str, role_id: str):
        login = await self.collection.find_one({
            "academicId": academic_id,
            "roles": ObjectId(role_id)
        })
        return login is not None

    async def get_users_with_role(self, role_id: str):
        logins = await self.collection.find({"roles": ObjectId(role_id)}).to_list(None)
        return logins

    async def get_login_with_role_details(self, academic_id: str):
        login = await self.get_login_by_academic_id(academic_id)

        # Get role details
        role_details = []
        for role_id in login.get("roles", []):
            role = await self.db["roles"].find_one({"_id": role_id})
            if role:
                role_details.append({
                    "role_id": str(role["_id"]),
                    "title": role.get("title", ""),
                    "slug": role.get("slug", ""),
                    "status": role.get("status", ""),
                    "description": role.get("description", ""),
                    "deleted": role.get("deleted", False)
                })

        return {
            "login": login,
            "role_details": role_details
        }