import uuid
from pydantic import BeforeValidator, BaseModel, Field
from typing import Annotated

PyObjectId = Annotated[str, BeforeValidator(str)]

class QueryVectorStore(BaseModel):
    query: str
    k: int = 4
    pre_filter: dict | None = None

class CreateVectorIndex(BaseModel):
    store_name: str | None  = Field(default_factory=lambda: str(uuid.uuid4()))
    pre_filter_field_names: list[str] = []






