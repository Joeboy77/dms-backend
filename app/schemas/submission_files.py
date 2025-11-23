from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum

from app.schemas.base import Obj, PyObjectId


class FileStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    PENDING_REVIEW = "pending_review"
    CHANGES_REQUESTED = "changes_requested"
    APPROVED = "approved"


class Page(BaseModel):
    items: List["SubmissionFilePublic"]
    next_cursor: Optional[str] = None


class SubmissionFileCreate(BaseModel):
    submission_id: PyObjectId
    file_name: str
    file_path: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    uploaded_by: PyObjectId
    comments: Optional[str] = None
    status: FileStatus = FileStatus.PENDING_REVIEW


class SubmissionFileUpdate(BaseModel):
    file_name: Optional[str] = None
    file_path: Optional[str] = None
    comments: Optional[str] = None
    status: Optional[FileStatus] = None


class SubmissionFilePublic(Obj):
    submission_id: PyObjectId
    file_name: str
    file_path: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    uploaded_by: PyObjectId
    comments: Optional[str] = None
    status: FileStatus = FileStatus.PENDING_REVIEW
    uploaded_at: datetime = Field(validation_alias="createdAt")
    updated_at: datetime = Field(validation_alias="updatedAt")