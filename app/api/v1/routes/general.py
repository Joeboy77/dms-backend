from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime

from app.core.authentication.auth_middleware import RoleBasedAccessControl, get_current_token
from app.core.database import get_db
from app.schemas.token import TokenData

router = APIRouter(tags=["General"])

require_coordinator = RoleBasedAccessControl(["projects_coordinator"])


@router.get("/general/logs")
async def get_general_logs(
    pageNumber: int = Query(1, ge=1, alias="pageNumber"),
    pageSize: int = Query(10, ge=1, le=100, alias="pageSize"),
    search: Optional[str] = Query(None, alias="search"),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_coordinator)
):
    """
    Get all activity logs for coordinator dashboard.
    Returns logs in the format expected by the frontend.
    Supports search by description, action, and user_name.
    """
    try:
        skip = (pageNumber - 1) * pageSize
        
        query = {}
        if search:
            query["$or"] = [
                {"description": {"$regex": search, "$options": "i"}},
                {"action": {"$regex": search, "$options": "i"}},
                {"user_name": {"$regex": search, "$options": "i"}},
                {"details.message": {"$regex": search, "$options": "i"}}
            ]
        
        total_logs = await db["activity_logs"].count_documents(query)
        
        logs = await db["activity_logs"].find(
            query,
            {"_id": 1, "description": 1, "action": 1, "user_name": 1, "user_id": 1, "timestamp": 1, "createdAt": 1, "updatedAt": 1, "type": 1, "details": 1}
        ).sort("timestamp", -1).skip(skip).limit(pageSize).to_list(length=pageSize)
        
        formatted_logs = []
        for log in logs:
            log_description = log.get("description", "") or log.get("action", "")
            
            user_name = log.get("user_name", "System")
            
            timestamp = log.get("timestamp") or log.get("createdAt")
            
            details = log.get("details", {})
            
            formatted_logs.append({
                "id": str(log["_id"]),
                "action": log.get("action", ""),
                "description": log_description,
                "details": {
                    "message": log_description,
                    "status": "success" if log.get("type") != "error" else "error",
                    **details
                },
                "user_name": user_name,
                "user_id": str(log.get("user_id", "")),
                "type": log.get("type", "coordinator_action"),
                "timestamp": timestamp,
                "createdAt": timestamp,
                "updatedAt": log.get("updatedAt", timestamp)
            })
        
        return {
            "success": True,
            "data": {
                "logs": formatted_logs,
                "pagination": {
                    "pageNumber": pageNumber,
                    "pageSize": pageSize,
                    "totalCount": total_logs,
                    "totalPages": (total_logs + pageSize - 1) // pageSize
                }
            },
            "message": "Logs fetched successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching logs: {str(e)}")


@router.get("/general/logs/export")
async def export_all_logs(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_coordinator)
):
    """
    Get all activity logs for export (no pagination).
    Returns all logs in the format expected for CSV export.
    """
    try:
        logs = await db["activity_logs"].find(
            {},
            {"_id": 1, "description": 1, "action": 1, "user_name": 1, "user_id": 1, "timestamp": 1, "createdAt": 1, "updatedAt": 1, "type": 1, "details": 1}
        ).sort("timestamp", -1).to_list(None)
        
        formatted_logs = []
        for log in logs:
            log_description = log.get("description", "") or log.get("action", "")
            
            user_name = log.get("user_name", "System")
            
            timestamp = log.get("timestamp") or log.get("createdAt")
            
            details = log.get("details", {})
            
            formatted_logs.append({
                "id": str(log["_id"]),
                "action": log.get("action", ""),
                "description": log_description,
                "details": {
                    "message": log_description,
                    "status": "success" if log.get("type") != "error" else "error",
                    **details
                },
                "user_name": user_name,
                "user_id": str(log.get("user_id", "")),
                "type": log.get("type", "coordinator_action"),
                "timestamp": timestamp,
                "createdAt": timestamp,
                "updatedAt": log.get("updatedAt", timestamp)
            })
        
        return {
            "success": True,
            "data": {
                "logs": formatted_logs,
                "total": len(formatted_logs)
            },
            "message": "Logs fetched successfully for export"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching logs for export: {str(e)}")

