from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.authentication.auth_middleware import RoleBasedAccessControl, get_current_token
from app.core.database import get_db
from app.schemas.token import TokenData

router = APIRouter(tags=["Coordinator Logs"])

require_coordinator = RoleBasedAccessControl(["projects_coordinator"])


@router.get("/coordinator/logs")
async def get_coordinator_logs(
    limit: int = Query(12, ge=1, le=100),
    search: str = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_coordinator)
):
    """
    Get coordinator activity logs for the logs table view.
    Returns logs with Log, By, and Time columns as shown in the image.
    """
    try:
        query = {}
        if search:
            query["$or"] = [
                {"description": {"$regex": search, "$options": "i"}},
                {"action": {"$regex": search, "$options": "i"}},
                {"user_name": {"$regex": search, "$options": "i"}}
            ]
        
        total_logs = await db["activity_logs"].count_documents(query)
        
        logs = await db["activity_logs"].find(
            query,
            {"_id": 1, "description": 1, "action": 1, "user_name": 1, "timestamp": 1, "createdAt": 1, "type": 1}
        ).sort("timestamp", -1).limit(limit).to_list(length=limit)
        
        formatted_logs = []
        for log in logs:
            log_description = log.get("description", "") or log.get("action", "")
            
            user_name = log.get("user_name", "System")
            
            timestamp = log.get("timestamp") or log.get("createdAt")
            
            formatted_logs.append({
                "id": str(log["_id"]),
                "log": log_description,
                "by": user_name,
                "time": timestamp
            })
        
        return {
            "logs": formatted_logs,
            "pagination": {
                "current_page": 1,
                "per_page": limit,
                "total": total_logs,
                "showing": f"1-{len(formatted_logs)} of {total_logs}"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching coordinator logs: {str(e)}")


@router.post("/coordinator/logs")
async def create_coordinator_log(
    log_data: dict,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_coordinator)
):
    """
    Create a new activity log entry for coordinator actions.
    This can be called when coordinator performs actions like assigning students.
    """
    try:
        from datetime import datetime
        
        # Prepare log entry
        log_entry = {
            "description": log_data.get("description", ""),
            "action": log_data.get("action", ""),
            "user_name": getattr(current_user, 'sub', 'LEC2025003'),  # Coordinator's academic ID
            "user_id": getattr(current_user, 'id', '68f909ae2e6f85f29dbfc30b'),
            "type": log_data.get("type", "coordinator_action"),
            "timestamp": datetime.utcnow(),
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
            "details": log_data.get("details", {})
        }
        
        # Insert log entry
        result = await db["activity_logs"].insert_one(log_entry)
        
        return {
            "message": "Log entry created successfully",
            "log_id": str(result.inserted_id)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating log entry: {str(e)}")
