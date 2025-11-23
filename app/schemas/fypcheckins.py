from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from app.schemas.base import Obj, PyObjectId


class Page(BaseModel):
    items: List["FypCheckinPublic"]
    next_cursor: Optional[str] = None


class FypCheckinCreate(BaseModel):
    academicYear: PyObjectId
    checkin: bool = True
    active: bool = True


class FypCheckinUpdate(BaseModel):
    academicYear: Optional[PyObjectId] = None
    checkin: Optional[bool] = None
    active: Optional[bool] = None


class FypCheckinPublic(Obj):
    academicYear: PyObjectId
    checkin: bool
    active: bool
    createdAt: datetime = Field(validation_alias="createdAt")
    updatedAt: datetime = Field(validation_alias="updatedAt")