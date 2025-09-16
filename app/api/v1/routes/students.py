from fastapi import APIRouter, Depends, HTTPException, Query, responses
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.authentication.auth_middleware import get_current_token
from app.core.database import get_db
from app.schemas.students import StudentCreate, StudentPublic, StudentUpdate, Page
from app.schemas.token import TokenData
from app.controllers.students import StudentController

router = APIRouter(tags=["Students"])


@router.get("/students", response_model=Page)
async def get_all_students(
    limit: int = Query(10, alias="limit", ge=1, le=100),
    cursor: str | None = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = StudentController(db)
    return await controller.get_all_students(limit=limit, cursor=cursor)


@router.get("/students/{id}", response_model=StudentPublic)
async def get_student(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(get_current_token),
):
    controller = StudentController(db)
    return await controller.get_student_by_id(id)


@router.post("/students", response_model=StudentPublic)
async def create_student(
    student: StudentCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(get_current_token),
):
    controller = StudentController(db)
    student_data = student.model_dump()
    return await controller.create_student(student_data)


@router.patch("/students/{id}", response_model=StudentPublic)
async def update_student(
    id: str,
    student: StudentUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(get_current_token),
):
    controller = StudentController(db)
    update_data = student.model_dump()
    return await controller.update_student(id, update_data)


@router.delete("/students/{id}", status_code=204)
async def delete_student(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(get_current_token),
):
    controller = StudentController(db)
    await controller.delete_student(id)
    return responses.Response(status_code=204)


@router.get("/students/major/{major}", response_model=list[StudentPublic])
async def get_students_by_major(
    major: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(get_current_token),
):
    controller = StudentController(db)
    return await controller.get_students_by_major(major)


@router.get("/students/year/{year}", response_model=list[StudentPublic])
async def get_students_by_year(
    year: int,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(get_current_token),
):
    controller = StudentController(db)
    return await controller.get_students_by_year(year)


@router.get("/students/project-area/{project_area_id}")
async def get_students_by_project_area(
    project_area_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = StudentController(db)
    return await controller.get_students_by_project_area(project_area_id)

@router.get("/students/supervisor/{supervisor_id}")
async def get_students_by_supervisor(
    supervisor_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = StudentController(db)
    return await controller.get_students_by_supervisor(supervisor_id)


@router.get("/students/count")
async def get_total_student_count(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(get_current_token),
):
    controller = StudentController(db)
    return await controller.get_total_student_count()
