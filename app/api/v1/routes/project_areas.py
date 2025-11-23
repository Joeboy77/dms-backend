from fastapi import APIRouter, Depends, HTTPException, Query, responses
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional

from app.core.authentication.auth_middleware import get_current_token
from app.core.database import get_db
from app.schemas.project_areas import ProjectAreaCreate, ProjectAreaPublic, ProjectAreaUpdate, Page, ProjectAreaWithLecturers, AllProjectAreasWithLecturers
from app.schemas.token import TokenData
from app.controllers.project_areas import ProjectAreaController

router = APIRouter(tags=["Project Areas"])


@router.get("/project-areas", response_model=Page)
async def get_all_project_areas(
    limit: int = Query(10, alias="limit", ge=1, le=100),
    cursor: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = ProjectAreaController(db)
    return await controller.get_all_project_areas(limit=limit, cursor=cursor)


@router.get("/project-areas/{id}", response_model=ProjectAreaPublic)
async def get_project_area(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = ProjectAreaController(db)
    return await controller.get_project_area_by_id(id)


@router.post("/project-areas", response_model=ProjectAreaPublic)
async def create_project_area(
    project_area: ProjectAreaCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = ProjectAreaController(db)
    project_area_data = project_area.model_dump()
    return await controller.create_project_area(project_area_data)


@router.patch("/project-areas/{id}", response_model=ProjectAreaPublic)
async def update_project_area(
    id: str,
    project_area: ProjectAreaUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = ProjectAreaController(db)
    update_data = project_area.model_dump()
    return await controller.update_project_area(id, update_data)


@router.delete("/project-areas/{id}", status_code=204)
async def delete_project_area(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = ProjectAreaController(db)
    await controller.delete_project_area(id)
    return responses.Response(status_code=204)


@router.get("/project-areas/search/{title}", response_model=List[ProjectAreaPublic])
async def search_project_areas_by_title(
    title: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = ProjectAreaController(db)
    return await controller.search_project_areas_by_title(title)


@router.get("/project-areas-lecturers", response_model=AllProjectAreasWithLecturers)
async def get_project_area_with_lecturers(
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = ProjectAreaController(db)
    return await controller.get_all_project_area_with_interested_lecturers()


@router.get("/project-areas/{id}/with-lecturers", response_model=ProjectAreaWithLecturers)
async def get_project_area_with_lecturers(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = ProjectAreaController(db)
    return await controller.get_project_area_with_interested_lecturers(id)


@router.post("/project-areas/{id}/lecturers/{lecturer_id}", response_model=ProjectAreaPublic)
async def add_interested_lecturer(
    id: str,
    lecturer_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = ProjectAreaController(db)
    return await controller.add_interested_lecturer(id, lecturer_id)


@router.delete("/project-areas/{id}/lecturers/{lecturer_id}", response_model=ProjectAreaPublic)
async def remove_interested_lecturer(
    id: str,
    lecturer_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = ProjectAreaController(db)
    return await controller.remove_interested_lecturer(id, lecturer_id)
