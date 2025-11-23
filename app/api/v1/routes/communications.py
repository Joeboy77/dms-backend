from fastapi import APIRouter, Depends, Query, responses, HTTPException
from typing import Optional, List, Dict
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from app.core.database import get_db
from app.schemas.communications import (
    CommunicationCreate,
    CommunicationPublic,
    CommunicationUpdate,
    Page,
    SendMessageRequest,
    ReplyMessageRequest,
    Participant
)
from app.controllers.communications import CommunicationController

router = APIRouter(tags=["Communications"])


class MarkAsReadRequest(BaseModel):
    participant_id: str


class SearchMessagesRequest(BaseModel):
    participant_id: str
    search_term: str


@router.get("/communications", response_model=Page)
async def get_all_communications(
    limit: int = Query(10, alias="limit", ge=1, le=100),
    cursor: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = CommunicationController(db)
    return await controller.get_all_communications(limit=limit, cursor=cursor)


@router.get("/communications/{id}", response_model=CommunicationPublic)
async def get_communication(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = CommunicationController(db)
    return await controller.get_communication_by_id(id)


@router.post("/communications/send", response_model=CommunicationPublic)
async def send_message(
    message_request: SendMessageRequest,
    sender: Participant,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = CommunicationController(db)
    message_data = {
        "sender": sender.model_dump(),
        "recipients": [recipient.model_dump() for recipient in message_request.recipients],
        "text": message_request.text,
        "replies": []
    }
    return await controller.send_message(message_data)


@router.post("/communications/{id}/reply", response_model=CommunicationPublic)
async def reply_to_message(
    id: str,
    reply_request: ReplyMessageRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = CommunicationController(db)
    reply_data = {
        "sender": reply_request.sender.model_dump(),
        "text": reply_request.text
    }
    return await controller.reply_to_message(id, reply_data)


@router.get("/communications/user/{participant_id}/{user_type}", response_model=List[CommunicationPublic])
async def get_user_conversations(
    participant_id: str,
    user_type: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = CommunicationController(db)
    return await controller.get_conversations_for_user(participant_id, user_type)


@router.get("/communications/between/{user1_id}/{user1_type}/{user2_id}/{user2_type}")
async def get_conversation_between_users(
    user1_id: str,
    user1_type: str,
    user2_id: str,
    user2_type: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = CommunicationController(db)
    return await controller.get_conversation_between_users(user1_id, user1_type, user2_id, user2_type)


@router.get("/communications/recent/{participant_id}/{user_type}")
async def get_recent_conversations(
    participant_id: str,
    user_type: str,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = CommunicationController(db)
    return await controller.get_recent_conversations(participant_id, user_type, limit)


@router.patch("/communications/{id}/mark-read", response_model=CommunicationPublic)
async def mark_message_as_read(
    id: str,
    mark_read_request: MarkAsReadRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = CommunicationController(db)
    return await controller.mark_as_read(id, mark_read_request.participant_id)


@router.get("/communications/unread-count/{participant_id}/{user_type}")
async def get_unread_count(
    participant_id: str,
    user_type: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = CommunicationController(db)
    return await controller.get_unread_count(participant_id, user_type)


@router.post("/communications/search")
async def search_messages(
    search_request: SearchMessagesRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = CommunicationController(db)
    return await controller.search_messages(search_request.participant_id, search_request.search_term)


@router.delete("/communications/{id}", status_code=204)
async def delete_communication(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = CommunicationController(db)
    await controller.delete_communication(id)
    return responses.Response(status_code=204)


@router.patch("/communications/{id}", response_model=CommunicationPublic)
async def update_communication(
    id: str,
    communication: CommunicationUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = CommunicationController(db)
    update_data = communication.model_dump()

    # This would need custom logic since communications are typically immutable
    # You might want to restrict what can be updated
    raise HTTPException(status_code=501, detail="Communication updates not implemented")


@router.get("/communications/contacts/{participant_id}/{user_type}")
async def get_available_contacts(
    participant_id: str,
    user_type: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Get all people a user can communicate with based on their role:
    - Students: Can talk to group members and their supervisor
    - Supervisors/Lecturers: Can talk to all students they supervise
    - Admins: Can talk to everyone (if implemented)
    """
    controller = CommunicationController(db)
    return await controller.get_available_contacts(participant_id, user_type)