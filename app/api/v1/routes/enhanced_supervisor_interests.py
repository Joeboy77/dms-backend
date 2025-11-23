from fastapi import APIRouter, Depends, Query
from typing import Optional, List, Dict
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.controllers.enhanced_supervisor_interests import EnhancedSupervisorInterestController
from app.schemas.enhanced_supervisor_interests import (
    SupervisorInterestProfile,
    AddSupervisorInterestRequest,
    RemoveSupervisorInterestRequest,
    SupervisorMatchingStudentsResponse,
    SupervisorInterestAnalytics,
    OptimalMatchesResponse,
)

router = APIRouter(tags=["Enhanced Supervisor Interests"]) 


@router.get("/enhanced/supervisors/{supervisor_id}/interest-profile", response_model=SupervisorInterestProfile)
async def get_supervisor_interest_profile(
    supervisor_id: str,
    academic_year_id: Optional[str] = Query(None, alias="academic_year_id"),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = EnhancedSupervisorInterestController(db)
    return await controller.get_supervisor_interest_profile(supervisor_id, academic_year_id)


@router.post("/enhanced/supervisors/{supervisor_id}/interests")
async def add_supervisor_interest(
    supervisor_id: str,
    payload: AddSupervisorInterestRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = EnhancedSupervisorInterestController(db)
    return await controller.add_supervisor_interest(
        supervisor_id=supervisor_id,
        project_area_id=payload.project_area_id,
        academic_year_id=payload.academic_year_id,
    )


@router.delete("/enhanced/supervisors/{supervisor_id}/interests")
async def remove_supervisor_interest(
    supervisor_id: str,
    payload: RemoveSupervisorInterestRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = EnhancedSupervisorInterestController(db)
    return await controller.remove_supervisor_interest(
        supervisor_id=supervisor_id,
        project_area_id=payload.project_area_id,
        academic_year_id=payload.academic_year_id,
    )


@router.get("/enhanced/supervisors/{supervisor_id}/matching-students", response_model=SupervisorMatchingStudentsResponse)
async def get_supervisor_matching_students(
    supervisor_id: str,
    academic_year_id: Optional[str] = Query(None, alias="academic_year_id"),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = EnhancedSupervisorInterestController(db)
    items = await controller.get_supervisor_matching_students(supervisor_id, academic_year_id)
    return {"items": items}


@router.get("/enhanced/supervisors/interests/analytics", response_model=SupervisorInterestAnalytics)
async def get_supervisor_interest_analytics(
    academic_year_id: Optional[str] = Query(None, alias="academic_year_id"),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = EnhancedSupervisorInterestController(db)
    return await controller.get_supervisor_interest_analytics(academic_year_id)


@router.get("/enhanced/supervisors/optimal-matches", response_model=OptimalMatchesResponse)
async def get_optimal_supervisor_student_matches(
    academic_year_id: Optional[str] = Query(None, alias="academic_year_id"),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = EnhancedSupervisorInterestController(db)
    items = await controller.get_optimal_supervisor_student_matches(academic_year_id)
    return {"items": items}
