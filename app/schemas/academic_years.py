from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from app.schemas.base import Obj, PyObjectId


class Page(BaseModel):
    items: List["AcademicYearPublic"]
    next_cursor: Optional[str] = None


class AcademicYearCreate(BaseModel):
    year: str
    createdBy: PyObjectId
    terms: int = 2
    status: str = "INACTIVE"
    currentTerm: int = 1
    deleted: bool = False


class AcademicYearUpdate(BaseModel):
    year: Optional[str] = None
    terms: Optional[int] = None
    status: Optional[str] = None
    currentTerm: Optional[int] = None
    deleted: Optional[bool] = None


class AcademicYearPublic(Obj):
    year: str
    createdBy: PyObjectId
    createdAt: datetime = Field(validation_alias="createdAt")
    updatedAt: datetime = Field(validation_alias="updatedAt")
    deleted: bool = False
    terms: int = 2
    status: str = "INACTIVE"
    currentTerm: int = 1