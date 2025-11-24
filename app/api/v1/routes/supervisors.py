from fastapi import APIRouter, Depends, HTTPException, Query, responses
from typing import Optional, List, Dict
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.authentication.auth_middleware import get_current_token, RoleBasedAccessControl
from app.core.database import get_db
from app.schemas.supervisors import (
    SupervisorCreate,
    SupervisorPublic,
    SupervisorUpdate,
    Page,
    SupervisorWithLecturer,
    SupervisorWithLecturerDetails,
    StudentSupervisorResponse
)
from app.schemas.lecturers import LecturerPublic
from app.schemas.token import TokenData
from app.controllers.supervisors import SupervisorController

router = APIRouter(tags=["Supervisors"])

require_coordinator = RoleBasedAccessControl(["projects_coordinator"])


@router.get("/supervisors")
async def get_all_supervisors(
    limit: int = Query(10, alias="limit", ge=1, le=100),
    cursor: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_coordinator)
):
    controller = SupervisorController(db)
    return await controller.get_all_supervisors(limit=limit, cursor=cursor)


@router.get("/supervisors-with-details")
async def get_all_supervisors_with_lecturer_details(
    limit: int = Query(10, alias="limit", ge=1, le=100),
    cursor: Optional[str] = None,
    academic_year: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_coordinator)
):
    controller = SupervisorController(db)
    return await controller.get_all_supervisors_with_lecturer_details(limit=limit, cursor=cursor, academic_year=academic_year)


