from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_db
from app.core.websocket_manager import manager
from app.core.authentication.auth_middleware import get_current_token, TokenData, RoleBasedAccessControl
from bson import ObjectId
from datetime import datetime
import json
import logging
from typing import List, Optional

router = APIRouter(tags=["WebSocket Chat"])

require_supervisor = RoleBasedAccessControl(["projects_supervisor", "projects_coordinator"])

logger = logging.getLogger(__name__)

class ChatMessage:
    def __init__(self, sender_id: str, sender_type: str, content: str, message_type: str = "text", group_id: Optional[str] = None, recipient_id: Optional[str] = None):
        self.sender_id = sender_id
        self.sender_type = sender_type
        self.content = content
        self.message_type = message_type
        self.group_id = group_id
        self.recipient_id = recipient_id
        self.timestamp = datetime.utcnow()

    def to_dict(self):
        return {
            "id": str(ObjectId()),
            "sender_id": self.sender_id,
            "sender_type": self.sender_type,
            "content": self.content,
            "message_type": self.message_type,
            "group_id": self.group_id,
            "recipient_id": self.recipient_id,
            "timestamp": self.timestamp.isoformat(),
            "created_at": self.timestamp.isoformat()
        }

async def authenticate_websocket(websocket: WebSocket, token: str) -> Optional[TokenData]:
    """Authenticate WebSocket connection using JWT token"""
    try:
        from app.core.authentication.auth_token import verify_access_token
        token_data = verify_access_token(token)
        return token_data
    except Exception as e:
        logger.error(f"WebSocket authentication failed: {e}")
        await websocket.close(code=1008, reason="Authentication failed")
        return None

async def get_user_info(db: AsyncIOMotorDatabase, user_id: str, user_type: str) -> Optional[dict]:
    """Get user information from database"""
    try:
        if user_type == "student":
            user = await db["students"].find_one({"_id": ObjectId(user_id)})
            if user:
                return {
                    "id": str(user["_id"]),
                    "name": f"{user.get('surname', '')} {user.get('otherNames', '')}".strip(),
                    "email": user.get("email", ""),
                    "type": "student",
                    "academic_id": user.get("academicId", ""),
                    "image": user.get("image", "")
                }
        elif user_type in ["projects_supervisor", "lecturer"]:
            user = await db["lecturers"].find_one({"_id": ObjectId(user_id)})
            if user:
                return {
                    "id": str(user["_id"]),
                    "name": f"{user.get('surname', '')} {user.get('otherNames', '')}".strip(),
                    "email": user.get("email", ""),
                    "type": "supervisor",
                    "academic_id": user.get("academicId", ""),
                    "image": user.get("image", "")
                }
    except Exception as e:
        logger.error(f"Error getting user info: {e}")
    return None

