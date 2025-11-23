from fastapi import APIRouter, Depends, HTTPException, Query, responses
from typing import Optional, List, Dict
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.authentication.auth_middleware import get_current_token
from app.core.database import get_db
from app.schemas.reminders import ReminderCreate, ReminderPublic, ReminderUpdate, Page
from app.schemas.token import TokenData
from app.controllers.reminders import ReminderController

router = APIRouter(tags=["Reminders"])


@router.get("/reminders", response_model=Page)
async def get_all_reminders(
    limit: int = Query(10, alias="limit", ge=1, le=100),
    cursor: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = ReminderController(db)
    return await controller.get_all_reminders(limit=limit, cursor=cursor)


@router.get("/reminders/{id}", response_model=ReminderPublic)
async def get_reminder(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = ReminderController(db)
    return await controller.get_reminder_by_id(id)


@router.post("/reminders", response_model=ReminderPublic)
async def create_reminder(
    reminder: ReminderCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = ReminderController(db)
    reminder_data = reminder.model_dump()
    return await controller.create_reminder(reminder_data)


@router.patch("/reminders/{id}", response_model=ReminderPublic)
async def update_reminder(
    id: str,
    reminder: ReminderUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = ReminderController(db)
    update_data = reminder.model_dump()
    return await controller.update_reminder(id, update_data)


@router.delete("/reminders/{id}", status_code=204)
async def delete_reminder(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = ReminderController(db)
    await controller.delete_reminder(id)
    return responses.Response(status_code=204)


@router.get("/reminders/upcoming/{limit}", response_model=List[ReminderPublic])
async def get_upcoming_reminders(
    limit: int = 10,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = ReminderController(db)
    return await controller.get_upcoming_reminders(limit)


@router.get("/reminders/past/{limit}", response_model=List[ReminderPublic])
async def get_past_reminders(
    limit: int = 10,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = ReminderController(db)
    return await controller.get_past_reminders(limit)