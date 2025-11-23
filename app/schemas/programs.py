from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from app.schemas.base import Obj, PyObjectId


class Page(BaseModel):
    items: List["ProgramPublic"]
    next_cursor: Optional[str] = None


class ProgramCreate(BaseModel):
    title: str
    tag: str
    description: str
    createdBy: PyObjectId
    code: str


class ProgramUpdate(BaseModel):
    title: Optional[str] = None
    tag: Optional[str] = None
    description: Optional[str] = None
    code: Optional[str] = None


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
    student_image: Optional[str] = None
    program: Optional[ProgramPublic] = None
    progress_status: str