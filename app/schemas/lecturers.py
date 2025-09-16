from datetime import datetime
from pydantic import BaseModel, Field

from app.schemas.base import Obj


class Page(BaseModel):
    items: list["LecturerPublic"]
    next_cursor: str | None = None


class LecturerCreate(BaseModel):
    name: str
    email: str
    phone: str | None = None
    department: str | None = None
    title: str | None = None
    specialization: str | None = None


class LecturerUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    department: str | None = None
    title: str | None = None
    specialization: str | None = None


class LecturerPublic(Obj):
    name: str
    email: str
    phone: str | None = None
    department: str | None = None
    title: str | None = None
    specialization: str | None = None
    created_at: datetime = Field(validation_alias="createdAt")
    updated_at: datetime = Field(validation_alias="updatedAt")