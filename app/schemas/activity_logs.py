from datetime import datetime
from typing import Optional, Any, List
from pydantic import BaseModel, Field, ConfigDict

class ActorInfo(BaseModel):
    id: str
    name: str
    role: str

class Detail(BaseModel):
    model_config = ConfigDict(extra="allow")

class ActivityPublic(BaseModel):
    action: str
    details: Optional[Detail]
    createdAt: datetime = Field(validation_alias="createdAt")
    updatedAt: Optional[datetime] = Field(default=None, validation_alias="updatedAt")

class Page(BaseModel):
    items: List[ActivityPublic]
    next_cursor: Optional[str] = None
