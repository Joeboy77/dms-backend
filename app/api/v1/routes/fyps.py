from fastapi import APIRouter, Depends, HTTPException, Query, responses
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.authentication.auth_middleware import get_current_token
from app.core.database import get_db
from app.schemas.fyps import FypCreate, FypPublic, FypPublicWithProjectArea, FypUpdate, Page, FypDashboard
from app.schemas.token import TokenData
from app.controllers.fyps import FypController

router = APIRouter(tags=["FYPs"])


@router.get("/fyps", response_model=Page)
async def get_all_fyps(
    limit: int = Query(10, alias="limit", ge=1, le=100),
    cursor: str | None = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = FypController(db)
    return await controller.get_all_fyps(limit=limit, cursor=cursor)


@router.get("/fyps/{id}", response_model=FypPublic)
async def get_fyp(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = FypController(db)
    return await controller.get_fyp_by_id(id)


@router.post("/fyps", response_model=FypPublic)
async def create_fyp(
    fyp: FypCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = FypController(db)
    fyp_data = fyp.model_dump()
    return await controller.create_fyp(fyp_data)


@router.patch("/fyps/{id}", response_model=FypPublic)
async def update_fyp(
    id: str,
    fyp: FypUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = FypController(db)
    update_data = fyp.model_dump()
    return await controller.update_fyp(id, update_data)


@router.delete("/fyps/{id}", status_code=204)
async def delete_fyp(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = FypController(db)
    await controller.delete_fyp(id)
    return responses.Response(status_code=204)


@router.get("/fyps/student/{student_id}", response_model=FypPublicWithProjectArea | None)
async def get_fyp_by_student(
    student_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = FypController(db)
    return await controller.get_fyps_by_student(student_id)


@router.get("/fyps/supervisor/{supervisor_id}", response_model=list[FypPublic])
async def get_fyps_by_supervisor(
    supervisor_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = FypController(db)
    return await controller.get_fyps_by_supervisor(supervisor_id)


@router.get("/fyps/project-area/{project_area_id}", response_model=list[FypPublic])
async def get_fyps_by_project_area(
    project_area_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = FypController(db)
    return await controller.get_fyps_by_project_area(project_area_id)


@router.get("/fyps/checkin/{checkin_id}", response_model=list[FypPublic])
async def get_fyps_by_checkin(
    checkin_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = FypController(db)
    return await controller.get_fyps_by_checkin(checkin_id)


@router.get("/fyps/dashboard/{student_id}", response_model=FypDashboard)
async def get_fyp_dashboard(
    student_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    """
    Get comprehensive dashboard data for a student's FYP.
    Returns aggregated data including supervisor info, project area, progress stages,
    deliverables, calendar events, and reminders.
    """
    controller = FypController(db)
    return await controller.get_dashboard_by_student(student_id)