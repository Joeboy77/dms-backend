from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

from app.schemas.base import Obj
from app.schemas.gateway import Provider, Type

class Page(BaseModel):
    items: List["ModelPublic"]
    next_cursor: Optional[str] = None

class LanguageModel(BaseModel):
    model: str
    url: Optional[str] = None

class ModelCreate(BaseModel):
    provider: Provider
    type: Type
    url: Optional[str] = None
    models: List[LanguageModel]

class ModelUpdate(BaseModel):
    provider: Optional[Provider] = None
    type: Optional[Type] = None
    url: Optional[str] = None
    models: Optional[List[LanguageModel]] = None

class ModelPublic(Obj):
    provider: Provider
    type: Type
    url: str
    models: List[LanguageModel]
    created_at: datetime
    updated_at: Optional[datetime] = None