@router.websocket("/ws/chat/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str, token: str = Query(...)):
    """WebSocket endpoint for real-time chat"""
    logger.info(f"WebSocket connection attempt: user_id={user_id}, token={token[:20]}...")
    
    # Authenticate the connection
    token_data = await authenticate_websocket(websocket, token)
    if not token_data:
        logger.error("WebSocket authentication failed")
        return
    
    logger.info(f"WebSocket authentication successful: role={token_data.role}")
    
    # Get user info from database
    from app.core.database import db
    user_info = await get_user_info(db, user_id, token_data.role)
    if not user_info:
        logger.error(f"User not found: user_id={user_id}, role={token_data.role}")
        await websocket.close(code=1008, reason="User not found")
        return
    
    # Connect the user
    logger.info(f"Connecting user to WebSocket manager: user_id={user_id}")
    await manager.connect(websocket, user_id, user_info)
    logger.info(f"User connected successfully: user_id={user_id}")
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            message_type = message_data.get("type", "message")
            
            if message_type == "message":
                await handle_chat_message(db, user_id, user_info, message_data)
            elif message_type == "join_group":
                await handle_join_group(user_id, message_data)
            elif message_type == "leave_group":
                await handle_leave_group(user_id, message_data)
            elif message_type == "typing":
                await handle_typing_indicator(user_id, message_data)
            elif message_type == "ping":
                await manager.send_personal_message({"type": "pong"}, user_id)
                
    except WebSocketDisconnect:
        manager.disconnect(user_id)
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        manager.disconnect(user_id)

async def handle_chat_message(db: AsyncIOMotorDatabase, sender_id: str, sender_info: dict, message_data: dict):
    """Handle incoming chat messages"""
    try:
        content = message_data.get("content", "").strip()
        if not content:
            return
        
        message_type = message_data.get("message_type", "text")
        group_id = message_data.get("group_id")
        recipient_id = message_data.get("recipient_id")
        
        # Create message object
        chat_message = ChatMessage(
            sender_id=sender_id,
            sender_type=sender_info["type"],
            content=content,
            message_type=message_type,
            group_id=group_id,
            recipient_id=recipient_id
        )
        
        message_dict = chat_message.to_dict()
        
        # Save message to database
        await save_message_to_db(db, message_dict)
        
        # Send message to recipients
        if group_id:
            await handle_group_message(db, sender_id, group_id, message_dict)
        elif recipient_id:
            await handle_individual_message(sender_id, recipient_id, message_dict)
        else:
            logger.error("No group_id or recipient_id provided")
            
    except Exception as e:
        logger.error(f"Error handling chat message: {e}")

async def handle_group_message(db: AsyncIOMotorDatabase, sender_id: str, group_id: str, message_dict: dict):
    """Handle group messages"""
    try:
        # Get group members from database
        group = await db["groups"].find_one({"_id": ObjectId(group_id)})
        if not group:
            logger.error(f"Group {group_id} not found")
            return
        
        # Get all group members
        member_ids = group.get("members", [])
        
        # Send message to all online group members except sender
        for member_id in member_ids:
            member_id_str = str(member_id)
            if member_id_str != sender_id and manager.is_user_connected(member_id_str):
                await manager.send_personal_message({
                    "type": "group_message",
                    "group_id": group_id,
                    "message": message_dict,
                    "sender_info": {
                        "id": sender_id,
                        "name": message_dict.get("sender_name", "Unknown"),
                        "type": message_dict.get("sender_type", "unknown")
                    }
                }, member_id_str)
        
        # Also send to supervisor if they're online
        supervisor_id = str(group.get("supervisor"))
        if supervisor_id != sender_id and manager.is_user_connected(supervisor_id):
            await manager.send_personal_message({
                "type": "group_message",
                "group_id": group_id,
                "message": message_dict,
                "sender_info": {
                    "id": sender_id,
                    "name": message_dict.get("sender_name", "Unknown"),
                    "type": message_dict.get("sender_type", "unknown")
                }
            }, supervisor_id)
            
    except Exception as e:
        logger.error(f"Error handling group message: {e}")

async def handle_individual_message(sender_id: str, recipient_id: str, message_dict: dict):
    """Handle individual messages"""
    try:
        # Send message to recipient if they're online
        if manager.is_user_connected(recipient_id):
            await manager.send_personal_message({
                "type": "individual_message",
                "message": message_dict,
                "sender_info": {
                    "id": sender_id,
                    "name": message_dict.get("sender_name", "Unknown"),
                    "type": message_dict.get("sender_type", "unknown")
                }
            }, recipient_id)
        
        # Send confirmation back to sender
        await manager.send_personal_message({
            "type": "message_sent",
            "message_id": message_dict["id"],
            "recipient_id": recipient_id
        }, sender_id)
        
    except Exception as e:
        logger.error(f"Error handling individual message: {e}")

async def handle_join_group(user_id: str, message_data: dict):
    """Handle user joining a group for real-time updates"""
    group_id = message_data.get("group_id")
    if group_id:
        manager.add_user_to_group(user_id, group_id)
        await manager.send_personal_message({
            "type": "joined_group",
            "group_id": group_id
        }, user_id)

async def handle_leave_group(user_id: str, message_data: dict):
    """Handle user leaving a group"""
    group_id = message_data.get("group_id")
    if group_id:
        manager.remove_user_from_group(user_id, group_id)
        await manager.send_personal_message({
            "type": "left_group",
            "group_id": group_id
        }, user_id)

async def handle_typing_indicator(user_id: str, message_data: dict):
    """Handle typing indicators"""
    recipient_id = message_data.get("recipient_id")
    group_id = message_data.get("group_id")
    is_typing = message_data.get("is_typing", False)
    
    if recipient_id and manager.is_user_connected(recipient_id):
        await manager.send_personal_message({
            "type": "typing_indicator",
            "sender_id": user_id,
            "is_typing": is_typing
        }, recipient_id)
    elif group_id:
        # Send typing indicator to all group members
        if group_id in manager.group_members:
            for member_id in manager.group_members[group_id]:
                if member_id != user_id and manager.is_user_connected(member_id):
                    await manager.send_personal_message({
                        "type": "typing_indicator",
                        "sender_id": user_id,
                        "group_id": group_id,
                        "is_typing": is_typing
                    }, member_id)

async def save_message_to_db(db: AsyncIOMotorDatabase, message_dict: dict):
    """Save message to database"""
    try:
        # Add to messages collection
        await db["messages"].insert_one(message_dict)
        
        # Update conversation/communication record
        conversation_data = {
            "last_message": message_dict["content"],
            "last_message_at": message_dict["timestamp"],
            "updated_at": datetime.utcnow()
        }
        
        if message_dict.get("group_id"):
            # Update group conversation
            await db["group_conversations"].update_one(
                {"group_id": ObjectId(message_dict["group_id"])},
                {"$set": conversation_data},
                upsert=True
            )
        elif message_dict.get("recipient_id"):
            # Update individual conversation
            participants = sorted([message_dict["sender_id"], message_dict["recipient_id"]])
            await db["individual_conversations"].update_one(
                {"participants": participants},
                {"$set": conversation_data},
                upsert=True
            )
            
    except Exception as e:
        logger.error(f"Error saving message to database: {e}")

# Additional endpoints for chat functionality

@router.get("/chat/groups")
async def get_supervisor_groups(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_supervisor)
):
    """Get all groups for a supervisor to enable group chat"""
    try:
        supervisor_academic_id = current_user.email
        if not supervisor_academic_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing supervisor ID")
        
        supervisor = await db["lecturers"].find_one({"academicId": supervisor_academic_id})
        if not supervisor:
            raise HTTPException(status_code=404, detail="Supervisor not found")
        
        supervisor_id = supervisor["_id"]
        
        groups = await db["groups"].find({
            "supervisor": supervisor_id,
            "status": "active"
        }).to_list(length=None)
        
        group_list = []
        for group in groups:
            # Get group members info
            member_ids = group.get("members", [])
            members = await db["students"].find({
                "_id": {"$in": member_ids}
            }).to_list(length=None)
            
            group_list.append({
                "id": str(group["_id"]),
                "name": group.get("name", ""),
                "project_topic": group.get("project_topic", ""),
                "member_count": len(members),
                "members": [
                    {
                        "id": str(member["_id"]),
                        "name": f"{member.get('surname', '')} {member.get('otherNames', '')}".strip(),
                        "email": member.get("email", ""),
                        "academic_id": member.get("academicId", ""),
                        "image": member.get("image", "")
                    }
                    for member in members
                ]
            })
        
        return {"groups": group_list}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching groups: {str(e)}")

