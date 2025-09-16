from datetime import datetime
from pydantic import BaseModel, Field

from app.schemas.base import Obj, PyObjectId


class Page(BaseModel):
    items: list["DeliverablePublic"]
    next_cursor: str | None = None


class DeliverableCreate(BaseModel):
    title: str
    start_date: datetime
    end_date: datetime
    supervisor_id: PyObjectId
    instructions: str | None = None
    file_path: str | None = None


class DeliverableUpdate(BaseModel):
    title: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    supervisor_id: PyObjectId | None = None
    instructions: str | None = None
    file_path: str | None = None


class DeliverablePublic(Obj):
    title: str
    start_date: datetime
    end_date: datetime
    supervisor_id: PyObjectId
    instructions: str | None = None
    file_path: str | None = None
    total_submissions: int = 0
    created_at: datetime | None = Field(default=None, validation_alias="createdAt")
    updated_at: datetime | None = Field(default=None, validation_alias="updatedAt")