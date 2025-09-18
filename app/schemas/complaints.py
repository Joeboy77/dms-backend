from datetime import datetime
from pydantic import BaseModel, Field

from app.schemas.base import Obj, PyObjectId


class Page(BaseModel):
    items: list["ComplaintPublic"]
    next_cursor: str | None = None


class ComplaintCreate(BaseModel):
    subject: str
    complaint: str
    reference: str | None = None
    category: PyObjectId
    attachment: str | None = None
    status: str = "PENDING"
    createdBy: dict | None = None
    assignedTo: list[PyObjectId] = []
    actions: list[dict] = []
    deleted: bool = False
    feedbacks: list[dict] = []
    admin: PyObjectId | None = None


class ComplaintUpdate(BaseModel):
    subject: str | None = None
    complaint: str | None = None
    reference: str | None = None
    category: PyObjectId | None = None
    attachment: str | None = None
    status: str | None = None
    createdBy: dict | None = None
    assignedTo: list[PyObjectId] | None = None
    actions: list[dict] | None = None
    deleted: bool | None = None
    feedbacks: list[dict] | None = None
    admin: PyObjectId | None = None


class ComplaintPublic(Obj):
    subject: str
    complaint: str
    reference: str | None = None
    category: PyObjectId
    attachment: str | None = None
    status: str = "PENDING"
    createdBy: dict | None = None
    assignedTo: list[PyObjectId] = []
    actions: list[dict] = []
    deleted: bool = False
    feedbacks: list[dict] = []
    admin: PyObjectId | None = None
    createdAt: datetime = Field(validation_alias="createdAt")
    updatedAt: datetime = Field(validation_alias="updatedAt")


class ComplaintAction(BaseModel):
    action_type: str
    description: str
    performed_by: PyObjectId
    performed_at: datetime
    notes: str | None = None


class ComplaintFeedback(BaseModel):
    feedback_type: str
    message: str
    provided_by: PyObjectId
    provided_at: datetime
    rating: int | None = None