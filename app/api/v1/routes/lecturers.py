from fastapi import APIRouter, Depends, HTTPException, Query, responses
from typing import Optional, List, Dict
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.authentication.auth_middleware import get_current_token
from app.core.database import get_db
from app.schemas.lecturers import LecturerCreate, LecturerPublic, LecturerUpdate, Page
from app.schemas.token import TokenData
from app.controllers.lecturers import LecturerController

router = APIRouter(tags=["Lecturers"])


@router.get("/lecturers", response_model=Page)
async def get_all_lecturers(
    limit: int = Query(10, alias="limit", ge=1, le=100),
    cursor: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = LecturerController(db)
    return await controller.get_all_lecturers(limit=limit, cursor=cursor)


@router.get("/lecturers/{id}", response_model=LecturerPublic)
async def get_lecturer(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = LecturerController(db)
    return await controller.get_lecturer_by_id(id)


@router.get("/lecturers/by-academic-id/{academic_id}", response_model=LecturerPublic)
async def get_lecturer_by_academic_id(
    academic_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = LecturerController(db)
    return await controller.get_lecturer_by_academic_id(academic_id)


@router.post("/lecturers", response_model=LecturerPublic)
async def create_lecturer(
    lecturer: LecturerCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = LecturerController(db)
    lecturer_data = lecturer.model_dump()
    return await controller.create_lecturer(lecturer_data)


@router.patch("/lecturers/{id}", response_model=LecturerPublic)
async def update_lecturer(
    id: str,
    lecturer: LecturerUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = LecturerController(db)
    update_data = lecturer.model_dump()
    current_pin = update_data.pop("current_pin", None)  # Extract current_pin from update_data
    return await controller.update_lecturer(id, update_data, current_pin)


@router.delete("/lecturers/{id}", status_code=204)
async def delete_lecturer(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = LecturerController(db)
    await controller.delete_lecturer(id)
    return responses.Response(status_code=204)


@router.get("/lecturers/search/{name}", response_model=List[LecturerPublic])
async def search_lecturers_by_name(
    name: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = LecturerController(db)
    return await controller.search_lecturers_by_name(name)


@router.get("/lecturers/department/{department}", response_model=List[LecturerPublic])
async def get_lecturers_by_department(
    department: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = LecturerController(db)
    return await controller.get_lecturers_by_department(department)