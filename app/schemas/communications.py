from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from app.schemas.base import Obj, PyObjectId


class Page(BaseModel):
    items: List["CommunicationPublic"]
    next_cursor: Optional[str] = None


class Participant(BaseModel):
    participantId: PyObjectId
    userType: str
    email: str


class Recipient(BaseModel):
    participantId: PyObjectId
    userType: str
    email: str
    _id: Optional[PyObjectId] = None


class Reply(BaseModel):
    sender: Participant
    text: str
    _id: Optional[PyObjectId] = None
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None


class CommunicationCreate(BaseModel):
    sender: Participant
    recipients: List[Recipient]
    text: str
    replies: List[Reply] = []


class CommunicationUpdate(BaseModel):
    sender: Optional[Participant] = None
    recipients: Optional[List[Recipient]] = None
    text: Optional[str] = None
    replies: Optional[List[Reply]] = None


class CommunicationPublic(Obj):
    sender: Participant
    recipients: List[Recipient]
    text: str
    replies: List[Reply] = []
    createdAt: datetime = Field(validation_alias="createdAt")
    updatedAt: datetime = Field(validation_alias="updatedAt")


class SendMessageRequest(BaseModel):
    recipients: List[Recipient]
    text: str


class ReplyMessageRequest(BaseModel):
    text: str
    sender: Participant


class GetConversationsRequest(BaseModel):
    participant_id: str
    user_type: str