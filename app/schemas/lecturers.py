from datetime import datetime
from pydantic import BaseModel, Field

from app.schemas.base import Obj, PyObjectId


class Page(BaseModel):
    items: list["LecturerPublic"]
    next_cursor: str | None = None


class LecturerCreate(BaseModel):
    image: str | None = None
    title: str | None = None
    surname: str
    otherNames: str | None = None
    academicId: str
    pin: str
    position: str | None = None
    email: str
    phone: str | None = None
    department: str | None = None
    committees: list[str] = []
    bio: str | None = None
    officeHours: str | None = None
    officeLocation: str | None = None
    deleted: bool = False
    projectAreas: list[PyObjectId] = []


class LecturerUpdate(BaseModel):
    image: str | None = None
    title: str | None = None
    surname: str | None = None
    otherNames: str | None = None
    academicId: str | None = None
    position: str | None = None
    email: str | None = None
    phone: str | None = None
    bio: str | None = None
    officeHours: str | None = None
    officeLocation: str | None = None
    department: str | None = None
    committees: list[str] | None = None
    officeLocation: str | None = None
    deleted: bool | None = None
    projectAreas: list[PyObjectId] | None = None


class LecturerPublic(Obj):
    image: str | None = None
    title: str | None = None
    surname: str
    otherNames: str | None = None
    academicId: str
    pin: str
    position: str | None = None
    email: str
    phone: str | None = None
    bio: str | None = None
    officeHours: str | None = None
    officeLocation: str | None = None
    department: str | None = None
    committees: list[str] = []
    deleted: bool = False
    projectAreas: list[PyObjectId] = []
    createdAt: datetime = Field(validation_alias="createdAt")
    updatedAt: datetime = Field(validation_alias="updatedAt")