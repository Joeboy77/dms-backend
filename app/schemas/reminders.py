from datetime import datetime
from pydantic import BaseModel, Field

from app.schemas.base import Obj


class Page(BaseModel):
    items: list["ReminderPublic"]
    next_cursor: str | None = None


class ReminderCreate(BaseModel):
    title: str
    date_time: datetime


class ReminderUpdate(BaseModel):
    title: str | None = None
    date_time: datetime | None = None


class ReminderPublic(Obj):
    title: str
    date_time: datetime
    created_at: datetime | None = Field(default=None, validation_alias="createdAt")
    updated_at: datetime | None = Field(default=None, validation_alias="updatedAt")