from fastapi import APIRouter, Depends, Query, responses
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.schemas.logins import LoginCreate, LoginPublic, LoginUpdate, Page, LoginWithRoles
from app.controllers.logins import LoginController

router = APIRouter(tags=["Logins"])


@router.get("/logins", response_model=Page)
async def get_all_logins(
    limit: int = Query(10, alias="limit", ge=1, le=100),
    cursor: str | None = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = LoginController(db)
    return await controller.get_all_logins(limit=limit, cursor=cursor)


@router.get("/logins/{id}", response_model=LoginPublic)
async def get_login(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = LoginController(db)
    return await controller.get_login_by_id(id)


@router.get("/logins/academic-id/{academic_id}", response_model=LoginPublic)
async def get_login_by_academic_id(
    academic_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = LoginController(db)
    return await controller.get_login_by_academic_id(academic_id)


@router.get("/logins/academic-id/{academic_id}/with-roles", response_model=LoginWithRoles)
async def get_login_with_role_details(
    academic_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = LoginController(db)
    return await controller.get_login_with_role_details(academic_id)


@router.post("/logins", response_model=LoginPublic)
async def create_login(
    login: LoginCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = LoginController(db)
    login_data = login.model_dump()
    return await controller.create_login(login_data)


@router.patch("/logins/{id}", response_model=LoginPublic)
async def update_login(
    id: str,
    login: LoginUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = LoginController(db)
    update_data = login.model_dump()
    return await controller.update_login(id, update_data)


@router.delete("/logins/{id}", status_code=204)
async def delete_login(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = LoginController(db)
    await controller.delete_login(id)
    return responses.Response(status_code=204)


@router.get("/logins/role/{role_id}/users", response_model=list[LoginPublic])
async def get_users_with_role(
    role_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = LoginController(db)
    return await controller.get_users_with_role(role_id)


@router.get("/logins/check-role/{academic_id}/{role_id}")
async def check_user_has_role(
    academic_id: str,
    role_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = LoginController(db)
    has_role = await controller.check_user_has_role(academic_id, role_id)
    return {"has_role": has_role}