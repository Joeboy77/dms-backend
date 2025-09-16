from fastapi import APIRouter, Depends, HTTPException, Query, responses
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.authentication.auth_middleware import get_current_token
from app.core.database import get_db
from app.schemas.lecturer_project_areas import LecturerProjectAreaCreate, LecturerProjectAreaPublic, LecturerProjectAreaUpdate, Page, StudentInfoResponse
from app.schemas.token import TokenData
from app.controllers.lecturer_project_areas import LecturerProjectAreaController

router = APIRouter(tags=["Lecturer Project Areas"])


@router.get("/lecturer-project-areas", response_model=Page)
async def get_all_lecturer_project_areas(
    limit: int = Query(10, alias="limit", ge=1, le=100),
    cursor: str | None = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = LecturerProjectAreaController(db)
    return await controller.get_all_lecturer_project_areas(limit=limit, cursor=cursor)


@router.get("/lecturer-project-areas/{id}", response_model=LecturerProjectAreaPublic)
async def get_lecturer_project_area(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = LecturerProjectAreaController(db)
    return await controller.get_lecturer_project_area_by_id(id)


@router.post("/lecturer-project-areas", response_model=LecturerProjectAreaPublic)
async def create_lecturer_project_area(
    lpa: LecturerProjectAreaCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = LecturerProjectAreaController(db)
    lpa_data = lpa.model_dump()
    return await controller.create_lecturer_project_area(lpa_data)


@router.patch("/lecturer-project-areas/{id}", response_model=LecturerProjectAreaPublic)
async def update_lecturer_project_area(
    id: str,
    lpa: LecturerProjectAreaUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = LecturerProjectAreaController(db)
    update_data = lpa.model_dump()
    return await controller.update_lecturer_project_area(id, update_data)


@router.delete("/lecturer-project-areas/{id}", status_code=204)
async def delete_lecturer_project_area(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = LecturerProjectAreaController(db)
    await controller.delete_lecturer_project_area(id)
    return responses.Response(status_code=204)


@router.get("/lecturer-project-areas/lecturer/{lecturer_id}", response_model=list[LecturerProjectAreaPublic])
async def get_lecturer_project_areas_by_lecturer(
    lecturer_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = LecturerProjectAreaController(db)
    return await controller.get_by_lecturer(lecturer_id)


@router.get("/lecturer-project-areas/academic-year/{academic_year_id}", response_model=list[LecturerProjectAreaPublic])
async def get_lecturer_project_areas_by_academic_year(
    academic_year_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = LecturerProjectAreaController(db)
    return await controller.get_by_academic_year(academic_year_id)


@router.get("/students/{student_id}/info", response_model=StudentInfoResponse)
async def get_student_info_with_supervisor_and_project_area(
    student_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = LecturerProjectAreaController(db)
    return await controller.get_student_info_with_supervisor_and_project_area(student_id)