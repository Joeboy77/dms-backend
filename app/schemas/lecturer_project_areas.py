from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field

from app.schemas.base import Obj, PyObjectId


class Page(BaseModel):
    items: List["LecturerProjectAreaPublic"]
    next_cursor: Optional[str] = None


class LecturerProjectAreaCreate(BaseModel):
    lecturer: PyObjectId
    projectAreas: List[PyObjectId]
    academicYear: PyObjectId


class LecturerProjectAreaUpdate(BaseModel):
    lecturer: Optional[PyObjectId] = None
    projectAreas: Optional[List[PyObjectId]] = None
    academicYear: Optional[PyObjectId] = None


class LecturerProjectAreaPublic(Obj):
    lecturer: PyObjectId
    projectAreas: List[PyObjectId]
    academicYear: PyObjectId
    createdAt: datetime = Field(validation_alias="createdAt")
    updatedAt: datetime = Field(validation_alias="updatedAt")


class StudentInfoResponse(BaseModel):
    student: Dict
    supervisor: Optional[Dict] = None
    project_area: Optional[Dict] = None
    fyp_details: Optional[Dict] = None