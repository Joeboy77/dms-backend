from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field

from app.schemas.base import Obj, PyObjectId


class Page(BaseModel):
    items: List["ComplaintPublic"]
    next_cursor: Optional[str] = None


class ComplaintCreate(BaseModel):
    subject: str
    complaint: str
    reference: Optional[str] = None
    category: PyObjectId
    attachment: Optional[str] = None
    status: str = "PENDING"
    createdBy: Optional[Dict] = None
    assignedTo: List[PyObjectId] = []
    actions: List[Dict] = []
    deleted: bool = False
    feedbacks: List[Dict] = []
    admin: Optional[PyObjectId] = None


class ComplaintUpdate(BaseModel):
    subject: Optional[str] = None
    complaint: Optional[str] = None
    reference: Optional[str] = None
    category: Optional[PyObjectId] = None
    attachment: Optional[str] = None
    status: Optional[str] = None
    createdBy: Optional[Dict] = None
    assignedTo: Optional[List[PyObjectId]] = None
    actions: Optional[List[Dict]] = None
    deleted: Optional[bool] = None
    feedbacks: Optional[List[Dict]] = None
    admin: Optional[PyObjectId] = None


class ComplaintPublic(Obj):
    subject: str
    complaint: str
    reference: Optional[str] = None
    category: PyObjectId
    attachment: Optional[str] = None
    status: str = "PENDING"
    createdBy: Optional[Dict] = None
    assignedTo: List[PyObjectId] = []
    actions: List[Dict] = []
    deleted: bool = False
    feedbacks: List[Dict] = []
    admin: Optional[PyObjectId] = None
    createdAt: datetime = Field(validation_alias="createdAt")
    updatedAt: datetime = Field(validation_alias="updatedAt")


class ComplaintAction(BaseModel):
    action_type: str
    description: str
    performed_by: PyObjectId
    performed_at: datetime
    notes: Optional[str] = None


class ComplaintFeedback(BaseModel):
    feedback_type: str
    message: str
    provided_by: PyObjectId
    provided_at: datetime
    rating: Optional[int] = None