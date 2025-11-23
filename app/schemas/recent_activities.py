from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from app.schemas.base import Obj, PyObjectId


class Page(BaseModel):
    items: List["RecentActivityPublic"]
    next_cursor: Optional[str] = None


class RecentActivityCreate(BaseModel):
    timestamp: datetime
    user_id: PyObjectId
    user_name: str
    description: str


class RecentActivityUpdate(BaseModel):
    timestamp: Optional[datetime] = None
    user_id: Optional[PyObjectId] = None
    user_name: Optional[str] = None
    description: Optional[str] = None


class RecentActivityPublic(Obj):
    timestamp: datetime
    user_id: PyObjectId
    user_name: str
    description: str
    created_at: Optional[datetime] = Field(default=None, validation_alias="createdAt")
    updated_at: Optional[datetime] = Field(default=None, validation_alias="updatedAt")