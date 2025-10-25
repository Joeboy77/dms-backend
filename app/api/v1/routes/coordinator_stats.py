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
    page: int = 1,
    per_page: int = 12,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(require_coordinator)  # Temporarily disabled for testing
):
    """
    Get recent activities for project coordinator dashboard.
    Returns unified timeline of coordinator actions and student submissions.
    """
    try:
        from datetime import datetime, timedelta
        
        # Get coordinator activity logs
        coordinator_activities = await db["activity_logs"].find(
            {},
            {"_id": 1, "description": 1, "timestamp": 1, "type": 1, "user_name": 1}
        ).sort("timestamp", -1).limit(per_page * 2).to_list(length=per_page * 2)
        
        # Get recent student submissions
        recent_submissions = await db["submissions"].find(
            {},
            {"_id": 1, "createdAt": 1, "status": 1, "group_id": 1, "deliverable_id": 1, "student_id": 1}
        ).sort("createdAt", -1).limit(per_page * 2).to_list(length=per_page * 2)
        
        # Format coordinator activities
        formatted_coordinator_activities = []
        for activity in coordinator_activities:
            formatted_coordinator_activities.append({
                "id": f"coord_{str(activity['_id'])}",
                "description": activity.get("description", ""),
                "timestamp": activity.get("timestamp"),
                "type": activity.get("type", "coordinator_action"),
                "by": activity.get("user_name", "Coordinator"),
                "source": "coordinator"
            })
        
        # Format student submissions with student and deliverable details
        formatted_student_activities = []
        for submission in recent_submissions:
            # Get student details
            student = await db["students"].find_one({"_id": submission.get("student_id")})
            student_name = "Unknown Student"
            if student:
                student_name = f"{student.get('surname', '')} {student.get('otherNames', '')}".strip()
            
            # Get deliverable details
            deliverable = await db["deliverables"].find_one({"_id": submission.get("deliverable_id")})
            deliverable_name = "Unknown Deliverable"
            if deliverable:
                deliverable_name = deliverable.get("title", "Unknown Deliverable")
            
            # Get group details if applicable
            group_name = ""
            if submission.get("group_id"):
                group = await db["groups"].find_one({"_id": submission.get("group_id")})
                if group:
                    group_name = f" (Group: {group.get('name', 'Unknown Group')})"
            
            formatted_student_activities.append({
                "id": f"sub_{str(submission['_id'])}",
                "description": f"{student_name} submitted {deliverable_name}{group_name}",
                "timestamp": submission.get("createdAt"),
                "type": "student_submission",
                "by": student_name,
                "source": "student",
                "status": submission.get("status", "submitted")
            })
        
        # Combine and sort all activities by timestamp
        all_activities = formatted_coordinator_activities + formatted_student_activities
        # Sort by timestamp, handling None values
        all_activities.sort(key=lambda x: x["timestamp"] or datetime.min, reverse=True)
        
        # Limit to requested number
        limited_activities = all_activities[:per_page]
        
        # Get total count for pagination
        total_coordinator_activities = await db["activity_logs"].count_documents({})
        total_student_submissions = await db["submissions"].count_documents({})
        total_activities = total_coordinator_activities + total_student_submissions
        
        return {
            "activities": limited_activities,
            "pagination": {
                "current_page": page,
                "per_page": per_page,
                "total": total_activities,
                "showing": f"1-{len(limited_activities)} of {total_activities}"
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
