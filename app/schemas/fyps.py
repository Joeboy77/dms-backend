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
    student: PyObjectId | str
    projectArea: PyObjectId | str
    checkin: PyObjectId | str
    supervisor: PyObjectId | str | None = None
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


# Dashboard Schemas
class ProjectStage(BaseModel):
    name: str
    status: str  # "completed", "in_progress", "not_started", "locked"
    completed: bool


class DeliverableProgress(BaseModel):
    name: str
    deadline: datetime
    status: str  # "Completed", "In Progress", "Not Started"


class SupervisorInfo(BaseModel):
    name: str
    academicId: str | None = None
    areaOfInterest: str | None = None
    email: str | None = None
    title: str | None = None
    department: str | None = None


class ProjectAreaInfo(BaseModel):
    title: str
    description: str | None = None
    topic: str | None = None  # This might be stored in FYP or separately


class ReminderInfo(BaseModel):
    title: str
    date: datetime
    formatted: str | None = None


class ProjectOverview(BaseModel):
    stages: List[ProjectStage]
    completionPercentage: float
    nextDeadline: datetime | None = None


class CalendarInfo(BaseModel):
    highlightedDates: List[str]  # List of date strings in YYYY-MM-DD format
    month: int | None = None
    year: int | None = None


class FypDashboard(BaseModel):
    supervisor: SupervisorInfo
    projectArea: ProjectAreaInfo
    projectOverview: ProjectOverview
    projectProgress: List[DeliverableProgress]
    calendar: CalendarInfo
    reminders: List[ReminderInfo]