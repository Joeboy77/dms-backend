from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field

from app.schemas.base import Obj, PyObjectId


class Page(BaseModel):
    items: List["ProjectPublic"]
    next_cursor: Optional[str] = None
    
    
class ProjectCreate(BaseModel):
    title: str
    description: str
    project_area_id: PyObjectId
    
    
class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    project_area_id: Optional[PyObjectId] = None
    
    
class ProjectPublic(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    group_id: PyObjectId
    title: str
    description: str
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)

    
    
class ProjectWithDetails(BaseModel):
    project: ProjectPublic
    project_area: Optional[Dict] = None
    staff: List[Dict] = []
    
    
class AllProjectsWithDetails(BaseModel):
    projects: List[ProjectPublic]