@router.get("/chat/students")
async def get_supervisor_students(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_supervisor)
):
    """Get all students for a supervisor to enable individual chat"""
    try:
        supervisor_academic_id = current_user.email
        if not supervisor_academic_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing supervisor ID")
        
        supervisor = await db["lecturers"].find_one({"academicId": supervisor_academic_id})
        if not supervisor:
            raise HTTPException(status_code=404, detail="Supervisor not found")
        
        supervisor_id = supervisor["_id"]
        
        # Get students assigned to this supervisor
        fyps = await db["fyps"].find({
            "supervisor": supervisor_id
        }).to_list(length=None)
        
        student_ids = [fyp["student"] for fyp in fyps]
        
        if not student_ids:
            return {"students": []}
        
        students = await db["students"].find({
            "_id": {"$in": student_ids}
        }).to_list(length=None)
        
        student_list = []
        for student in students:
            student_list.append({
                "id": str(student["_id"]),
                "name": f"{student.get('surname', '')} {student.get('otherNames', '')}".strip(),
                "email": student.get("email", ""),
                "academic_id": student.get("academicId", ""),
                "image": student.get("image", ""),
                "program": student.get("program", ""),
                "type": student.get("type", "UNDERGRADUATE")
            })
        
        return {"students": student_list}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching students: {str(e)}")

@router.get("/chat/conversations/{user_id}")
async def get_user_conversations(
    user_id: str,
    user_type: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Get all conversations for a user"""
    try:
        conversations = []
        
        # Get individual conversations
        individual_conversations = await db["individual_conversations"].find({
            "participants": {"$in": [user_id]}
        }).to_list(length=None)
        
        for conv in individual_conversations:
            participants = conv.get("participants", [])
            other_participant = [p for p in participants if p != user_id]
            if other_participant:
                # Get other participant info
                other_user = await get_user_info(db, other_participant[0], "student")
                if other_user:
                    conversations.append({
                        "id": str(conv["_id"]),
                        "type": "individual",
                        "participant": other_user,
                        "last_message": conv.get("last_message", ""),
                        "last_message_at": conv.get("last_message_at", ""),
                        "unread_count": 0  # TODO: Implement unread count
                    })
        
        # Get group conversations
        if user_type in ["projects_supervisor", "lecturer"]:
            # Get groups supervised by this user
            groups = await db["groups"].find({
                "supervisor": ObjectId(user_id),
                "status": "active"
            }).to_list(length=None)
            
            for group in groups:
                group_conversations = await db["group_conversations"].find({
                    "group_id": group["_id"]
                }).to_list(length=None)
                
                for conv in group_conversations:
                    conversations.append({
                        "id": str(conv["_id"]),
                        "type": "group",
                        "group": {
                            "id": str(group["_id"]),
                            "name": group.get("name", ""),
                            "project_topic": group.get("project_topic", ""),
                            "member_count": len(group.get("members", []))
                        },
                        "last_message": conv.get("last_message", ""),
                        "last_message_at": conv.get("last_message_at", ""),
                        "unread_count": 0  # TODO: Implement unread count
                    })
        
        # Sort by last message time
        conversations.sort(key=lambda x: x.get("last_message_at", ""), reverse=True)
        
        return {"conversations": conversations}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching conversations: {str(e)}")
