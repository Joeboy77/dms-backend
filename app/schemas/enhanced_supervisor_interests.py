from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from app.schemas.base import Obj, PyObjectId


class SupervisorInfo(BaseModel):
    supervisor_id: PyObjectId
    lecturer_id: PyObjectId
    max_students: int
    current_students: int
    capacity_utilization: float
    available_slots: int


class LecturerInfo(BaseModel):
    lecturer_id: PyObjectId
    name: str
    email: str
    position: str | None = None
    bio: str | None = None
    office_hours: str | None = None
    office_location: str | None = None


class ProjectAreaInfo(BaseModel):
    project_area_id: PyObjectId
    title: str
    description: str | None = None
    image: str | None = None
    academic_year_id: PyObjectId
    interested_students_count: int
    created_at: datetime | None = Field(validation_alias="createdAt", default=None)
    updated_at: datetime | None = Field(validation_alias="updatedAt", default=None)


class SupervisorInterestProfile(BaseModel):
    supervisor: SupervisorInfo
    lecturer: LecturerInfo
    project_areas: List[ProjectAreaInfo]
    total_project_areas: int
    total_interested_students: int


class AddSupervisorInterestRequest(BaseModel):
    project_area_id: PyObjectId
    academic_year_id: PyObjectId


class RemoveSupervisorInterestRequest(BaseModel):
    project_area_id: PyObjectId
    academic_year_id: PyObjectId


class MatchingStudentProjectArea(BaseModel):
    id: PyObjectId
    title: str
    description: str | None = None


class MatchingStudentPreference(BaseModel):
    rank: int
    level: str
    notes: str | None = None


class MatchingStudent(BaseModel):
    student_id: PyObjectId
    student_name: str
    academic_id: str | None = None
    email: str | None = None
    program: str | None = None
    project_area: MatchingStudentProjectArea
    student_preference: MatchingStudentPreference
    match_score: float
    interest_created_at: datetime | None = Field(validation_alias="interest_created_at", default=None)


class SupervisorMatchingStudentsResponse(BaseModel):
    items: List[MatchingStudent]


class SupervisorInterestAnalytics(BaseModel):
    total_supervisors: int
    supervisors_with_interests: int
    average_interests_per_supervisor: float
    most_popular_areas_for_supervisors: List[dict]
    supervisor_capacity_utilization: dict
    matching_statistics: dict


class OptimalMatch(BaseModel):
    student_id: PyObjectId
    supervisor_id: PyObjectId
    project_area_id: PyObjectId
    match_score: float
    supervisor_capacity: int


class OptimalMatchesResponse(BaseModel):
    items: List[OptimalMatch]
