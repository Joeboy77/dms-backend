from datetime import datetime
from typing import Optional

from bson import ObjectId
from pydantic import BaseModel, Field

from app.schemas.base import Obj, PyObjectId


class Page(BaseModel):
    items: list["ActivityPublic"]
    next_cursor: str | None = None


class Detail(BaseModel):
    status: int
    message: str
    requestType: str


class ActivityPublic(Obj):
    action: str
    details: Detail
    createdAt: datetime = Field(validation_alias="createdAt")
    updatedAt: datetime | None = Field(default=None, validation_alias="updatedAt")
