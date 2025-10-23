from fastapi import APIRouter, Depends, HTTPException, Query, responses
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


@router.get("/supervisors", response_model=Page)
async def get_all_supervisors(
    limit: int = Query(10, alias="limit", ge=1, le=100),
    cursor: str | None = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_coordinator)
):
    controller = SupervisorController(db)
    return await controller.get_all_supervisors(limit=limit, cursor=cursor)


@router.get("/supervisors-with-details")
async def get_all_supervisors_with_lecturer_details(
    limit: int = Query(10, alias="limit", ge=1, le=100),
    cursor: str | None = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_coordinator)
):
    controller = SupervisorController(db)
    return await controller.get_all_supervisors_with_lecturer_details(limit=limit, cursor=cursor)


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


@router.get("/supervisors/academic-year/{academic_year_id}", response_model=list[SupervisorPublic])
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