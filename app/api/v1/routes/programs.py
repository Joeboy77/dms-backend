from fastapi import APIRouter, Depends, HTTPException, Query, responses
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional

from app.core.authentication.auth_middleware import get_current_token
from app.core.database import get_db
from app.schemas.programs import ProgramCreate, ProgramPublic, ProgramUpdate, Page, StudentDashboardResponse
from app.schemas.token import TokenData
from app.controllers.programs import ProgramController

router = APIRouter(tags=["Programs"])


@router.get("/programs", response_model=Page)
async def get_all_programs(
    limit: int = Query(10, alias="limit", ge=1, le=100),
    cursor: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = ProgramController(db)
    return await controller.get_all_programs(limit=limit, cursor=cursor)


@router.get("/programs/{id}", response_model=ProgramPublic)
async def get_program(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = ProgramController(db)
    return await controller.get_program_by_id(id)


@router.post("/programs", response_model=ProgramPublic)
async def create_program(
    program: ProgramCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = ProgramController(db)
    program_data = program.model_dump()
    return await controller.create_program(program_data)


@router.patch("/programs/{id}", response_model=ProgramPublic)
async def update_program(
    id: str,
    program: ProgramUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(get_current_token),
):
    controller = ProgramController(db)
    update_data = program.model_dump()
    return await controller.update_program(id, update_data)


@router.delete("/programs/{id}", status_code=204)
async def delete_program(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(get_current_token),
):
    controller = ProgramController(db)
    await controller.delete_program(id)
    return responses.Response(status_code=204)


@router.get("/programs/search/{title}", response_model=List[ProgramPublic])
async def search_programs_by_title(
    title: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(get_current_token),
):
    controller = ProgramController(db)
    return await controller.search_programs_by_title(title)


@router.get("/students-dashboard", response_model=List[StudentDashboardResponse])
async def get_all_student_dashboard(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(get_current_token),
):
    controller = ProgramController(db)
    return await controller.get_all_student_dashboard()


@router.get("/students/{student_id}/dashboard", response_model=StudentDashboardResponse)
async def get_student_dashboard(
    student_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(get_current_token),
):
    controller = ProgramController(db)
    return await controller.get_student_dashboard(student_id)


