from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from app.schemas.base import Obj


class Page(BaseModel):
    items: List["ReminderPublic"]
    next_cursor: Optional[str] = None


class ReminderCreate(BaseModel):
    title: str
    date_time: datetime


class ReminderUpdate(BaseModel):
    title: Optional[str] = None
    date_time: Optional[datetime] = None


class ReminderPublic(Obj):
    title: str
    date_time: datetime
    created_at: Optional[datetime] = Field(default=None, validation_alias="createdAt")
    updated_at: Optional[datetime] = Field(default=None, validation_alias="updatedAt")