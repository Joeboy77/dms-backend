from datetime import datetime
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
    items: list["SubmissionPublic"]
    next_cursor: str | None = None


class SubmissionCreate(BaseModel):
    deliverable_id: PyObjectId
    group_id: PyObjectId
    comments: str | None = None
    status: SubmissionStatus = SubmissionStatus.IN_PROGRESS


class SubmissionUpdate(BaseModel):
    comments: str | None = None
    status: SubmissionStatus | None = None


class SubmissionPublic(Obj):
    deliverable_id: PyObjectId
    group_id: PyObjectId
    comments: str | None = None
    status: SubmissionStatus = SubmissionStatus.IN_PROGRESS
    file_count: int = 0
    submitted_at: datetime = Field(validation_alias="createdAt")
    updated_at: datetime | None = Field(default=None, validation_alias="updatedAt")


class GroupSubmissionInfo(BaseModel):
    group_id: PyObjectId
    group_name: str
    student_count: int
    students: list[dict] = []
    submission: SubmissionPublic
    files: list[dict] = []


class SubmissionWithFiles(BaseModel):
    submission: SubmissionPublic
    files: list[dict] = []
    group_details: dict | None = None


class SubmissionDetailsResponse(BaseModel):
    submission: SubmissionPublic
    group: dict
    students: list[dict] = []
    files: list[dict] = []