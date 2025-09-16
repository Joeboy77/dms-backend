from fastapi import APIRouter, Depends, HTTPException, Query, responses
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.authentication.auth_middleware import get_current_token
from app.core.database import get_db
from app.schemas.fypcheckins import FypCheckinCreate, FypCheckinPublic, FypCheckinUpdate, Page
from app.schemas.token import TokenData
from app.controllers.fypcheckins import FypCheckinController

router = APIRouter(tags=["FYP Checkins"])


@router.get("/fyp-checkins", response_model=Page)
async def get_all_checkins(
    limit: int = Query(10, alias="limit", ge=1, le=100),
    cursor: str | None = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = FypCheckinController(db)
    return await controller.get_all_checkins(limit=limit, cursor=cursor)


@router.get("/fyp-checkins/{id}", response_model=FypCheckinPublic)
async def get_checkin(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(get_current_token),
):
    controller = FypCheckinController(db)
    return await controller.get_checkin_by_id(id)


@router.post("/fyp-checkins", response_model=FypCheckinPublic)
async def create_checkin(
    checkin: FypCheckinCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(get_current_token),
):
    controller = FypCheckinController(db)
    checkin_data = checkin.model_dump()
    return await controller.create_checkin(checkin_data)


@router.patch("/fyp-checkins/{id}", response_model=FypCheckinPublic)
async def update_checkin(
    id: str,
    checkin: FypCheckinUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(get_current_token),
):
    controller = FypCheckinController(db)
    update_data = checkin.model_dump()
    return await controller.update_checkin(id, update_data)


@router.delete("/fyp-checkins/{id}", status_code=204)
async def delete_checkin(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(get_current_token),
):
    controller = FypCheckinController(db)
    await controller.delete_checkin(id)
    return responses.Response(status_code=204)


@router.get("/fyp-checkins/academic-year/{academic_year_id}", response_model=list[FypCheckinPublic])
async def get_checkins_by_academic_year(
    academic_year_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(get_current_token),
):
    controller = FypCheckinController(db)
    return await controller.get_checkins_by_academic_year(academic_year_id)


@router.get("/fyp-checkins/active", response_model=list[FypCheckinPublic])
async def get_active_checkins(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(get_current_token),
):
    controller = FypCheckinController(db)
    return await controller.get_active_checkins()