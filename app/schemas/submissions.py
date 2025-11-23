from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from enum import Enum

from app.schemas.base import Obj, PyObjectId


class SubmissionStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PENDING_REVIEW = "pending_review"
    CHANGES_REQUESTED = "changes_requested"
    APPROVED = "approved"


class Page(BaseModel):
    items: List["SubmissionPublic"]
    next_cursor: Optional[str] = None


class SubmissionCreate(BaseModel):
    deliverable_id: PyObjectId
    project_id: PyObjectId
    group_id: PyObjectId
    attempt_number: int = 1
    lecturer_feedback: Optional[str] = None
    status: SubmissionStatus = SubmissionStatus.IN_PROGRESS


class SubmissionUpdate(BaseModel):
    lecturer_feedback: Optional[str] = None
    status: Optional[SubmissionStatus] = None


class SubmissionPublic(Obj):
    deliverable_id: PyObjectId
    project_id: PyObjectId
    group_id: PyObjectId
    lecturer_feedback: Optional[str] = None
    status: SubmissionStatus = SubmissionStatus.IN_PROGRESS
    attempt_number: int
    file_count: int = 0
    submitted_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True
        from_attributes = True


class GroupSubmissionInfo(BaseModel):
    group_id: PyObjectId
    group_name: str
    student_count: int
    students: List[Dict] = []
    submission: SubmissionPublic
    files: List[Dict] = []


class SubmissionWithFiles(BaseModel):
    submission: SubmissionPublic
    files: List[Dict] = []
    group_details: Optional[Dict] = None


class SubmissionDetailsResponse(BaseModel):
    submission: SubmissionPublic
    group: Dict
    students: List[Dict] = []
    files: List[Dict] = []
