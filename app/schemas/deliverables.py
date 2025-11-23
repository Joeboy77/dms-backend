from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from app.schemas.base import Obj, PyObjectId
from app.schemas.submissions import SubmissionPublic


class Page(BaseModel):
    items: List["DeliverablePublic"]
    next_cursor: Optional[str] = None

class DeliverableCreate(BaseModel):
    title: str
    start_date: datetime
    end_date: datetime
    project_id: PyObjectId
    instructions: Optional[str] = None
    file_path: Optional[str] = None

class DeliverableUpdate(BaseModel):
    title: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    supervisor_id: Optional[PyObjectId] = None
    project_id: Optional[PyObjectId] = None
    instructions: Optional[str] = None
    file_path: Optional[str] = None


class DeliverablePublic(Obj):
    title: str
    start_date: datetime
    end_date: datetime
    supervisor_id: PyObjectId
    project_id: PyObjectId
    instructions: Optional[str] = None
    file_path: Optional[str] = None
    status: Optional[str] = None
    group_ids: Optional[List[PyObjectId]] = None
    submissions: Optional[List[SubmissionPublic]] = None
    total_submissions: int = 0
    created_at: Optional[datetime] = Field(default=None, validation_alias="createdAt")
    updated_at: Optional[datetime] = Field(default=None, validation_alias="updatedAt")
