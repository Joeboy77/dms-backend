from fastapi import APIRouter, Depends, HTTPException, Query, responses
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.authentication.auth_middleware import get_current_token
from app.core.database import get_db
from app.schemas.recent_activities import RecentActivityCreate, RecentActivityPublic, RecentActivityUpdate, Page
from app.schemas.token import TokenData
from app.controllers.recent_activities import RecentActivityController

router = APIRouter(tags=["Recent Activities"])


@router.get("/recent-activities", response_model=Page)
async def get_all_activities(
    limit: int = Query(10, alias="limit", ge=1, le=100),
    cursor: str | None = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = RecentActivityController(db)
    return await controller.get_all_activities(limit=limit, cursor=cursor)


@router.get("/recent-activities/{id}", response_model=RecentActivityPublic)
async def get_activity(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = RecentActivityController(db)
    return await controller.get_activity_by_id(id)


@router.post("/recent-activities", response_model=RecentActivityPublic)
async def create_activity(
    activity: RecentActivityCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = RecentActivityController(db)
    activity_data = activity.model_dump()
    return await controller.create_activity(activity_data)


@router.patch("/recent-activities/{id}", response_model=RecentActivityPublic)
async def update_activity(
    id: str,
    activity: RecentActivityUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = RecentActivityController(db)
    update_data = activity.model_dump()
    return await controller.update_activity(id, update_data)


@router.delete("/recent-activities/{id}", status_code=204)
async def delete_activity(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = RecentActivityController(db)
    await controller.delete_activity(id)
    return responses.Response(status_code=204)


@router.get("/recent-activities/user/{user_id}", response_model=list[RecentActivityPublic])
async def get_activities_by_user(
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = RecentActivityController(db)
    return await controller.get_activities_by_user(user_id)


@router.get("/recent-activities/recent/{limit}", response_model=list[RecentActivityPublic])
async def get_recent_activities(
    limit: int = 20,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = RecentActivityController(db)
    return await controller.get_recent_activities(limit)


@router.post("/recent-activities/seed")
async def seed_sample_data(
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = RecentActivityController(db)
    return await controller.seed_sample_data()