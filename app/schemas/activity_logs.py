from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field, ConfigDict

# ✅ Actor information (if needed)
class ActorInfo(BaseModel):
    id: str
    name: str
    role: str  # e.g. "admin", "supervisor", "student"

# ✅ Flexible details structure
class Detail(BaseModel):
    # status: Optional[int] = None
    # message: Optional[str] = None
    # requestType: Optional[str] = None
    model_config = ConfigDict(extra="allow")

    # class Config:
    #     # Allow any extra fields that exist in MongoDB documents
    #     extra = "allow"

# ✅ Activity public schema
class ActivityPublic(BaseModel):
    action: str
    details: Optional[Detail]
    createdAt: datetime = Field(validation_alias="createdAt")
    updatedAt: Optional[datetime] = Field(default=None, validation_alias="updatedAt")

# ✅ Paginated response model
class Page(BaseModel):
    items: list[ActivityPublic]
    next_cursor: Optional[str] = None
