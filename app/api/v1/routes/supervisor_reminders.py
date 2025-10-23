from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_db
from app.core.authentication.auth_middleware import get_current_token, RoleBasedAccessControl, TokenData

router = APIRouter(tags=["Supervisor Reminders"])

require_supervisor = RoleBasedAccessControl(["projects_supervisor", "projects_coordinator"])


@router.get("/supervisor/reminders")
async def get_supervisor_reminders(
    limit: int = Query(10, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_supervisor)
):
    """
    Get reminders for project supervisor dashboard.
    Returns upcoming reminders/events with dates and times.
    """
    try:
        from datetime import datetime, timedelta
        

        supervisor_academic_id = getattr(current_user, 'sub', 'LEC2025003')
        
        supervisor = await db["lecturers"].find_one({"academicId": supervisor_academic_id})
        if not supervisor:
            raise HTTPException(status_code=404, detail="Supervisor not found")
        
        supervisor_id = supervisor["_id"]
        
        students_under_supervisor = await db["fyps"].find(
            {"supervisor_id": supervisor_id},
            {"student_id": 1}
        ).to_list(length=None)
        
        student_ids = [fyp["student_id"] for fyp in students_under_supervisor]
        
        current_date = datetime.utcnow()
        
        general_reminders = await db["reminders"].find(
            {
                "date_time": {"$gte": current_date},
                "supervisor_id": {"$exists": False}  # General reminders
            },
            {"_id": 1, "title": 1, "description": 1, "date_time": 1, "type": 1}
        ).sort("date_time", 1).limit(limit).to_list(length=limit)
        
        supervisor_reminders = await db["reminders"].find(
            {
                "date_time": {"$gte": current_date},
                "supervisor_id": supervisor_id
            },
            {"_id": 1, "title": 1, "description": 1, "date_time": 1, "type": 1}
        ).sort("date_time", 1).limit(limit).to_list(length=limit)
        
        student_reminders = []
        if student_ids:
            student_reminders = await db["reminders"].find(
                {
                    "date_time": {"$gte": current_date},
                    "student_id": {"$in": student_ids}
                },
                {"_id": 1, "title": 1, "description": 1, "date_time": 1, "type": 1}
            ).sort("date_time", 1).limit(limit).to_list(length=limit)
        
        all_reminders = general_reminders + supervisor_reminders + student_reminders
        
        unique_reminders = []
        seen_ids = set()
        for reminder in all_reminders:
            if str(reminder["_id"]) not in seen_ids:
                unique_reminders.append(reminder)
                seen_ids.add(str(reminder["_id"]))
        
        unique_reminders.sort(key=lambda x: x.get("date_time", datetime.min))
        limited_reminders = unique_reminders[:limit]
        
        formatted_reminders = []
        for reminder in limited_reminders:
            try:
                reminder_datetime = reminder.get("date_time")
                if isinstance(reminder_datetime, str):
                    reminder_datetime = datetime.fromisoformat(reminder_datetime.replace('Z', '+00:00'))
                
                date_str = reminder_datetime.strftime("%d %b").upper()  # "14 NOV"
                day_of_week = reminder_datetime.strftime("%A")  # "Tuesday"
                time_str = reminder_datetime.strftime("%I:%M %p").lower()  # "7:30 am"
                
            except:
                date_str = "Unknown"
                day_of_week = "Unknown"
                time_str = "7:30 am"
            
            formatted_reminders.append({
                "id": str(reminder["_id"]),
                "date": date_str,
                "title": reminder.get("title", ""),
                "day": day_of_week,
                "time": time_str,
                "description": reminder.get("description", ""),
                "type": reminder.get("type", "reminder")
            })
        
        total_reminders = await db["reminders"].count_documents({
            "date_time": {"$gte": current_date}
        })
        
        return {
            "reminders": formatted_reminders,
            "supervisor_info": {
                "academic_id": supervisor_academic_id,
                "name": f"{supervisor.get('surname', '')} {supervisor.get('otherNames', '')}".strip(),
                "students_count": len(student_ids)
            },
            "pagination": {
                "current_page": 1,
                "per_page": limit,
                "total": total_reminders,
                "showing": f"1-{len(formatted_reminders)} of {total_reminders}"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching supervisor reminders: {str(e)}")
