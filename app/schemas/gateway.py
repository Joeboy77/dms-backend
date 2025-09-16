from enum import Enum
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
    messages: list[Messages]
    response_format: dict| None = None
    tools: list[dict] | None = None
    stream: bool = False
    temperature: float = 0.0

class ChatCompletionRequestV2(BaseModel):
    model: str
    messages: list[Messages]
    response_format: dict| None = None
    tools: list[dict] | None = None
    stream: bool = False
    temperature: float = 0.0


