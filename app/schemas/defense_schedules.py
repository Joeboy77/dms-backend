from datetime import datetime, date, time
from typing import Optional, List
from pydantic import BaseModel, Field
from app.schemas.base import Obj, PyObjectId


class DefensePanelCreate(BaseModel):
    name: str
    lecturer_ids: List[PyObjectId]
    description: Optional[str] = None


class DefensePanelUpdate(BaseModel):
    name: Optional[str] = None
    lecturer_ids: Optional[List[PyObjectId]] = None
    description: Optional[str] = None


class DefensePanelPublic(Obj):
    name: str
    lecturer_ids: List[str]
    lecturers: List[dict] = []
    description: Optional[str] = None
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    
    class Config:
        populate_by_name = True
        from_attributes = True


class TimeSlot(BaseModel):
    student_id: Optional[PyObjectId] = None
    group_id: Optional[PyObjectId] = None
    start_time: str
    end_time: str


class DefenseScheduleCreate(BaseModel):
    panel_id: PyObjectId
    student_ids: Optional[List[PyObjectId]] = []
    group_ids: Optional[List[PyObjectId]] = []
    defense_date: date
    time_slots: List[TimeSlot]
    meeting_link: str
    academic_year_id: Optional[PyObjectId] = None
    notes: Optional[str] = None


class DefenseScheduleUpdate(BaseModel):
    panel_id: Optional[PyObjectId] = None
    student_ids: Optional[List[PyObjectId]] = None
    group_ids: Optional[List[PyObjectId]] = None
    defense_date: Optional[date] = None
    time_slots: Optional[List[TimeSlot]] = None
    meeting_link: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class TimeSlotPublic(BaseModel):
    student_id: Optional[str] = None
    group_id: Optional[str] = None
    start_time: str
    end_time: str
    student: Optional[dict] = None
    group: Optional[dict] = None


class DefenseSchedulePublic(Obj):
    panel_id: str
    panel: Optional[dict] = None
    student_ids: List[str] = []
    students: List[dict] = []
    group_ids: List[str] = []
    groups: List[dict] = []
    defense_date: date
    time_slots: List[TimeSlotPublic] = []
    meeting_link: str
    status: str
    academic_year_id: Optional[str] = None
    academic_year: Optional[dict] = None
    notes: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    
    class Config:
        populate_by_name = True
        from_attributes = True


class Page(BaseModel):
    items: List[DefenseSchedulePublic]
    next_cursor: Optional[str] = None


class PanelPage(BaseModel):
    items: List[DefensePanelPublic]
    next_cursor: Optional[str] = None

