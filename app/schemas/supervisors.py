from datetime import datetime
from pydantic import BaseModel, Field

from app.schemas.base import Obj, PyObjectId
from app.schemas.lecturers import LecturerPublic


class Page(BaseModel):
    items: list["SupervisorPublic"]
    next_cursor: str | None = None


class SupervisorCreate(BaseModel):
    lecturer_id: PyObjectId
    max_students: int | None = None


class SupervisorUpdate(BaseModel):
    lecturer_id: PyObjectId | None = None
    max_students: int | None = None


class SupervisorPublic(Obj):
    lecturer_id: PyObjectId
    max_students: int | None = None
    project_student_count: int
    createdAt: datetime = Field(validation_alias="createdAt", alias="createdAt")
    updatedAt: datetime = Field(validation_alias="updatedAt", alias="updatedAt")


class SupervisorWithLecturer(BaseModel):
    supervisor: SupervisorPublic
    lecturer: LecturerPublic


class SupervisorWithLecturerDetails(Obj):
    lecturer_id: PyObjectId
    max_students: int | None = None
    project_student_count: int
    created_at: datetime = Field(validation_alias="createdAt")
    updated_at: datetime = Field(validation_alias="updatedAt")
    lecturer_name: str
    lecturer_email: str
    lecturer_phone: str | None = None
    lecturer_department: str | None = None
    lecturer_title: str | None = None
    lecturer_specialization: str | None = None


class StudentInfo(BaseModel):
    student_id: str
    academic_id: str
    student_name: str
    email: str
    phone: str | None = None
    program: str | None = None
    level: str | None = None


class SupervisorInfo(BaseModel):
    supervisor_id: str
    academic_id: str
    name: str
    email: str
    phone: str | None = None
    title: str | None = None
    position: str | None = None
    department: str | None = None
    bio: str | None = None
    office_hours: str | None = None
    office_location: str | None = None
    max_students: int | None = None
    total_students_supervised: int
    specialization: str | None = None


class AssignmentInfo(BaseModel):
    fyp_id: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    checkin_id: str | None = None
    project_area_id: str | None = None


class ProjectAreaInfo(BaseModel):
    project_area_id: str
    title: str
    description: str | None = None
    image: str | None = None


class StudentSupervisorResponse(BaseModel):
    student: StudentInfo
    supervisor: SupervisorInfo
    assignment: AssignmentInfo
    project_area: ProjectAreaInfo | None = None