@router.get("/supervisors/{id}", response_model=SupervisorPublic)
async def get_supervisor(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = SupervisorController(db)
    return await controller.get_supervisor_by_id(id)


@router.post("/supervisors", response_model=SupervisorPublic)
async def create_supervisor(
    supervisor: SupervisorCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = SupervisorController(db)
    supervisor_data = supervisor.model_dump()
    return await controller.create_supervisor(supervisor_data)


@router.patch("/supervisors/{id}", response_model=SupervisorPublic)
async def update_supervisor(
    id: str,
    supervisor: SupervisorUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = SupervisorController(db)
    update_data = supervisor.model_dump()
    return await controller.update_supervisor(id, update_data)


@router.delete("/supervisors/{id}", status_code=204)
async def delete_supervisor(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = SupervisorController(db)
    await controller.delete_supervisor(id)
    return responses.Response(status_code=204)


@router.get("/supervisors/{id}/with-lecturer", response_model=SupervisorWithLecturer)
async def get_supervisor_with_lecturer(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = SupervisorController(db)
    return await controller.get_supervisor_with_lecturer(id)


@router.get("/supervisors/{id}/lecturer", response_model=LecturerPublic)
async def get_lecturer_by_supervisor_id(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = SupervisorController(db)
    return await controller.get_lecturer_by_supervisor_id(id)


@router.get("/supervisors/academic-year/{academic_year_id}", response_model=List[SupervisorPublic])
async def get_supervisors_by_academic_year(
    academic_year_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = SupervisorController(db)
    return await controller.get_supervisors_by_academic_year(academic_year_id)


@router.get("/supervisors/academic-year/{academic_year_id}/detailed")
async def get_supervisors_by_academic_year_detailed(
    academic_year_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = SupervisorController(db)
    return await controller.get_supervisors_by_academic_year_detailed(academic_year_id)


@router.get("/supervisors/student/{student_id}", response_model=StudentSupervisorResponse)
async def get_supervisor_by_student_id(
    student_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    """Get supervisor details for a specific student using their academic ID"""
    controller = SupervisorController(db)
    return await controller.get_supervisor_by_student_id(student_id)


@router.get("/supervisors/{supervisor_id}/with-students")
async def get_supervisor_with_students(
    supervisor_id: str,
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    project_status: Optional[str] = Query(None),
    academic_year: Optional[str] = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_coordinator)
):
    """
    Get supervisor details with all their students for coordinator dashboard.
    Includes student images, IDs, names, programs, and project status.
    Supports search and filtering by project status.
    """
    try:
        from app.controllers.students import StudentController
        from bson import ObjectId
        
        lecturer_id = None
        lecturer = None
        supervisor_details = None
        
        if ObjectId.is_valid(supervisor_id):
            supervisor_oid = ObjectId(supervisor_id)
            supervisor_doc = await db["supervisors"].find_one({"_id": supervisor_oid})
            
            if supervisor_doc:
                supervisor_controller = SupervisorController(db)
                try:
                    supervisor_details = await supervisor_controller.get_supervisor_by_id(supervisor_id)
                    lecturer_id = ObjectId(supervisor_details["lecturer_id"])
                except Exception:
                    lecturer_id = supervisor_doc.get("lecturer_id")
            else:
                lecturer = await db["lecturers"].find_one({"_id": supervisor_oid})
                if lecturer:
                    lecturer_id = lecturer["_id"]
                    supervisor_doc = await db["supervisors"].find_one({"lecturer_id": lecturer_id})
                    if supervisor_doc:
                        supervisor_controller = SupervisorController(db)
                        try:
                            supervisor_details = await supervisor_controller.get_supervisor_by_id(str(supervisor_doc["_id"]))
                        except Exception:
                            pass
        
        if not lecturer_id:
            raise HTTPException(status_code=404, detail="Supervisor or lecturer not found")
        
        if not lecturer:
            lecturer = await db["lecturers"].find_one({"_id": lecturer_id})
            if not lecturer:
                raise HTTPException(status_code=404, detail="Lecturer not found")
        
        checkin_id = None
        if academic_year:
            academic_year_doc = await db["academic_years"].find_one({"title": academic_year})
            if academic_year_doc:
                checkin = await db["fypcheckins"].find_one({"academicYear": academic_year_doc["_id"]})
                if checkin:
                    checkin_id = checkin["_id"]
        
        fyp_query = {
            "$or": [
                {"supervisor": lecturer_id},
                {"supervisor": str(lecturer_id)}
            ]
        }
        if checkin_id:
            fyp_query["checkin"] = checkin_id
        
        fyps = await db["fyps"].find(fyp_query).to_list(None)
        
        groups = await db["groups"].find({
            "$or": [
                {"supervisor": lecturer_id},
                {"supervisor": str(lecturer_id)}
            ],
            "status": {"$ne": "inactive"}
        }).to_list(None)
        
        students_data = []
        student_ids_seen = set()
        
        for fyp in fyps:
            student_id = fyp.get("student")
            if not student_id or str(student_id) in student_ids_seen:
                continue
            
            student_ids_seen.add(str(student_id))
            
            student = await db["students"].find_one({"_id": ObjectId(student_id) if isinstance(student_id, str) else student_id})
            if not student or student.get("deleted"):
                continue
            
            program = None
            if student.get("program"):
                program_field = student["program"]
                if isinstance(program_field, str) and ObjectId.is_valid(program_field):
                    program = await db["programs"].find_one({"_id": ObjectId(program_field)})
                elif isinstance(program_field, ObjectId):
                    program = await db["programs"].find_one({"_id": program_field})
            
            student_name = f"{student.get('surname', '')} {student.get('otherNames', '')}".strip()
            
            students_data.append({
                "student_id": str(student["_id"]),
                "student_name": student_name,
                "surname": student.get("surname", ""),
                "otherNames": student.get("otherNames", ""),
                "email": student.get("email", ""),
                "phone": student.get("phone", ""),
                "student_image": student.get("image", ""),
                "academicId": student.get("academicId", ""),
                "program": {
                    "program_id": str(program["_id"]) if program else None,
                    "title": program.get("title", "") if program else None,
                    "tag": program.get("tag", "") if program else None,
                    "description": program.get("description", "") if program else None,
                } if program else None,
            })
        
        for group in groups:
            members = group.get("members", []) or group.get("students", [])
            for member_id in members:
                if str(member_id) in student_ids_seen:
                    continue
                
                student_ids_seen.add(str(member_id))
                
                student = await db["students"].find_one({"_id": ObjectId(member_id) if isinstance(member_id, str) else member_id})
                if not student or student.get("deleted"):
                    continue
                
                program = None
                if student.get("program"):
                    program_field = student["program"]
                    if isinstance(program_field, str) and ObjectId.is_valid(program_field):
                        program = await db["programs"].find_one({"_id": ObjectId(program_field)})
                    elif isinstance(program_field, ObjectId):
                        program = await db["programs"].find_one({"_id": program_field})
                
                student_name = f"{student.get('surname', '')} {student.get('otherNames', '')}".strip()
                
                students_data.append({
                    "student_id": str(student["_id"]),
                    "student_name": student_name,
                    "surname": student.get("surname", ""),
                    "otherNames": student.get("otherNames", ""),
                    "email": student.get("email", ""),
                    "phone": student.get("phone", ""),
                    "student_image": student.get("image", ""),
                    "academicId": student.get("academicId", ""),
                    "program": {
                        "program_id": str(program["_id"]) if program else None,
                        "title": program.get("title", "") if program else None,
                        "tag": program.get("tag", "") if program else None,
                        "description": program.get("description", "") if program else None,
                    } if program else None,
                })
        
        for student in students_data:
            # This is a placeholder - you'll need to implement actual project status logic
            # based on your business rules (e.g., based on deliverables, submissions, etc.)
            student["project_status"] = "In Progress"  # Placeholder
        
        # Apply search filter if provided
        if search:
            students_data = [
                student for student in students_data
                if search.lower() in student.get("student_name", "").lower() or
                   search.lower() in student.get("academicId", "").lower()
            ]
        
        # Apply project status filter if provided
        if project_status:
            students_data = [
                student for student in students_data
                if student.get("project_status", "Not Started").lower() == project_status.lower()
            ]
        
        # Limit results
        students_data = students_data[:limit]
        
        lecturer_name = f"{lecturer.get('surname', '')} {lecturer.get('otherNames', '')}".strip() if lecturer else ""
        
        return {
            "supervisor": {
                "id": str(lecturer_id),
                "lecturer_id": str(lecturer_id),
                "name": lecturer_name,
                "lecturer_name": lecturer_name,
                "title": lecturer.get("title", "") if lecturer else "",
                "email": lecturer.get("email", "") if lecturer else "",
                "academic_id": lecturer.get("academicId", "") if lecturer else "",
                "max_students": supervisor_details.get("max_students", 5) if supervisor_details else lecturer.get("max_students", 5),
                "current_students": len(students_data)
            },
            "students": students_data,
            "pagination": {
                "current_page": 1,
                "per_page": limit,
                "total": len(students_data),
                "showing": f"1-{len(students_data)} of {len(students_data)}"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching supervisor with students: {str(e)}")