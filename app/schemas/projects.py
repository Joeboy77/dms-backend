from datetime import datetime
from pydantic import BaseModel, Field

from app.schemas.base import Obj, PyObjectId


class Page(BaseModel):
    items: list["ProjectPublic"]
    next_cursor: str | None = None
    
    
class ProjectCreate(BaseModel):
    title: str
    description: str
    project_area_id: PyObjectId
    
    
class ProjectUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    project_area_id: PyObjectId | None = None
    
    
class ProjectPublic(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    group_id: PyObjectId
    title: str
    description: str
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)

    
    
class ProjectWithDetails(BaseModel):
    project: ProjectPublic
    project_area: dict | None = None
    staff: list[dict] = []
    
    
class AllProjectsWithDetails(BaseModel):
    projects: list[ProjectPublic]
    # project_areas: list[dict] = []
    # staff: list[dict] = []