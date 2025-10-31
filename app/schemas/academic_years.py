from datetime import datetime
from pydantic import BaseModel, Field

from app.schemas.base import Obj, PyObjectId


class Page(BaseModel):
    items: list["AcademicYearPublic"]
    next_cursor: str | None = None


class AcademicYearCreate(BaseModel):
    year: str
    createdBy: PyObjectId
    terms: int = 2
    status: str = "INACTIVE"
    currentTerm: int = 1
    deleted: bool = False


class AcademicYearUpdate(BaseModel):
    year: str | None = None
    terms: int | None = None
    status: str | None = None
    currentTerm: int | None = None
    deleted: bool | None = None


class AcademicYearPublic(Obj):
    year: str
    createdBy: PyObjectId
    createdAt: datetime = Field(validation_alias="createdAt")
    updatedAt: datetime = Field(validation_alias="updatedAt")
    deleted: bool = False
    terms: int = 2
    status: str = "INACTIVE"
    currentTerm: int = 1