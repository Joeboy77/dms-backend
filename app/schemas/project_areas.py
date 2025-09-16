from datetime import datetime
from pydantic import BaseModel, Field

from app.schemas.base import Obj, PyObjectId


class Page(BaseModel):
    items: list["ProjectAreaPublic"]
    next_cursor: str | None = None


class ProjectAreaCreate(BaseModel):
    title: str
    description: str
    image: str | None = None
    interested_staff: list[PyObjectId] = []


class ProjectAreaUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    image: str | None = None
    interested_staff: list[PyObjectId] | None = None


class ProjectAreaPublic(Obj):
    title: str
    description: str
    image: str | None = None
    interested_staff: list[PyObjectId] = []
    interested_staff_count: int = 0
    createdAt: datetime = Field(validation_alias="createdAt")
    updatedAt: datetime = Field(validation_alias="updatedAt")


class ProjectAreaWithLecturers(BaseModel):
    project_area: ProjectAreaPublic
    lecturers: list[dict] = []


class AllProjectAreasWithLecturers(BaseModel):
    project_areas: list[ProjectAreaPublic]
    lecturers: list[dict] = []