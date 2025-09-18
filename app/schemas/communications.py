from datetime import datetime
from pydantic import BaseModel, Field

from app.schemas.base import Obj, PyObjectId


class Page(BaseModel):
    items: list["CommunicationPublic"]
    next_cursor: str | None = None


class Participant(BaseModel):
    participantId: PyObjectId
    userType: str  # "student", "lecturer", "admin", etc.
    email: str


class Recipient(BaseModel):
    participantId: PyObjectId
    userType: str
    email: str
    _id: PyObjectId | None = None


class Reply(BaseModel):
    sender: Participant
    text: str  # Base64 encoded message
    _id: PyObjectId | None = None
    createdAt: datetime | None = None
    updatedAt: datetime | None = None


class CommunicationCreate(BaseModel):
    sender: Participant
    recipients: list[Recipient]
    text: str  # Base64 encoded message
    replies: list[Reply] = []


class CommunicationUpdate(BaseModel):
    sender: Participant | None = None
    recipients: list[Recipient] | None = None
    text: str | None = None
    replies: list[Reply] | None = None


class CommunicationPublic(Obj):
    sender: Participant
    recipients: list[Recipient]
    text: str  # Base64 encoded message
    replies: list[Reply] = []
    createdAt: datetime = Field(validation_alias="createdAt")
    updatedAt: datetime = Field(validation_alias="updatedAt")


class SendMessageRequest(BaseModel):
    recipients: list[Recipient]
    text: str  # Base64 encoded message


class ReplyMessageRequest(BaseModel):
    text: str  # Base64 encoded message
    sender: Participant


class GetConversationsRequest(BaseModel):
    participant_id: str
    user_type: str