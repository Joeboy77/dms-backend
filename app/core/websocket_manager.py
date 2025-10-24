from typing import Dict, List, Set
import json
import asyncio
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Store active connections by user_id
        self.active_connections: Dict[str, WebSocket] = {}
        # Store user info for each connection
        self.user_info: Dict[str, dict] = {}
        # Store group memberships for group messaging
        self.group_members: Dict[str, Set[str]] = {}

    async def connect(self, websocket: WebSocket, user_id: str, user_info: dict):
        """Accept a new WebSocket connection and store user info"""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        self.user_info[user_id] = user_info
        
        logger.info(f"User {user_id} connected. Total connections: {len(self.active_connections)}")
        
        # Send connection confirmation
        await self.send_personal_message({
            "type": "connection_established",
            "message": "Connected to chat server",
            "timestamp": datetime.utcnow().isoformat()
        }, user_id)

    def disconnect(self, user_id: str):
        """Remove a WebSocket connection"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        if user_id in self.user_info:
            del self.user_info[user_id]
        
        # Remove from all groups
        for group_id, members in self.group_members.items():
            members.discard(user_id)
            if not members:  # Remove empty groups
                del self.group_members[group_id]
        
        logger.info(f"User {user_id} disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: dict, user_id: str):
        """Send a message to a specific user"""
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to {user_id}: {e}")
                # Remove the connection if it's broken
                self.disconnect(user_id)

    async def send_group_message(self, message: dict, group_id: str, sender_id: str):
        """Send a message to all members of a group except the sender"""
        if group_id in self.group_members:
            for user_id in self.group_members[group_id]:
                if user_id != sender_id:  # Don't send to sender
                    await self.send_personal_message(message, user_id)

    async def broadcast_to_supervisor_students(self, message: dict, supervisor_id: str, sender_id: str):
        """Send a message to all students supervised by a specific supervisor"""
        # This will be implemented with database lookup
        # For now, we'll use a placeholder
        pass

    def add_user_to_group(self, user_id: str, group_id: str):
        """Add a user to a group for group messaging"""
        if group_id not in self.group_members:
            self.group_members[group_id] = set()
        self.group_members[group_id].add(user_id)

    def remove_user_from_group(self, user_id: str, group_id: str):
        """Remove a user from a group"""
        if group_id in self.group_members:
            self.group_members[group_id].discard(user_id)
            if not self.group_members[group_id]:  # Remove empty groups
                del self.group_members[group_id]

    def get_connected_users(self) -> List[dict]:
        """Get list of all connected users"""
        return [
            {"user_id": user_id, "user_info": info}
            for user_id, info in self.user_info.items()
        ]

    def is_user_connected(self, user_id: str) -> bool:
        """Check if a user is currently connected"""
        return user_id in self.active_connections

# Global connection manager instance
manager = ConnectionManager()
