from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from app.schemas.base import Obj, PyObjectId


class Page(BaseModel):
    items: list[AnnouncementPublic]
    next_cursor: str | None = None


class AnnouncementCreate(BaseModel):
    subject: str
    content: str
    # If omitted or empty, announcement will be sent to ALL students under the supervisor
    recipient_ids: list[PyObjectId] | None = None
    priority: str = "normal"
    attachments: list[str] | None = None
    
    model_config = ConfigDict(populate_by_name=True)


class AnnouncementUpdate(BaseModel):
    subject: str | None = None
    content: str | None = None
    priority: str | None = None
    attachments: list[str] | None = None


class AnnouncementPublic(Obj):
    subject: str
    content: str
    sender_id: PyObjectId
    sender_name: str
    sender_email: str
    recipient_ids: list[PyObjectId]
    recipients: list[dict] | None = None
    priority: str = "normal"
    attachments: list[str] | None = None
    created_at: datetime
    updated_at: datetime | None = None
    
    model_config = ConfigDict(populate_by_name=True)

