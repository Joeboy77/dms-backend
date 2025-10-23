from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_db
from app.core.authentication.auth_middleware import get_current_token, RoleBasedAccessControl, TokenData

router = APIRouter(tags=["Supervisor Stats"])

require_supervisor = RoleBasedAccessControl(["projects_supervisor", "projects_coordinator"])


@router.get("/supervisor/recent-activities")
async def get_supervisor_recent_activities(
    limit: int = Query(12, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_supervisor)
):
    """
    Get recent activities for project supervisor dashboard.
    Returns unified timeline of supervisor actions and their students' submissions.
    """
    try:
        from datetime import datetime, timedelta
        
        # Get supervisor's academic ID from token
        supervisor_academic_id = getattr(current_user, 'sub', 'LEC2025003')
        
        # Find supervisor in lecturers collection
        supervisor = await db["lecturers"].find_one({"academicId": supervisor_academic_id})
        if not supervisor:
            raise HTTPException(status_code=404, detail="Supervisor not found")
        
        supervisor_id = supervisor["_id"]
        
        # Get students assigned to this supervisor
        students_under_supervisor = await db["fyps"].find(
            {"supervisor_id": supervisor_id},
            {"student_id": 1}
        ).to_list(length=None)
        
        student_ids = [fyp["student_id"] for fyp in students_under_supervisor]
        
        # Get supervisor's own activity logs (if any)
        supervisor_activities = await db["activity_logs"].find(
            {"user_name": supervisor_academic_id},
            {"_id": 1, "description": 1, "timestamp": 1, "type": 1, "user_name": 1}
        ).sort("timestamp", -1).limit(limit * 2).to_list(length=limit * 2)
        
        # Get submissions from students under this supervisor
        recent_submissions = []
        if student_ids:
            recent_submissions = await db["submissions"].find(
                {"student_id": {"$in": student_ids}},
                {"_id": 1, "createdAt": 1, "status": 1, "group_id": 1, "deliverable_id": 1, "student_id": 1}
            ).sort("createdAt", -1).limit(limit * 2).to_list(length=limit * 2)
        
        # Format supervisor activities
        formatted_supervisor_activities = []
        for activity in supervisor_activities:
            formatted_supervisor_activities.append({
                "id": f"super_{str(activity['_id'])}",
                "description": activity.get("description", ""),
                "timestamp": activity.get("timestamp"),
                "type": activity.get("type", "supervisor_action"),
                "by": activity.get("user_name", "Supervisor"),
                "source": "supervisor"
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
        all_activities = formatted_supervisor_activities + formatted_student_activities
        all_activities.sort(key=lambda x: x["timestamp"], reverse=True)
        
        # Limit to requested number
        limited_activities = all_activities[:limit]
        
        # Get total count for pagination
        total_supervisor_activities = len(supervisor_activities)
        total_student_submissions = len(recent_submissions)
        total_activities = total_supervisor_activities + total_student_submissions
        
        return {
            "activities": limited_activities,
            "supervisor_info": {
                "academic_id": supervisor_academic_id,
                "name": f"{supervisor.get('surname', '')} {supervisor.get('otherNames', '')}".strip(),
                "students_count": len(student_ids)
            },
            "pagination": {
                "current_page": 1,
                "per_page": limit,
                "total": total_activities,
                "showing": f"1-{len(limited_activities)} of {total_activities}"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching supervisor recent activities: {str(e)}")


@router.get("/supervisor/student-stats")
async def get_supervisor_student_statistics(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_supervisor)
):
    """
    Get student statistics for the current supervisor.
    Returns total students, students with submissions, and students without submissions.
    """
    try:
        # Get supervisor's academic ID from token
        supervisor_academic_id = getattr(current_user, 'sub', 'LEC2025003')
        
        # Find supervisor in lecturers collection
        supervisor = await db["lecturers"].find_one({"academicId": supervisor_academic_id})
        if not supervisor:
            raise HTTPException(status_code=404, detail="Supervisor not found")
        
        supervisor_id = supervisor["_id"]
        
        # Get students assigned to this supervisor
        students_under_supervisor = await db["fyps"].find(
            {"supervisor_id": supervisor_id},
            {"student_id": 1}
        ).to_list(length=None)
        
        student_ids = [fyp["student_id"] for fyp in students_under_supervisor]
        total_students = len(student_ids)
        
        # Count students who have made submissions
        students_with_submissions = await db["submissions"].distinct(
            "student_id",
            {"student_id": {"$in": student_ids}}
        )
        students_with_submissions_count = len(students_with_submissions)
        
        # Calculate students without submissions
        students_without_submissions = total_students - students_with_submissions_count
        
        return {
            "total_students": total_students,
            "students_with_submissions": students_with_submissions_count,
            "students_without_submissions": students_without_submissions,
            "supervisor_info": {
                "academic_id": supervisor_academic_id,
                "name": f"{supervisor.get('surname', '')} {supervisor.get('otherNames', '')}".strip()
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching supervisor student statistics: {str(e)}")

