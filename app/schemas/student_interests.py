from datetime import datetime
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Union
from enum import Enum

from app.schemas.base import Obj, PyObjectId
from app.schemas.project_areas import ProjectAreaPublic


class InterestLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Page(BaseModel):
    items: List["StudentInterestPublic"]
    next_cursor: Optional[str] = None


class PreferenceOption(BaseModel):
    option: int
    supervisor_id: str
    project_area_id: str

class StudentPreferenceSchema(BaseModel):
    student_id: Union[PyObjectId, str]
    academic_year_id: Union[PyObjectId, str]
    preferences: List[PreferenceOption]
    project_topic: str


class StudentInterestCreate(BaseModel):
    student: PyObjectId
    academicYear: PyObjectId
    projectAreas: List[PyObjectId]
    preference_rank: Optional[int] = Field(default=0, ge=0, le=10)
    interest_level: InterestLevel = InterestLevel.MEDIUM
    # notes: Optional[str] = Field(default="", max_length=500)

    @validator('projectAreas')
    def validate_project_areas(cls, v):
        if not v:
            raise ValueError('At least one project area must be specified')
        if len(v) > 5:
            raise ValueError('Cannot specify more than 5 project areas')
        return v


class StudentInterestUpdate(BaseModel):
    projectAreas: Optional[List[PyObjectId]] = None
    preference_rank: Optional[int] = Field(default=None, ge=0, le=10)
    interest_level: Optional[InterestLevel] = None
    notes: Optional[str] = Field(default=None, max_length=500)

    @validator('projectAreas')
    def validate_project_areas(cls, v):
        if v is not None and len(v) > 5:
            raise ValueError('Cannot specify more than 5 project areas')
        return v


class StudentInterestPublic(Obj):
    student: PyObjectId
    academicYear: PyObjectId
    projectAreas: List[ProjectAreaPublic]
    supervisor: Optional[List[PyObjectId]] = None
    preference_rank: int = 0
    interest_level: InterestLevel = InterestLevel.MEDIUM
    notes: str = ""
    createdAt: datetime = Field(validation_alias="createdAt")
    updatedAt: datetime = Field(validation_alias="updatedAt")


class StudentInterestWithDetails(BaseModel):
    interest: StudentInterestPublic
    student_details: Dict
    project_area_details: List[Dict]
    academic_year_details: Dict

class StudentPreferenceUpdate(BaseModel):
    project_area_id: PyObjectId
    preference_rank: int = Field(ge=1, le=10)
    interest_level: InterestLevel = InterestLevel.MEDIUM
    notes: Optional[str] = Field(default="", max_length=500)


class SupervisorMatch(BaseModel):
    project_area: Dict
    supervisor: Dict
    student_preference: Optional[Dict] = None
    match_score: float


class StudentSupervisorMatches(BaseModel):
    student_id: str
    student_name: str
    matches: List[SupervisorMatch]
    total_matches: int


class InterestStatistics(BaseModel):
    total_interests: int
    unique_students: int
    project_area_popularity: Dict
    interest_level_distribution: Dict
    preference_rank_distribution: Dict
    project_area_titles: Dict


class BulkImportResult(BaseModel):
    imported_count: int
    error_count: int
    errors: List[Dict]


class StudentInterestAnalytics(BaseModel):
    most_popular_areas: List[Dict]
    least_popular_areas: List[Dict]
    average_interests_per_student: float
    students_without_interests: int
    interest_level_trends: Dict
    preference_rank_trends: Dict
