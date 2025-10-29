from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.authentication.auth_middleware import RoleBasedAccessControl, get_current_token
from app.core.database import get_db
from app.schemas.token import TokenData

router = APIRouter(tags=["Coordinator Project Areas"])

require_coordinator = RoleBasedAccessControl(["projects_coordinator"])


@router.get("/coordinator/project-areas")
async def get_project_areas_for_coordinator(
    limit: int = Query(20, ge=1, le=100),
    search: str = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_coordinator)
):
    """
    Get all project areas with interested staff for project coordinator dashboard.
    Returns project areas with staff details, similar to the grid view shown in the image.
    """
    try:
        from app.controllers.project_areas import ProjectAreaController
        
        controller = ProjectAreaController(db)
        result = await controller.get_all_project_area_with_interested_lecturers()
        
        project_areas = result.get("project_areas", [])
        lecturers = result.get("lecturers", [])
        
        lecturer_lookup = {lecturer["lecturer_id"]: lecturer for lecturer in lecturers}
        
        processed_areas = []
        for area in project_areas:
            interested_staff_ids = area.get("interested_staff", [])
            interested_staff_details = []
            
            for staff_id in interested_staff_ids:
                if staff_id in lecturer_lookup:
                    lecturer_info = lecturer_lookup[staff_id]
                    interested_staff_details.append({
                        "lecturer_id": lecturer_info["lecturer_id"],
                        "name": lecturer_info["name"],
                        "title": lecturer_info["title"],
                        "email": lecturer_info["email"],
                        "department": lecturer_info["department"]
                    })
            
            processed_area = {
                "id": str(area["_id"]),
                "title": area["title"],
                "description": area["description"],
                "image": area.get("image"),
                "interested_staff": interested_staff_details,
                "interested_staff_count": len(interested_staff_details),
                "created_at": area.get("createdAt"),
                "updated_at": area.get("updatedAt")
            }
            processed_areas.append(processed_area)
        
        # Apply search filter if provided
        if search:
            processed_areas = [
                area for area in processed_areas
                if search.lower() in area["title"].lower() or
                   search.lower() in area["description"].lower()
            ]
        
        # Limit results
        processed_areas = processed_areas[:limit]
        
        return {
            "project_areas": processed_areas,
            "pagination": {
                "current_page": 1,
                "per_page": limit,
                "total": len(processed_areas),
                "showing": f"1-{len(processed_areas)} of {len(processed_areas)}"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching project areas: {str(e)}")


@router.get("/coordinator/project-areas/{project_area_id}")
async def get_project_area_details_for_coordinator(
    project_area_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_coordinator)
):
    """
    Get detailed information about a specific project area for coordinator.
    Includes all interested staff and their details.
    """
    try:
        from app.controllers.project_areas import ProjectAreaController
        from bson import ObjectId
        
        controller = ProjectAreaController(db)
        
        project_area = await controller.get_project_area_by_id(project_area_id)
        
        lecturers = []
        for lecturer_id in project_area.get("interested_staff", []):
            lecturer = await db["lecturers"].find_one({"_id": lecturer_id})
            if lecturer:
                lecturers.append({
                    "lecturer_id": str(lecturer["_id"]),
                    "name": lecturer.get("name", ""),
                    "email": lecturer.get("email", ""),
                    "department": lecturer.get("department", ""),
                    "title": lecturer.get("title", ""),
                    "specialization": lecturer.get("specialization", "")
                })
        
        return {
            "project_area": {
                "id": str(project_area["_id"]),
                "title": project_area["title"],
                "description": project_area["description"],
                "image": project_area.get("image"),
                "interested_staff_count": len(lecturers),
                "created_at": project_area.get("createdAt"),
                "updated_at": project_area.get("updatedAt")
            },
            "lecturers": lecturers
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching project area details: {str(e)}")


@router.get("/coordinator/project-areas/{project_area_id}/students")
async def get_project_area_students_for_coordinator(
    project_area_id: str,
    limit: int = Query(20, ge=1, le=100),
    search: str = Query(None),
    project_status: str = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_coordinator)
):
    """
    Get students associated with a specific project area for coordinator.
    This is the endpoint for when "View project students" is clicked.
    Returns both interested staff and project students with search/filter capabilities.
    """
    try:
        from app.controllers.project_areas import ProjectAreaController
        from app.controllers.students import StudentController
        from bson import ObjectId
        
        controller = ProjectAreaController(db)
        project_area = await controller.get_project_area_by_id(project_area_id)
        
        interested_staff = []
        for lecturer_id in project_area.get("interested_staff", []):
            lecturer = await db["lecturers"].find_one({"_id": lecturer_id})
            if lecturer:
                interested_staff.append({
                    "lecturer_id": str(lecturer["_id"]),
                    "name": f"{lecturer.get('surname', '')} {lecturer.get('otherNames', '')}".strip(),
                    "title": lecturer.get("title", ""),
                    "email": lecturer.get("email", ""),
                    "department": lecturer.get("department", "Computer Science")
                })
        
        student_controller = StudentController(db)
        students_data = await student_controller.get_students_by_project_area(project_area_id)
        
        # Add project status to each student (placeholder implementation)
        for student in students_data:
            # This is a placeholder - you'll need to implement actual project status logic
            # based on your business rules (e.g., based on deliverables, submissions, etc.)
            student["project_status"] = "In Progress"  # Placeholder
        
        if search:
            students_data = [
                student for student in students_data
                if search.lower() in student.get("student_name", "").lower() or
                   search.lower() in student.get("academicId", "").lower()
            ]
        
        if project_status:
            students_data = [
                student for student in students_data
                if student.get("project_status", "Not Started").lower() == project_status.lower()
            ]
        
        students_data = students_data[:limit]
        
        return {
            "project_area": {
                "id": str(project_area["_id"]),
                "title": project_area["title"],
                "description": project_area["description"]
            },
            "interested_staff": interested_staff,
            "students": students_data,
            "pagination": {
                "current_page": 1,
                "per_page": limit,
                "total": len(students_data),
                "showing": f"1-{len(students_data)} of {len(students_data)}"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching project area students: {str(e)}")
