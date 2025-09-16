from fastapi import APIRouter, Depends, HTTPException, Query, responses
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.authentication.auth_middleware import get_current_token
from app.core.database import get_db
from app.schemas.groups import GroupCreate, GroupPublic, GroupUpdate, Page, GroupAddStudent, GroupRemoveStudent, GroupWithStudents
from app.schemas.token import TokenData
from app.controllers.groups import GroupController

router = APIRouter(tags=["Groups"])


@router.get("/groups", response_model=Page)
async def get_all_groups(
    limit: int = Query(10, alias="limit", ge=1, le=100),
    cursor: str | None = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = GroupController(db)
    return await controller.get_all_groups(limit=limit, cursor=cursor)


@router.get("/groups/{id}", response_model=GroupPublic)
async def get_group(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = GroupController(db)
    return await controller.get_group_by_id(id)


@router.post("/groups", response_model=GroupPublic)
async def create_group(
    group: GroupCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = GroupController(db)
    group_data = group.model_dump()
    return await controller.create_group(group_data)


@router.patch("/groups/{id}", response_model=GroupPublic)
async def update_group(
    id: str,
    group: GroupUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = GroupController(db)
    update_data = group.model_dump()
    return await controller.update_group(id, update_data)


@router.delete("/groups/{id}", status_code=204)
async def delete_group(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = GroupController(db)
    await controller.delete_group(id)
    return responses.Response(status_code=204)


@router.post("/groups/{id}/students", response_model=GroupPublic)
async def add_student_to_group(
    id: str,
    student: GroupAddStudent,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = GroupController(db)
    return await controller.add_student_to_group(id, str(student.student_id))


@router.delete("/groups/{id}/students/{student_id}", response_model=GroupPublic)
async def remove_student_from_group(
    id: str,
    student_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = GroupController(db)
    return await controller.remove_student_from_group(id, student_id)


@router.get("/groups/{id}/with-students", response_model=GroupWithStudents)
async def get_group_with_students(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = GroupController(db)
    return await controller.get_group_with_students(id)


@router.get("/students/{student_id}/groups", response_model=list[GroupPublic])
async def get_groups_by_student(
    student_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = GroupController(db)
    return await controller.get_groups_by_student(student_id)