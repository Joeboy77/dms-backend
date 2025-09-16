from fastapi import APIRouter, Depends, HTTPException, Query, responses
from app.schemas.activity_logs import Page
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.controllers.activity_logs import ActivityLogController
from app.core.authentication.auth_middleware import get_current_token
from app.core.database import get_db
from app.schemas.token import TokenData

router = APIRouter(tags=["Activity Logs"])


@router.get("/activity_logs", response_model=Page)
async def get_all_logs(
    limit: int = Query(10, alias="limit", ge=1, le=100),
    cursor: str | None = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = ActivityLogController(db)
    return await controller.get_all_logs(limit=limit, cursor=cursor)
