from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from bson import ObjectId

from app.schemas.base import Obj, PyObjectId


class Page(BaseModel):
    items: list["StudentPublic"]
    next_cursor: str | None = None


class StudentAssignmentRequest(BaseModel):
    student_ids: list[str]  # Accept academic IDs as strings
    academic_year_id: PyObjectId
    supervisor_id: PyObjectId


class StudentCreate(BaseModel):
    title: str | None = None
    surname: str
    otherNames: str | None = None
    email: str
    phone: str | None = None
    program: PyObjectId | None = None
    level: PyObjectId | None = None
    academicId: str
    pin: str
    academicYears: list[PyObjectId] | None = None
    deleted: bool = False
    type: str = "UNDERGRADUATE" # DEFERRED
    admissionYear: PyObjectId | None = None
    currentAcademicYear: PyObjectId | None = None
    classGroup: PyObjectId | None = None
    image: str | None = None
    
    model_config = ConfigDict(populate_by_name=True)


class StudentUpdate(BaseModel):
    title: str | None = None
    surname: str | None = None
    otherNames: str | None = None
    email: str | None = None
    phone: str | None = None
    program: PyObjectId | None = None
    level: PyObjectId | None = None
    academicId: str | None = None
    academicYears: list[PyObjectId] | None = None
    deleted: bool | None = None
    type: str | None = None
    admissionYear: PyObjectId | None = None
    currentAcademicYear: PyObjectId | None = None
    classGroup: PyObjectId | None = None
    image: str | None = None
    
    model_config = ConfigDict(populate_by_name=True)


class StudentPublic(Obj):
    title: str | None = None
    surname: str
    otherNames: str | None = None
    email: str
    phone: str | None = None
    program: PyObjectId | None = None
    level: PyObjectId | None = None
    createdAt: datetime = Field(validation_alias="createdAt")
    updatedAt: datetime | None = Field(default=None, validation_alias="updatedAt")
    academicId: str | None = Field(default=None, validation_alias="studentID")
    pin: str | None = Field(default=None, validation_alias="pin")
    academicYears: list[PyObjectId] | None = None
    deleted: bool = False
    type: str = "UNDERGRADUATE"
    admissionYear: PyObjectId | None = None
    currentAcademicYear: PyObjectId | None = None
    classGroup: PyObjectId | None = None
    image: str | None = None
    
    model_config = ConfigDict(populate_by_name=True)
    
    
class StudentLogin(BaseModel):
    academicId: str | None = Field(default=None, validation_alias="studentID")
    pin: str | None = None