from datetime import datetime
from typing import Optional, List, Dict
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException


class ProjectController:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db["projects"]
        
        
    async def get_all_projects(self, limit: int = 10, cursor: Optional[str] = None):
        query = {}
        if cursor:
            query["_id"] = {"$gt": ObjectId(cursor)}

        projects = await self.collection.find(query).sort("createdAt", 1).limit(limit).to_list(limit)

        next_cursor = None
        if len(projects) == limit:
            next_cursor = str(projects[-1]["_id"])

        return {
            "items": projects,
            "next_cursor": next_cursor
        }
        
        
    async def get_project_by_id(self, project_id: str):
        project = await self.collection.find_one({"_id": ObjectId(project_id)})
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project
    
    
    async def create_project(self, project_data: dict):
        project_data["createdAt"] = datetime.now()
        project_data["updatedAt"] = None

        result = await self.collection.insert_one(project_data)
        created_project = await self.collection.find_one({"_id": result.inserted_id})
        return created_project
    
    
    
    async def update_project(self, project_id: str, update_data: dict):
        update_data = {k: v for k, v in update_data.items() if v is not None}

        if not update_data:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        update_data["updatedAt"] = datetime.now()

        result = await self.collection.update_one(
            {"_id": ObjectId(project_id)},
            {"$set": update_data}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Project not found")

        updated_project = await self.collection.find_one({"_id": ObjectId(project_id)})
        return updated_project
    
    
    async def delete_project(self, project_id: str):
        result = await self.collection.delete_one({"_id": ObjectId(project_id)})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Project not found")
        return {"detail": "Project deleted successfully"}
    
    
    
    async def get_projects_by_group(self, group_id: str):
        projects = await self.collection.find({"group_id": ObjectId(group_id)}).to_list(100)
        return projects
    
    
    async def get_projects_within_date_range(self, start_date: datetime, end_date: datetime):
        projects = await self.collection.find({
            "createdAt": {
                "$gte": start_date,
                "$lte": end_date
            }
        }).to_list(100)
        return projects
    
    
    async def count_projects(self):
        count = await self.collection.count_documents({})
        return count