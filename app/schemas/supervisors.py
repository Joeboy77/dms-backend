from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from app.schemas.base import Obj, PyObjectId
from app.schemas.lecturers import LecturerPublic


class Page(BaseModel):
    items: List["SupervisorPublic"]
    next_cursor: Optional[str] = None


class SupervisorCreate(BaseModel):
    lecturer_id: PyObjectId
    max_students: Optional[int] = None


class SupervisorUpdate(BaseModel):
    lecturer_id: Optional[PyObjectId] = None
    max_students: Optional[int] = None


class SupervisorPublic(Obj):
    lecturer_id: PyObjectId
    max_students: Optional[int] = None
    project_student_count: int
    createdAt: datetime = Field(validation_alias="createdAt", alias="createdAt")
    updatedAt: datetime = Field(validation_alias="updatedAt", alias="updatedAt")


class SupervisorWithLecturer(BaseModel):
    supervisor: SupervisorPublic
    lecturer: LecturerPublic


class SupervisorWithLecturerDetails(Obj):
    lecturer_id: PyObjectId
    max_students: Optional[int] = None
    project_student_count: int
    created_at: datetime = Field(validation_alias="createdAt")
    updated_at: datetime = Field(validation_alias="updatedAt")
    lecturer_name: str
    lecturer_email: str
    lecturer_phone: Optional[str] = None
    lecturer_department: Optional[str] = None
    lecturer_title: Optional[str] = None
    lecturer_specialization: Optional[str] = None


class StudentInfo(BaseModel):
    student_id: str
    academic_id: str
    student_name: str
    email: str
    phone: Optional[str] = None
    program: Optional[str] = None
    level: Optional[str] = None


class SupervisorInfo(BaseModel):
    supervisor_id: str
    academic_id: str
    name: str
    email: str
    phone: Optional[str] = None
    title: Optional[str] = None
    position: Optional[str] = None
    department: Optional[str] = None
    bio: Optional[str] = None
    office_hours: Optional[str] = None
    office_location: Optional[str] = None
    max_students: Optional[int] = None
    total_students_supervised: int
    specialization: Optional[str] = None


class AssignmentInfo(BaseModel):
    fyp_id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    checkin_id: Optional[str] = None
    project_area_id: Optional[str] = None


class ProjectAreaInfo(BaseModel):
    project_area_id: str
    title: str
    description: Optional[str] = None
    image: Optional[str] = None


class StudentSupervisorResponse(BaseModel):
    student: StudentInfo
    supervisor: SupervisorInfo
    assignment: AssignmentInfo
    project_area: Optional[ProjectAreaInfo] = None