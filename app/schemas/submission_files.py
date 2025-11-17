from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

from app.schemas.base import Obj, PyObjectId


class FileStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    PENDING_REVIEW = "pending_review"
    CHANGES_REQUESTED = "changes_requested"
    APPROVED = "approved"


class Page(BaseModel):
    items: list["SubmissionFilePublic"]
    next_cursor: str | None = None


class SubmissionFileCreate(BaseModel):
    submission_id: PyObjectId
    file_name: str
    file_path: str
    file_type: str | None = None
    file_size: int | None = None
    uploaded_by: PyObjectId  # Student who uploaded this file
    comments: str | None = None
    status: FileStatus = FileStatus.PENDING_REVIEW


class SubmissionFileUpdate(BaseModel):
    file_name: str | None = None
    file_path: str | None = None
    comments: str | None = None
    status: FileStatus | None = None


class SubmissionFilePublic(Obj):
    submission_id: PyObjectId
    file_name: str
    file_path: str
    file_type: str | None = None
    file_size: int | None = None
    uploaded_by: PyObjectId
    comments: str | None = None
    status: FileStatus = FileStatus.PENDING_REVIEW
    uploaded_at: datetime = Field(validation_alias="createdAt")
    updated_at: datetime = Field(validation_alias="updatedAt")