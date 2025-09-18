from fastapi import APIRouter, Depends, Query, responses
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from app.core.database import get_db
from app.schemas.complaints import ComplaintCreate, ComplaintPublic, ComplaintUpdate, Page
from app.controllers.complaints import ComplaintController

router = APIRouter(tags=["Complaints"])


class AssignComplaintRequest(BaseModel):
    assigned_to: list[str]


class AddFeedbackRequest(BaseModel):
    feedback_type: str = "GENERAL"
    message: str
    provided_by: str
    rating: int | None = None


class UpdateStatusRequest(BaseModel):
    status: str
    notes: str | None = None


@router.get("/complaints", response_model=Page)
async def get_all_complaints(
    limit: int = Query(10, alias="limit", ge=1, le=100),
    cursor: str | None = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = ComplaintController(db)
    return await controller.get_all_complaints(limit=limit, cursor=cursor)


@router.get("/complaints/{id}", response_model=ComplaintPublic)
async def get_complaint(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = ComplaintController(db)
    return await controller.get_complaint_by_id(id)


@router.get("/complaints/reference/{reference}", response_model=ComplaintPublic)
async def get_complaint_by_reference(
    reference: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = ComplaintController(db)
    return await controller.get_complaints_by_reference(reference)


@router.get("/complaints/status/{status}", response_model=list[ComplaintPublic])
async def get_complaints_by_status(
    status: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = ComplaintController(db)
    return await controller.get_complaints_by_status(status)


@router.get("/complaints/category/{category_id}", response_model=list[ComplaintPublic])
async def get_complaints_by_category(
    category_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = ComplaintController(db)
    return await controller.get_complaints_by_category(category_id)


@router.post("/complaints", response_model=ComplaintPublic)
async def create_complaint(
    complaint: ComplaintCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = ComplaintController(db)
    complaint_data = complaint.model_dump()
    return await controller.create_complaint(complaint_data)


@router.patch("/complaints/{id}", response_model=ComplaintPublic)
async def update_complaint(
    id: str,
    complaint: ComplaintUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = ComplaintController(db)
    update_data = complaint.model_dump()
    return await controller.update_complaint(id, update_data)


@router.delete("/complaints/{id}", status_code=204)
async def delete_complaint(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = ComplaintController(db)
    await controller.delete_complaint(id)
    return responses.Response(status_code=204)


@router.patch("/complaints/{id}/assign", response_model=ComplaintPublic)
async def assign_complaint(
    id: str,
    assignment: AssignComplaintRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = ComplaintController(db)
    return await controller.assign_complaint(id, assignment.assigned_to)


@router.post("/complaints/{id}/feedback", response_model=ComplaintPublic)
async def add_feedback(
    id: str,
    feedback: AddFeedbackRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = ComplaintController(db)
    feedback_data = feedback.model_dump()
    return await controller.add_feedback(id, feedback_data)


@router.patch("/complaints/{id}/status", response_model=ComplaintPublic)
async def update_complaint_status(
    id: str,
    status_update: UpdateStatusRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = ComplaintController(db)
    return await controller.update_status(id, status_update.status, status_update.notes)