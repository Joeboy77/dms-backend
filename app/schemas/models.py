from datetime import datetime
from pydantic import BaseModel

from app.schemas.base import Obj
from app.schemas.gateway import Provider, Type

class Page(BaseModel):
    items: list["ModelPublic"]
    next_cursor: str | None = None

class LanguageModel(BaseModel):
    model: str
    url: str | None = None

class ModelCreate(BaseModel):
    provider: Provider
    type: Type
    url: str | None = None
    models: list[LanguageModel]

class ModelUpdate(BaseModel):
    provider: Provider | None = None
    type: Type | None = None
    url: str | None = None
    models: list[LanguageModel] | None = None

class ModelPublic(Obj):
    provider: Provider
    type: Type
    url: str
    models: list[LanguageModel]
    created_at: datetime
    updated_at: datetime | None = None