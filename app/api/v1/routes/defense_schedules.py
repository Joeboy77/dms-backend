from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from datetime import date
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.authentication.auth_middleware import RoleBasedAccessControl, get_current_token
from app.core.database import get_db
from app.schemas.token import TokenData
from app.schemas.defense_schedules import (
    DefensePanelCreate,
    DefensePanelUpdate,
    DefensePanelPublic,
    DefenseScheduleCreate,
    DefenseScheduleUpdate,
    DefenseSchedulePublic,
    Page,
    PanelPage
)
from app.controllers.defense_schedules import DefensePanelController, DefenseScheduleController

router = APIRouter(tags=["Defense Schedules"])

require_coordinator = RoleBasedAccessControl(["projects_coordinator"])


@router.post("/defense-panels", response_model=DefensePanelPublic)
async def create_defense_panel(
    panel_data: DefensePanelCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_coordinator)
):
    controller = DefensePanelController(db)
    return await controller.create_panel(panel_data.dict(), current_user.email)


@router.get("/defense-panels", response_model=PanelPage)
async def get_all_panels(
    limit: int = Query(100, ge=1, le=100),
    cursor: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_coordinator)
):
    controller = DefensePanelController(db)
    return await controller.get_all_panels(limit=limit, cursor=cursor)


@router.get("/defense-panels/{panel_id}", response_model=DefensePanelPublic)
async def get_panel(
    panel_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_coordinator)
):
    controller = DefensePanelController(db)
    return await controller.get_panel_by_id(panel_id)


@router.patch("/defense-panels/{panel_id}", response_model=DefensePanelPublic)
async def update_panel(
    panel_id: str,
    panel_data: DefensePanelUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_coordinator)
):
    controller = DefensePanelController(db)
    update_dict = {k: v for k, v in panel_data.dict().items() if v is not None}
    return await controller.update_panel(panel_id, update_dict)


@router.delete("/defense-panels/{panel_id}")
async def delete_panel(
    panel_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_coordinator)
):
    controller = DefensePanelController(db)
    return await controller.delete_panel(panel_id)


@router.get("/defense-panels/{panel_id}/students")
async def get_students_for_panel(
    panel_id: str,
    academic_year_id: Optional[str] = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_coordinator)
):
    controller = DefenseScheduleController(db)
    return await controller.get_students_for_panel(panel_id, academic_year_id)


@router.post("/defense-schedules", response_model=DefenseSchedulePublic)
async def create_defense_schedule(
    schedule_data: DefenseScheduleCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_coordinator)
):
    controller = DefenseScheduleController(db)
    schedule_dict = schedule_data.dict()
    academic_year_id = schedule_dict.pop("academic_year_id", None)
    return await controller.create_schedule(schedule_dict, current_user.email, academic_year_id)


@router.get("/defense-schedules", response_model=Page)
async def get_all_schedules(
    limit: int = Query(50, ge=1, le=100),
    cursor: Optional[str] = None,
    academic_year_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    panel_id: Optional[str] = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_coordinator)
):
    controller = DefenseScheduleController(db)
    return await controller.get_all_schedules(limit=limit, cursor=cursor, academic_year_id=academic_year_id, status=status, panel_id=panel_id)


@router.get("/defense-schedules/{schedule_id}", response_model=DefenseSchedulePublic)
async def get_schedule(
    schedule_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_coordinator)
):
    controller = DefenseScheduleController(db)
    return await controller.get_schedule_by_id(schedule_id)


@router.get("/defense-schedules/date/{target_date}")
async def get_schedules_by_date(
    target_date: date,
    academic_year_id: Optional[str] = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_coordinator)
):
    controller = DefenseScheduleController(db)
    return await controller.get_schedules_by_date(target_date, academic_year_id)


@router.get("/defense-schedules/calendar/markers")
async def get_calendar_markers(
    start_date: date = Query(...),
    end_date: date = Query(...),
    academic_year_id: Optional[str] = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_coordinator)
):
    controller = DefenseScheduleController(db)
    return await controller.get_calendar_markers(start_date, end_date, academic_year_id)


@router.patch("/defense-schedules/{schedule_id}", response_model=DefenseSchedulePublic)
async def update_schedule(
    schedule_id: str,
    schedule_data: DefenseScheduleUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_coordinator)
):
    controller = DefenseScheduleController(db)
    update_dict = {k: v for k, v in schedule_data.dict().items() if v is not None}
    return await controller.update_schedule(schedule_id, update_dict, current_user.email)


@router.post("/defense-schedules/{schedule_id}/cancel")
async def cancel_schedule(
    schedule_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_coordinator)
):
    controller = DefenseScheduleController(db)
    return await controller.cancel_schedule(schedule_id, current_user.email)

