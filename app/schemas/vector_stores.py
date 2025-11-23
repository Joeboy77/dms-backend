import uuid
from pydantic import BeforeValidator, BaseModel, Field
from typing import Annotated, Optional, List, Dict

PyObjectId = Annotated[str, BeforeValidator(str)]

class QueryVectorStore(BaseModel):
    query: str
    k: int = 4
    pre_filter: Optional[Dict] = None

class CreateVectorIndex(BaseModel):
    store_name: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    pre_filter_field_names: List[str] = []






