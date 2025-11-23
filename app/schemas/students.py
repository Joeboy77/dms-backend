from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from bson import ObjectId

from app.schemas.base import Obj, PyObjectId


class Page(BaseModel):
    items: List["StudentPublic"]
    next_cursor: Optional[str] = None


class StudentAssignmentRequest(BaseModel):
    student_ids: List[str]
    academic_year_id: PyObjectId
    supervisor_id: PyObjectId


class StudentCreate(BaseModel):
    title: Optional[str] = None
    surname: str
    otherNames: Optional[str] = None
    email: str
    phone: Optional[str] = None
    program: Optional[PyObjectId] = None
    level: Optional[PyObjectId] = None
    academicId: str
    pin: str
    academicYears: Optional[List[PyObjectId]] = None
    deleted: bool = False
    type: str = "UNDERGRADUATE"
    admissionYear: Optional[PyObjectId] = None
    currentAcademicYear: Optional[PyObjectId] = None
    classGroup: Optional[PyObjectId] = None
    image: Optional[str] = None
    
    model_config = ConfigDict(populate_by_name=True)


class StudentUpdate(BaseModel):
    title: Optional[str] = None
    surname: Optional[str] = None
    otherNames: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    program: Optional[PyObjectId] = None
    level: Optional[PyObjectId] = None
    academicId: Optional[str] = None
    academicYears: Optional[List[PyObjectId]] = None
    deleted: Optional[bool] = None
    type: Optional[str] = None
    admissionYear: Optional[PyObjectId] = None
    currentAcademicYear: Optional[PyObjectId] = None
    classGroup: Optional[PyObjectId] = None
    image: Optional[str] = None
    
    model_config = ConfigDict(populate_by_name=True)


class StudentPublic(Obj):
    title: Optional[str] = None
    surname: str
    otherNames: Optional[str] = None
    email: str
    phone: Optional[str] = None
    program: Optional[PyObjectId] = None
    level: Optional[PyObjectId] = None
    createdAt: datetime = Field(validation_alias="createdAt")
    updatedAt: Optional[datetime] = Field(default=None, validation_alias="updatedAt")
    academicId: Optional[str] = Field(default=None, validation_alias="studentID")
    pin: Optional[str] = Field(default=None, validation_alias="pin")
    academicYears: Optional[List[PyObjectId]] = None
    deleted: bool = False
    type: str = "UNDERGRADUATE"
    admissionYear: Optional[PyObjectId] = None
    currentAcademicYear: Optional[PyObjectId] = None
    classGroup: Optional[PyObjectId] = None
    image: Optional[str] = None
    
    model_config = ConfigDict(populate_by_name=True)
    
    
class StudentLogin(BaseModel):
    academicId: Optional[str] = Field(default=None, validation_alias="academicID")
    pin: Optional[str] = None