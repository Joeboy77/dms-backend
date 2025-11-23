from fastapi import APIRouter, Depends, HTTPException, Query, responses
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional

from app.core.authentication.auth_middleware import get_current_token
from app.core.database import get_db
from app.schemas.projects import ProjectCreate, ProjectPublic, ProjectUpdate, Page, ProjectWithDetails, AllProjectsWithDetails
from app.schemas.token import TokenData
from app.controllers.projects import ProjectController

router = APIRouter(tags=["Projects"])


@router.get("/projects", response_model=Page)
async def get_all_projects(
    limit: int = Query(10, alias="limit", ge=1, le=100),
    cursor: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = ProjectController(db)
    return await controller.get_all_projects(limit=limit, cursor=cursor)


@router.get("/projects/{id}", response_model=ProjectPublic)
async def get_project(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = ProjectController(db)
    return await controller.get_project_by_id(id)


@router.post("/projects", response_model=ProjectPublic)
async def create_project(
    project: ProjectCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = ProjectController(db)
    project_data = project.model_dump()
    return await controller.create_project(project_data)


@router.patch("/projects/{id}", response_model=ProjectPublic)
async def update_project(
    id: str,
    project: ProjectUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = ProjectController(db)
    update_data = project.model_dump()
    return await controller.update_project(id, update_data)


@router.delete("/projects/{id}", status_code=204)
async def delete_project(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = ProjectController(db)
    await controller.delete_project(id)
    return responses.Response(status_code=204)


@router.get("/projects-with-details", response_model=AllProjectsWithDetails)
async def get_all_projects_with_details(
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = ProjectController(db)
    return await controller.get_all_projects_with_details()


@router.get("/projects-with-details/{id}", response_model=ProjectWithDetails)
async def get_project_with_details(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = ProjectController(db)
    return await controller.get_project_with_details(id)



@router.get("/groups/{group_id}/projects", response_model=List[ProjectPublic])
async def get_projects_by_group(
    group_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = ProjectController(db)
    return await controller.get_projects_by_group(group_id)