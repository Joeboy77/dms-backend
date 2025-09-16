from datetime import datetime
from pydantic import BaseModel, Field

from app.schemas.base import Obj, PyObjectId


class Page(BaseModel):
    items: list["LecturerProjectAreaPublic"]
    next_cursor: str | None = None


class LecturerProjectAreaCreate(BaseModel):
    lecturer: PyObjectId
    projectAreas: list[PyObjectId]
    academicYear: PyObjectId


class LecturerProjectAreaUpdate(BaseModel):
    lecturer: PyObjectId | None = None
    projectAreas: list[PyObjectId] | None = None
    academicYear: PyObjectId | None = None


class LecturerProjectAreaPublic(Obj):
    lecturer: PyObjectId
    projectAreas: list[PyObjectId]
    academicYear: PyObjectId
    createdAt: datetime = Field(validation_alias="createdAt")
    updatedAt: datetime = Field(validation_alias="updatedAt")


class StudentInfoResponse(BaseModel):
    student: dict
    supervisor: dict | None = None
    project_area: dict | None = None
    fyp_details: dict | None = None