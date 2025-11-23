from fastapi import APIRouter, Depends, HTTPException, Query, responses
from typing import Optional, List, Dict
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.authentication.auth_middleware import get_current_token
from app.core.database import get_db
from app.schemas.deliverables import DeliverableCreate, DeliverablePublic, DeliverableUpdate, Page
from app.schemas.token import TokenData
from app.controllers.deliverables import DeliverableController

router = APIRouter(tags=["Deliverables"])


@router.get("/deliverables", response_model=Page)
async def get_all_deliverables(
    limit: int = Query(10, alias="limit", ge=1, le=100),
    cursor: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = DeliverableController(db)
    return await controller.get_all_deliverables(limit=limit, cursor=cursor)


@router.get("/deliverables/{id}", response_model=DeliverablePublic)
async def get_deliverable(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = DeliverableController(db)
    return await controller.get_deliverable_by_id(id)


@router.post("/deliverables/{supervisor_id}", response_model=DeliverablePublic)
async def create_deliverable(
    supervisor_id: str,
    deliverable: DeliverableCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    """
    Create a deliverable for a supervisor.
    
    The supervisor_id can be either:
    - A supervisor ObjectId
    - A lecturer's academicId (will be resolved to supervisor)
    
    If group_ids are not provided, they will be auto-populated from all groups
    associated with the supervisor's FYPs.
    """
    controller = DeliverableController(db)
    deliverable_data = deliverable.model_dump()
    return await controller.create_deliverable(supervisor_id, deliverable_data)


@router.patch("/deliverables/{id}", response_model=DeliverablePublic)
async def update_deliverable(
    id: str,
    deliverable: DeliverableUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = DeliverableController(db)
    update_data = deliverable.model_dump()
    return await controller.update_deliverable(id, update_data)


@router.delete("/deliverables/{id}", status_code=204)
async def delete_deliverable(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = DeliverableController(db)
    await controller.delete_deliverable(id)
    return responses.Response(status_code=204)


@router.get("/deliverables/supervisor/{supervisor_id}", response_model=List[DeliverablePublic])
async def get_deliverables_by_supervisor(
    supervisor_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = DeliverableController(db)
    return await controller.get_deliverables_by_supervisor(supervisor_id)


@router.get("/deliverables/active", response_model=List[DeliverablePublic])
async def get_active_deliverables(
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = DeliverableController(db)
    return await controller.get_active_deliverables()


@router.get("/deliverables/upcoming/{limit}", response_model=List[DeliverablePublic])
async def get_upcoming_deliverables(
    limit: int = 10,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = DeliverableController(db)
    return await controller.get_upcoming_deliverables(limit)


@router.get("/deliverables/student/{student_id}")
async def get_deliverables_for_student(
    student_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    """Get all deliverables for a specific student by their academic ID"""
    controller = DeliverableController(db)
    return await controller.get_deliverables_for_student(student_id)