from datetime import datetime
from pydantic import BaseModel, Field

from app.schemas.base import Obj, PyObjectId


class Page(BaseModel):
    items: list["FypPublic"]
    next_cursor: str | None = None


class FypCreate(BaseModel):
    student: PyObjectId
    projectArea: PyObjectId
    checkin: PyObjectId
    supervisor: PyObjectId | None = None


class FypUpdate(BaseModel):
    student: PyObjectId | None = None
    projectArea: PyObjectId | None = None
    checkin: PyObjectId | None = None
    supervisor: PyObjectId | None = None


class FypPublic(Obj):
    student: PyObjectId
    projectArea: PyObjectId
    checkin: PyObjectId
    supervisor: PyObjectId | None = None
    createdAt: datetime = Field(validation_alias="createdAt")
    updatedAt: datetime = Field(validation_alias="updatedAt")