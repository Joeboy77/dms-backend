from enum import Enum
from typing import Optional, List, Dict
from pydantic import BaseModel

class Provider(str, Enum):
    openai = "openai"
    groq = "groq"
    quest = "quest"

class Type(str, Enum):
    text = "text"
    audio = "audio"
    image = "image"

class Role(str, Enum):
    system = "system"
    user = "user"
    assistant = "assistant"
    tool = "tool"

class Messages(BaseModel):
    role: Role
    content: str

class ChatCompletionRequestV1(BaseModel):
    provider: Provider
    type: Type
    model: str
    messages: List[Messages]
    response_format: Optional[Dict] = None
    tools: Optional[List[Dict]] = None
    stream: bool = False
    temperature: float = 0.0

class ChatCompletionRequestV2(BaseModel):
    model: str
    messages: List[Messages]
    response_format: Optional[Dict] = None
    tools: Optional[List[Dict]] = None
    stream: bool = False
    temperature: float = 0.0


