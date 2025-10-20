from datetime import datetime
from pydantic import BaseModel, Field
from typing import List

from app.schemas.base import Obj, PyObjectId
from app.schemas.project_areas import ProjectAreaPublic


class Page(BaseModel):
    items: list["FypPublic"]
    next_cursor: str | None = None


class FypCreate(BaseModel):
    student: PyObjectId
    projectArea: PyObjectId
    checkin: PyObjectId
    supervisor: PyObjectId | None = None


class FypUpdate(BaseModel):
    student: PyObjectId | None = None
    projectArea: PyObjectId | None = None
    checkin: PyObjectId | None = None
    supervisor: PyObjectId | None = None


class FypPublic(Obj):
    student: PyObjectId
    projectArea: PyObjectId
    checkin: PyObjectId
    supervisor: PyObjectId | None = None
    createdAt: datetime = Field(validation_alias="createdAt")
    updatedAt: datetime = Field(validation_alias="updatedAt")
    
    
class FypPublicWithProjectArea(Obj):
    student: PyObjectId
    projectArea: ProjectAreaPublic
    checkin: PyObjectId
    supervisor: PyObjectId | None = None
    createdAt: datetime = Field(validation_alias="createdAt")
    updatedAt: datetime = Field(validation_alias="updatedAt")


class FypWithDetails(BaseModel):
    fyp: FypPublic
    student_details: dict
    project_area_details: List[ProjectAreaPublic]
    checkin_details: dict
    supervisor_details: dict
