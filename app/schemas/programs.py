from datetime import datetime
from pydantic import BaseModel, Field

from app.schemas.base import Obj, PyObjectId


class Page(BaseModel):
    items: list["ProgramPublic"]
    next_cursor: str | None = None


class ProgramCreate(BaseModel):
    title: str
    tag: str
    description: str
    createdBy: PyObjectId
    code: str


class ProgramUpdate(BaseModel):
    title: str | None = None
    tag: str | None = None
    description: str | None = None
    code: str | None = None


class ProgramPublic(Obj):
    title: str
    tag: str
    description: str
    createdBy: PyObjectId
    createdAt: datetime = Field(validation_alias="createdAt")
    updatedAt: datetime = Field(validation_alias="updatedAt")
    code: str


class StudentDashboardResponse(BaseModel):
    student_id: PyObjectId
    student_image: str | None = None
    program: ProgramPublic | None = None
    progress_status: str  # "not_started", "in_progress", "completed"