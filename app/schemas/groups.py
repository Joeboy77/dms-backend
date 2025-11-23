from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field

from app.schemas.base import Obj, PyObjectId


class Page(BaseModel):
    items: List["GroupPublic"]
    next_cursor: Optional[str] = None


class GroupCreate(BaseModel):
    name: str
    project_title: Optional[str] = None
    students: List[PyObjectId] = []


class GroupUpdate(BaseModel):
    name: Optional[str] = None
    project_title: Optional[str] = None


class GroupAddStudent(BaseModel):
    student_id: PyObjectId


class GroupRemoveStudent(BaseModel):
    student_id: PyObjectId


class GroupPublic(Obj):
    name: str
    project_title: Optional[str] = None
    supervisor: Optional[str] = None
    students: List[PyObjectId] = []
    student_count: int
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    
    class Config:
        populate_by_name = True
        from_attributes = True


class GroupWithStudents(BaseModel):
    group: GroupPublic
    students: List[Dict] = []
    
    
class GroupAssignmentRequest(BaseModel):
    group_ids: List[str]
    academic_year_id: str
    supervisor_id: PyObjectId
    
class GroupAssignmentResponse(BaseModel):
    assigned_groups: List[str] = []
    assignment_errors: List[str] = []