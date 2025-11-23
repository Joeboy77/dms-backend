from __future__ import annotations
from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, ConfigDict

from app.schemas.base import Obj, PyObjectId


class Page(BaseModel):
    items: List[AnnouncementPublic]
    next_cursor: Optional[str] = None


class AnnouncementCreate(BaseModel):
    subject: str
    content: str
    recipient_ids: Optional[List[PyObjectId]] = None
    priority: str = "normal"
    attachments: Optional[List[str]] = None
    
    model_config = ConfigDict(populate_by_name=True)


class AnnouncementUpdate(BaseModel):
    subject: Optional[str] = None
    content: Optional[str] = None
    priority: Optional[str] = None
    attachments: Optional[List[str]] = None


class AnnouncementPublic(Obj):
    subject: str
    content: str
    sender_id: PyObjectId
    sender_name: str
    sender_email: str
    recipient_ids: List[PyObjectId]
    recipients: Optional[List[Dict]] = None
    priority: str = "normal"
    attachments: Optional[List[str]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(populate_by_name=True)

