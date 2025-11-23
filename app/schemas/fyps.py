from datetime import datetime
from typing import Optional, List, Dict, Union
from pydantic import BaseModel, Field

from app.schemas.base import Obj, PyObjectId
from app.schemas.project_areas import ProjectAreaPublic


class Page(BaseModel):
    items: List["FypPublic"]
    next_cursor: Optional[str] = None


class FypCreate(BaseModel):
    group: PyObjectId
    projectArea: PyObjectId
    title: str
    checkin: PyObjectId


class FypUpdate(BaseModel):
    group: Optional[PyObjectId] = None
    projectArea: Optional[PyObjectId] = None
    title: Optional[str] = None
    checkin: Optional[PyObjectId] = None


class FypPublic(Obj):
    group: Union[PyObjectId, str]
    projectArea: Union[PyObjectId, str]
    title: str
    progress_percentage: float = 0.0
    checkin: Union[PyObjectId, str]
    supervisor: Optional[Union[PyObjectId, str]] = None
    createdAt: datetime = Field(validation_alias="createdAt")
    updatedAt: datetime = Field(validation_alias="updatedAt")

    
class FypPublicWithProjectArea(Obj):
    group: PyObjectId
    projectArea: ProjectAreaPublic
    checkin: PyObjectId
    supervisor: Optional[PyObjectId] = None
    createdAt: datetime = Field(validation_alias="createdAt")
    updatedAt: datetime = Field(validation_alias="updatedAt")


class FypWithDetails(BaseModel):
    fyp: FypPublic
    group_details: Dict
    project_area_details: List[ProjectAreaPublic]
    checkin_details: Dict
    supervisor_details: Dict


class ProjectStage(BaseModel):
    name: str
    status: str
    completed: bool


class DeliverableProgress(BaseModel):
    name: str
    deadline: datetime
    status: str


class SupervisorInfo(BaseModel):
    name: str
    academicId: Optional[str] = None
    areaOfInterest: Optional[str] = None
    email: Optional[str] = None
    title: Optional[str] = None
    department: Optional[str] = None


class ProjectAreaInfo(BaseModel):
    title: str
    description: Optional[str] = None
    topic: Optional[str] = None


class ReminderInfo(BaseModel):
    title: str
    date: datetime
    formatted: Optional[str] = None


class ProjectOverview(BaseModel):
    stages: List[ProjectStage]
    completionPercentage: float
    nextDeadline: Optional[datetime] = None


class CalendarInfo(BaseModel):
    highlightedDates: List[str]
    month: Optional[int] = None
    year: Optional[int] = None


class FypDashboard(BaseModel):
    supervisor: SupervisorInfo
    projectArea: ProjectAreaInfo
    projectOverview: ProjectOverview
    projectProgress: List[DeliverableProgress]
    calendar: CalendarInfo
    reminders: List[ReminderInfo]