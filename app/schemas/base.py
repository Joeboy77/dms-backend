from typing import Annotated
from pydantic import BeforeValidator, BaseModel, Field

PyObjectId = Annotated[str, BeforeValidator(str)]


class Obj(BaseModel):
    id: PyObjectId = Field(validation_alias="_id")