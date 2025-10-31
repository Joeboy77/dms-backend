from datetime import datetime
from pydantic import BaseModel, Field

from app.schemas.base import Obj, PyObjectId


class Page(BaseModel):
    items: list["GroupPublic"]
    next_cursor: str | None = None


class GroupCreate(BaseModel):
    name: str
    description: str | None = None
    student_ids: list[PyObjectId] = []


class GroupUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class GroupAddStudent(BaseModel):
    student_id: PyObjectId


class GroupRemoveStudent(BaseModel):
    student_id: PyObjectId


class GroupPublic(Obj):
    name: str
    description: str | None = None
    student_ids: list[PyObjectId] = []
    student_count: int = 0
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    
    class Config:
        populate_by_name = True
        from_attributes = True


class GroupWithStudents(BaseModel):
    group: GroupPublic
    students: list[dict] = []  # Will contain student details