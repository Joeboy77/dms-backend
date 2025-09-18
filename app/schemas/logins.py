from datetime import datetime
from pydantic import BaseModel, Field

from app.schemas.base import Obj, PyObjectId


class Page(BaseModel):
    items: list["LoginPublic"]
    next_cursor: str | None = None


class LoginCreate(BaseModel):
    academicId: str
    pin: str
    roles: list[PyObjectId] = []


class LoginUpdate(BaseModel):
    academicId: str | None = None
    pin: str | None = None
    roles: list[PyObjectId] | None = None
    lastLogin: datetime | None = None
    token: str | None = None


class LoginPublic(Obj):
    academicId: str
    pin: str
    roles: list[PyObjectId] = []
    createdAt: datetime = Field(validation_alias="createdAt")
    updatedAt: datetime = Field(validation_alias="updatedAt")
    lastLogin: datetime | None = Field(default=None, validation_alias="lastLogin")
    token: str | None = Field(default=None, validation_alias="token")


class LoginWithRoles(BaseModel):
    login: LoginPublic
    role_details: list[dict] = []