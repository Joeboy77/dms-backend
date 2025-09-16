from datetime import datetime
from pydantic import BaseModel, Field

from app.schemas.base import Obj, PyObjectId


class Page(BaseModel):
    items: list["RecentActivityPublic"]
    next_cursor: str | None = None


class RecentActivityCreate(BaseModel):
    timestamp: datetime
    user_id: PyObjectId
    user_name: str
    description: str


class RecentActivityUpdate(BaseModel):
    timestamp: datetime | None = None
    user_id: PyObjectId | None = None
    user_name: str | None = None
    description: str | None = None


class RecentActivityPublic(Obj):
    timestamp: datetime
    user_id: PyObjectId
    user_name: str
    description: str
    created_at: datetime | None = Field(default=None, validation_alias="createdAt")
    updated_at: datetime | None = Field(default=None, validation_alias="updatedAt")