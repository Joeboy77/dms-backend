from datetime import datetime
from pydantic import BaseModel, Field

from app.schemas.base import Obj, PyObjectId


class Page(BaseModel):
    items: list["FypCheckinPublic"]
    next_cursor: str | None = None


class FypCheckinCreate(BaseModel):
    academicYear: PyObjectId
    checkin: bool = True
    active: bool = True


class FypCheckinUpdate(BaseModel):
    academicYear: PyObjectId | None = None
    checkin: bool | None = None
    active: bool | None = None


class FypCheckinPublic(Obj):
    academicYear: PyObjectId
    checkin: bool
    active: bool
    createdAt: datetime = Field(validation_alias="createdAt")
    updatedAt: datetime = Field(validation_alias="updatedAt")