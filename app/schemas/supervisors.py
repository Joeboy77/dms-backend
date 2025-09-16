from datetime import datetime
from pydantic import BaseModel, Field

from app.schemas.base import Obj, PyObjectId
from app.schemas.lecturers import LecturerPublic


class Page(BaseModel):
    items: list["SupervisorPublic"]
    next_cursor: str | None = None


class SupervisorCreate(BaseModel):
    lecturer_id: PyObjectId
    max_students: int | None = None


class SupervisorUpdate(BaseModel):
    lecturer_id: PyObjectId | None = None
    max_students: int | None = None


class SupervisorPublic(Obj):
    lecturer_id: PyObjectId
    max_students: int | None = None
    project_student_count: int = 0
    created_at: datetime = Field(validation_alias="createdAt")
    updated_at: datetime = Field(validation_alias="updatedAt")


class SupervisorWithLecturer(BaseModel):
    supervisor: SupervisorPublic
    lecturer: LecturerPublic


class SupervisorWithLecturerDetails(Obj):
    lecturer_id: PyObjectId
    max_students: int | None = None
    project_student_count: int = 0
    created_at: datetime = Field(validation_alias="createdAt")
    updated_at: datetime = Field(validation_alias="updatedAt")
    lecturer_name: str
    lecturer_email: str
    lecturer_phone: str | None = None
    lecturer_department: str | None = None
    lecturer_title: str | None = None
    lecturer_specialization: str | None = None