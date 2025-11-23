from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from app.schemas.base import Obj, PyObjectId


class Page(BaseModel):
    items: List["LecturerPublic"]
    next_cursor: Optional[str] = None


class LecturerCreate(BaseModel):
    image: Optional[str] = None
    title: Optional[str] = None
    surname: str
    otherNames: Optional[str] = None
    academicId: str
    pin: str
    position: Optional[str] = None
    email: str
    phone: Optional[str] = None
    department: Optional[str] = None
    committees: List[str] = []
    bio: Optional[str] = None
    officeHours: Optional[str] = None
    officeLocation: Optional[str] = None
    deleted: bool = False
    projectAreas: List[PyObjectId] = []


class LecturerUpdate(BaseModel):
    image: Optional[str] = None
    title: Optional[str] = None
    surname: Optional[str] = None
    otherNames: Optional[str] = None
    academicId: Optional[str] = None
    position: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    pin: Optional[str] = None
    current_pin: Optional[str] = None
    bio: Optional[str] = None
    officeHours: Optional[str] = None
    officeLocation: Optional[str] = None
    department: Optional[str] = None
    committees: Optional[List[str]] = None
    officeLocation: Optional[str] = None
    deleted: Optional[bool] = None
    projectAreas: Optional[List[PyObjectId]] = None


class LecturerPublic(Obj):
    image: Optional[str] = None
    title: Optional[str] = None
    surname: str
    otherNames: Optional[str] = None
    academicId: str
    pin: str
    position: Optional[str] = None
    email: str
    phone: Optional[str] = None
    bio: Optional[str] = None
    officeHours: Optional[str] = None
    officeLocation: Optional[str] = None
    department: Optional[str] = None
    committees: List[str] = []
    deleted: bool = False
    projectAreas: List[PyObjectId] = []
    createdAt: datetime = Field(validation_alias="createdAt")
    updatedAt: datetime = Field(validation_alias="updatedAt")