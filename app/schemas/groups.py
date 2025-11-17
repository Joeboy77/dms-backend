from datetime import datetime
from pydantic import BaseModel, Field

from app.schemas.base import Obj, PyObjectId


class Page(BaseModel):
    items: list["GroupPublic"]
    next_cursor: str | None = None


class GroupCreate(BaseModel):
    name: str
    project_title: str | None = None
    students: list[PyObjectId] = []


class GroupUpdate(BaseModel):
    name: str | None = None
    project_title: str | None = None


class GroupAddStudent(BaseModel):
    student_id: PyObjectId


class GroupRemoveStudent(BaseModel):
    student_id: PyObjectId


class GroupPublic(Obj):
    name: str
    project_title: str | None = None
    supervisor: str | None = None
    students: list[PyObjectId] = []
    student_count: int
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    
    class Config:
        populate_by_name = True
        from_attributes = True


class GroupWithStudents(BaseModel):
    group: GroupPublic
    students: list[dict] = []  # Will contain student details
    
    
class GroupAssignmentRequest(BaseModel):
    group_ids: list[str]  # Accept group IDs as strings
    academic_year_id: str
    supervisor_id: PyObjectId
    
class GroupAssignmentResponse(BaseModel):
    assigned_groups: list[str] = []
    assignment_errors: list[str] = []