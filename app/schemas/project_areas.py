from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field

from app.schemas.base import Obj, PyObjectId


class Page(BaseModel):
    items: List["ProjectAreaPublic"]
    next_cursor: Optional[str] = None


class ProjectAreaCreate(BaseModel):
    title: str
    description: str
    image: Optional[str] = None
    interested_staff: List[PyObjectId] = []


class ProjectAreaUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    image: Optional[str] = None
    interested_staff: Optional[List[PyObjectId]] = None


class ProjectAreaPublic(Obj):
    title: str
    description: str
    image: Optional[str] = None
    interested_staff: List[PyObjectId] = []
    interested_staff_count: int = 0
    createdAt: datetime = Field(validation_alias="createdAt")
    updatedAt: datetime = Field(validation_alias="updatedAt")


class ProjectAreaWithLecturers(BaseModel):
    project_area: ProjectAreaPublic
    lecturers: List[Dict] = []


class AllProjectAreasWithLecturers(BaseModel):
    project_areas: List[ProjectAreaPublic]