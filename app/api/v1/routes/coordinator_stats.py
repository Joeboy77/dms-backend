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
