from datetime import datetime
from typing import Optional, List, Dict
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException


class CommunicationController:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db["communications"]

    async def get_all_communications(self, limit: int = 10, cursor: Optional[str] = None):
        query = {}
        if cursor:
            query["_id"] = {"$gt": ObjectId(cursor)}

        communications = await self.collection.find(query).limit(limit).to_list(limit)

        next_cursor = None
        if len(communications) == limit:
            next_cursor = str(communications[-1]["_id"])

        return {
            "items": communications,
            "next_cursor": next_cursor
        }

    async def get_communication_by_id(self, communication_id: str):
        communication = await self.collection.find_one({"_id": ObjectId(communication_id)})
        if not communication:
            raise HTTPException(status_code=404, detail="Communication not found")
        return communication

    async def send_message(self, message_data: dict):
        message_data["createdAt"] = datetime.now()
        message_data["updatedAt"] = datetime.now()

        if "sender" in message_data and "participantId" in message_data["sender"]:
            sender_id = message_data["sender"]["participantId"]
            if isinstance(sender_id, str):
                message_data["sender"]["participantId"] = ObjectId(sender_id)

        for recipient in message_data.get("recipients", []):
            if "participantId" in recipient:
                recipient_id = recipient["participantId"]
                if isinstance(recipient_id, str):
                    recipient["participantId"] = ObjectId(recipient_id)
            if not recipient.get("_id"):
                recipient["_id"] = ObjectId()

        result = await self.collection.insert_one(message_data)
        created_message = await self.collection.find_one({"_id": result.inserted_id})
        return created_message

    async def reply_to_message(self, communication_id: str, reply_data: dict):
        reply_data["_id"] = ObjectId()
        reply_data["createdAt"] = datetime.now()
        reply_data["updatedAt"] = datetime.now()

        result = await self.collection.update_one(
            {"_id": ObjectId(communication_id)},
            {
                "$push": {"replies": reply_data},
                "$set": {"updatedAt": datetime.now()}
            }
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Communication not found")

        updated_communication = await self.collection.find_one({"_id": ObjectId(communication_id)})
        return updated_communication

    async def get_conversations_for_user(self, participant_id: str, user_type: str):
        """Get all conversations where the user is either sender or recipient"""
        query = {
            "$or": [
                {
                    "sender.participantId": ObjectId(participant_id),
                    "sender.userType": user_type
                },
                {
                    "recipients.participantId": ObjectId(participant_id),
                    "recipients.userType": user_type
                }
            ]
        }

        communications = await self.collection.find(query).sort("updatedAt", -1).to_list(None)
        return communications

    async def get_conversation_between_users(self, user1_id: str, user1_type: str, user2_id: str, user2_type: str):
        """Get conversation between two specific users"""
        query = {
            "$or": [
                {
                    "$and": [
                        {"sender.participantId": ObjectId(user1_id), "sender.userType": user1_type},
                        {"recipients.participantId": ObjectId(user2_id), "recipients.userType": user2_type}
                    ]
                },
                {
                    "$and": [
                        {"sender.participantId": ObjectId(user2_id), "sender.userType": user2_type},
                        {"recipients.participantId": ObjectId(user1_id), "recipients.userType": user1_type}
                    ]
                }
            ]
        }

        communications = await self.collection.find(query).sort("createdAt", 1).to_list(None)
        return communications

    async def mark_as_read(self, communication_id: str, participant_id: str):
        """Mark a message as read by a specific participant"""
        result = await self.collection.update_one(
            {
                "_id": ObjectId(communication_id),
                "recipients.participantId": ObjectId(participant_id)
            },
            {
                "$set": {
                    "recipients.$.readAt": datetime.now(),
                    "updatedAt": datetime.now()
                }
            }
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Communication or recipient not found")

        updated_communication = await self.collection.find_one({"_id": ObjectId(communication_id)})
        return updated_communication

    async def delete_communication(self, communication_id: str):
        result = await self.collection.delete_one({"_id": ObjectId(communication_id)})

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Communication not found")

        return {"message": "Communication deleted successfully"}

    async def search_messages(self, participant_id: str, search_term: str):
        """Search messages for a specific participant"""
        # Note: This searches in base64 encoded text, you might want to decode first
        query = {
            "$and": [
                {
                    "$or": [
                        {"sender.participantId": ObjectId(participant_id)},
                        {"recipients.participantId": ObjectId(participant_id)}
                    ]
                },
                {
                    "$or": [
                        {"text": {"$regex": search_term, "$options": "i"}},
                        {"replies.text": {"$regex": search_term, "$options": "i"}}
                    ]
                }
            ]
        }

        communications = await self.collection.find(query).sort("updatedAt", -1).to_list(None)
        return communications

    async def get_unread_count(self, participant_id: str, user_type: str):
        """Get count of unread messages for a user"""
        query = {
            "recipients": {
                "$elemMatch": {
                    "participantId": ObjectId(participant_id),
                    "userType": user_type,
                    "readAt": {"$exists": False}
                }
            }
        }

        unread_count = await self.collection.count_documents(query)
        return {"unread_count": unread_count}

    async def get_recent_conversations(self, participant_id: str, user_type: str, limit: int = 10):
        """Get recent conversations for a user"""
        conversations = await self.get_conversations_for_user(participant_id, user_type)

        # Group by conversation participants and get most recent message
        conversation_map = {}
        for comm in conversations:
            # Create a unique key for the conversation
            participants = []

            # Add sender
            sender_key = f"{comm['sender']['participantId']}_{comm['sender']['userType']}"
            participants.append(sender_key)

            # Add recipients
            for recipient in comm["recipients"]:
                recipient_key = f"{recipient['participantId']}_{recipient['userType']}"
                participants.append(recipient_key)

            # Remove current user and sort to create consistent key
            current_user_key = f"{participant_id}_{user_type}"
            participants = [p for p in participants if p != current_user_key]
            conversation_key = "_".join(sorted(participants))

            # Keep most recent communication for each conversation
            if conversation_key not in conversation_map or comm["updatedAt"] > conversation_map[conversation_key]["updatedAt"]:
                conversation_map[conversation_key] = comm

        # Return most recent conversations
        recent_conversations = list(conversation_map.values())
        recent_conversations.sort(key=lambda x: x["updatedAt"], reverse=True)

        return recent_conversations[:limit]

    async def get_available_contacts(self, participant_id: str, user_type: str):
        """Get all people a user can communicate with based on their role"""
        contacts = []

        if user_type.lower() == "student":
            # For students: get group members and their supervisor

            # 1. Get groups the student belongs to
            groups = await self.db["groups"].find({"student_ids": ObjectId(participant_id)}).to_list(None)

            group_member_ids = set()
            for group in groups:
                for student_id in group.get("student_ids", []):
                    if str(student_id) != participant_id:  # Exclude self
                        group_member_ids.add(student_id)

            # Get group member details
            if group_member_ids:
                group_members = await self.db["students"].find({
                    "_id": {"$in": list(group_member_ids)}
                }).to_list(None)

                for member in group_members:
                    student_name = f"{member.get('surname', '')} {member.get('otherNames', '')}".strip()
                    contacts.append({
                        "participantId": str(member["_id"]),
                        "userType": "student",
                        "email": member.get("email", ""),
                        "name": student_name,
                        "title": member.get("title", ""),
                        "relationship": "group_member",
                        "academic_id": member.get("academicId", "")
                    })

            # 2. Get student's supervisor from FYP
            fyp = await self.db["fyps"].find_one({"student": ObjectId(participant_id)})
            if fyp and fyp.get("supervisor"):
                supervisor = await self.db["lecturers"].find_one({"_id": fyp["supervisor"]})
                if supervisor:
                    supervisor_name = f"{supervisor.get('surname', '')} {supervisor.get('otherNames', '')}".strip()
                    contacts.append({
                        "participantId": str(supervisor["_id"]),
                        "userType": "lecturer",
                        "email": supervisor.get("email", ""),
                        "name": supervisor_name,
                        "title": supervisor.get("title", ""),
                        "position": supervisor.get("position", ""),
                        "relationship": "supervisor",
                        "academic_id": supervisor.get("academicId", "")
                    })

        elif user_type.lower() == "projects_supervisor" or user_type.lower() == "lecturer":
            # For supervisors: get all students they supervise
            supervised_fyps = await self.db["fyps"].find({"supervisor": ObjectId(participant_id)}).to_list(None)

            student_ids = [fyp["student"] for fyp in supervised_fyps]

            if student_ids:
                students = await self.db["students"].find({
                    "_id": {"$in": student_ids}
                }).to_list(None)

                for student in students:
                    student_name = f"{student.get('surname', '')} {student.get('otherNames', '')}".strip()
                    contacts.append({
                        "participantId": str(student["_id"]),
                        "userType": "student",
                        "email": student.get("email", ""),
                        "name": student_name,
                        "title": student.get("title", ""),
                        "relationship": "supervised_student",
                        "academic_id": student.get("academicId", ""),
                        "type": student.get("type", "UNDERGRADUATE")
                    })

        elif user_type.lower() == "projects_coordinator" or user_type.lower() == "coordinator":
            lecturers = await self.db["lecturers"].find({}).to_list(None)
            
            for lecturer in lecturers:
                lecturer_name = f"{lecturer.get('surname', '')} {lecturer.get('otherNames', '')}".strip()
                contacts.append({
                    "participantId": str(lecturer["_id"]),
                    "userType": "projects_supervisor",
                    "email": lecturer.get("email", ""),
                    "name": lecturer_name,
                    "title": lecturer.get("title", ""),
                    "position": lecturer.get("position", ""),
                    "relationship": "supervisor",
                    "academic_id": lecturer.get("academicId", ""),
                    "image": lecturer.get("image")
                })

        elif user_type.lower() == "admin":
            # For admins: they can communicate with everyone (optional implementation)
            # You might want to limit this or implement different logic
            pass

        # Remove duplicates based on participantId
        seen = set()
        unique_contacts = []
        for contact in contacts:
            contact_key = f"{contact['participantId']}_{contact['userType']}"
            if contact_key not in seen:
                seen.add(contact_key)
                unique_contacts.append(contact)

        # Sort by name
        unique_contacts.sort(key=lambda x: x.get("name", ""))

        return unique_contacts