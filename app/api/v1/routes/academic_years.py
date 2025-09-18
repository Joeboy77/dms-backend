from fastapi import APIRouter, Depends, Query, responses
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.schemas.academic_years import AcademicYearCreate, AcademicYearPublic, AcademicYearUpdate, Page
from app.controllers.academic_years import AcademicYearController

router = APIRouter(tags=["Academic Years"])


@router.get("/academic-years", response_model=Page)
async def get_all_academic_years(
    limit: int = Query(10, alias="limit", ge=1, le=100),
    cursor: str | None = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = AcademicYearController(db)
    return await controller.get_all_academic_years(limit=limit, cursor=cursor)


@router.get("/academic-years/active", response_model=list[AcademicYearPublic])
async def get_active_academic_years(
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = AcademicYearController(db)
    return await controller.get_active_academic_years()


@router.get("/academic-years/{id}", response_model=AcademicYearPublic)
async def get_academic_year(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = AcademicYearController(db)
    return await controller.get_academic_year_by_id(id)


@router.post("/academic-years", response_model=AcademicYearPublic)
async def create_academic_year(
    academic_year: AcademicYearCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = AcademicYearController(db)
    academic_year_data = academic_year.model_dump()
    return await controller.create_academic_year(academic_year_data)


@router.patch("/academic-years/{id}", response_model=AcademicYearPublic)
async def update_academic_year(
    id: str,
    academic_year: AcademicYearUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = AcademicYearController(db)
    update_data = academic_year.model_dump()
    return await controller.update_academic_year(id, update_data)


@router.delete("/academic-years/{id}", status_code=204)
async def delete_academic_year(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = AcademicYearController(db)
    await controller.delete_academic_year(id)
    return responses.Response(status_code=204)