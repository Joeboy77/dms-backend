from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.authentication.auth_middleware import get_current_token, RoleBasedAccessControl
from app.schemas.token import TokenData

router = APIRouter(tags=["Coordinator Statistics"])

require_coordinator = RoleBasedAccessControl(["projects_coordinator"])


@router.get("/coordinator/student-stats")
async def get_student_statistics(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_coordinator)
):
    """
    Get student statistics for project coordinator:
    - Total students
    - Assigned students (have a supervisor)
    - Unassigned students (no supervisor)
    """
    try:
        total_students = await db["students"].count_documents({})
        
        assigned_students = await db["students"].count_documents({
            "supervisor": {"$exists": True, "$ne": None}
        })
        
        unassigned_students = await db["students"].count_documents({
            "$or": [
                {"supervisor": {"$exists": False}},
                {"supervisor": None},
                {"supervisor": ""}
            ]
        })
        
        return {
            "total_students": total_students,
            "assigned_students": assigned_students,
            "unassigned_students": unassigned_students
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching student statistics: {str(e)}")


@router.get("/coordinator/recent-activities")
async def get_recent_activities(
    limit: int = 12,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_coordinator)
):
    """
    Get recent activities for project coordinator dashboard.
    Returns paginated list of recent activities with pagination info.
    """
    try:
        total_activities = await db["activity_logs"].count_documents({})
        
        activities = await db["activity_logs"].find(
            {},
            {"_id": 1, "description": 1, "timestamp": 1, "type": 1}
        ).sort("timestamp", -1).limit(limit).to_list(length=limit)
        
        formatted_activities = []
        for activity in activities:
            formatted_activities.append({
                "id": str(activity["_id"]),
                "description": activity.get("description", ""),
                "timestamp": activity.get("timestamp"),
                "type": activity.get("type", "assignment")
            })
        
        return {
            "activities": formatted_activities,
            "pagination": {
                "current_page": 1,
                "per_page": limit,
                "total": total_activities,
                "showing": f"1-{len(formatted_activities)} of {total_activities}"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching recent activities: {str(e)}")


@router.get("/coordinator/reminders")
async def get_reminders(
    limit: int = 10,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_coordinator)
):
    """
    Get reminders for project coordinator dashboard.
    Returns upcoming reminders/events with dates and times.
    """
    try:
        from datetime import datetime, timedelta
        
        current_date = datetime.utcnow()
        
        total_reminders = await db["reminders"].count_documents({})
        
        reminders = await db["reminders"].find(
            {
                "date": {"$gte": current_date.strftime("%Y-%m-%d")}
            },
            {"_id": 1, "title": 1, "description": 1, "date": 1, "time": 1, "type": 1}
        ).sort("date", 1).limit(limit).to_list(length=limit)
        
        formatted_reminders = []
        for reminder in reminders:
            try:
                reminder_date = datetime.strptime(reminder.get("date", ""), "%Y-%m-%d")
                day_of_week = reminder_date.strftime("%A")
                formatted_date = reminder_date.strftime("%B %d")
            except:
                day_of_week = "Unknown"
                formatted_date = reminder.get("date", "")
            
            formatted_reminders.append({
                "id": str(reminder["_id"]),
                "title": reminder.get("title", ""),
                "description": reminder.get("description", ""),
                "date": reminder.get("date", ""),
                "formatted_date": formatted_date,
                "day_of_week": day_of_week,
                "time": reminder.get("time", "7:30 am"),
                "type": reminder.get("type", "reminder")
            })
        
        return {
            "reminders": formatted_reminders,
            "pagination": {
                "current_page": 1,
                "per_page": limit,
                "total": total_reminders,
                "showing": f"1-{len(formatted_reminders)} of {total_reminders}"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching reminders: {str(e)}")
