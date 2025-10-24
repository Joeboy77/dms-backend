from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas.activity_logs import Page
from app.controllers.activity_logs import ActivityLogController
from app.core.authentication.auth_middleware import get_current_token
from app.core.database import get_db
from app.schemas.token import TokenData

router = APIRouter(tags=["Activity Logs"])

@router.get("/activity_logs", response_model=Page)
async def get_all_logs(
    limit: int = Query(10, ge=1, le=100),
    cursor: str | None = None,
    role: str | None = None,
    token: TokenData = Depends(get_current_token),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = ActivityLogController(db)
    return await controller.get_logs(token=token, limit=limit, cursor=cursor, role=role)
