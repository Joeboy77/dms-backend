from fastapi import APIRouter, Depends, HTTPException, Query, responses
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List

from app.core.authentication.auth_middleware import get_current_token
from app.core.database import get_db
from app.schemas.student_interests import (
    StudentInterestCreate, 
    StudentInterestPublic, 
    StudentInterestUpdate, 
    Page,
    StudentInterestWithDetails,
    StudentPreferenceUpdate,
    StudentSupervisorMatches,
    InterestStatistics,
    BulkImportResult,
    StudentInterestAnalytics
)
from app.schemas.token import TokenData
from app.controllers.student_interests import StudentInterestController

router = APIRouter(tags=["Student Interests"])


@router.get("/student-interests", response_model=Page)
async def get_all_student_interests(
    limit: int = Query(10, alias="limit", ge=1, le=100),
    cursor: str | None = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Get all student interests with pagination"""
    controller = StudentInterestController(db)
    return await controller.get_all_student_interests(limit=limit, cursor=cursor)


@router.get("/student-interests/{id}", response_model=StudentInterestPublic)
async def get_student_interest(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    """Get specific student interest by ID"""
    controller = StudentInterestController(db)
    return await controller.get_student_interest_by_id(id)


@router.post("/student-interests", response_model=StudentInterestPublic)
async def create_student_interest(
    interest: StudentInterestCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    """Create new student interest record"""
    controller = StudentInterestController(db)
    interest_data = interest.model_dump()
    return await controller.create_student_interest(interest_data)


@router.patch("/student-interests/{id}", response_model=StudentInterestPublic)
async def update_student_interest(
    id: str,
    interest: StudentInterestUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    """Update student interest record"""
    controller = StudentInterestController(db)
    update_data = interest.model_dump()
    return await controller.update_student_interest(id, update_data)


@router.delete("/student-interests/{id}", status_code=204)
async def delete_student_interest(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    """Delete student interest record"""
    controller = StudentInterestController(db)
    await controller.delete_student_interest(id)
    return responses.Response(status_code=204)


@router.get("/student-interests/student/{student_id}", response_model=List[StudentInterestPublic])
async def get_student_interests_by_student(
    student_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    """Get all interests for a specific student"""
    controller = StudentInterestController(db)
    return await controller.get_student_interests_by_student(student_id)


@router.get("/student-interests/academic-year/{academic_year_id}", response_model=List[StudentInterestPublic])
async def get_student_interests_by_academic_year(
    academic_year_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    """Get all student interests for a specific academic year"""
    controller = StudentInterestController(db)
    return await controller.get_student_interests_by_academic_year(academic_year_id)


@router.get("/student-interests/project-area/{project_area_id}")
async def get_students_interested_in_project_area(
    project_area_id: str,
    academic_year_id: str = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    """Get all students interested in a specific project area"""
    controller = StudentInterestController(db)
    return await controller.get_students_interested_in_project_area(project_area_id, academic_year_id)


@router.patch("/student-interests/preference")
async def update_student_preference_ranking(
    student_id: str = Query(...),
    project_area_id: str = Query(...),
    rank: int = Query(..., ge=1, le=10),
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    """Update student's preference ranking for a project area"""
    controller = StudentInterestController(db)
    return await controller.update_student_preference_ranking(student_id, project_area_id, rank)


@router.get("/student-interests/matches/{student_id}", response_model=StudentSupervisorMatches)
async def get_student_supervisor_matches(
    student_id: str,
    academic_year_id: str = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    """Find potential supervisor matches based on student interests"""
    controller = StudentInterestController(db)
    matches = await controller.get_student_supervisor_matches(student_id, academic_year_id)
    
    # Get student details for response
    student = await db["students"].find_one({"_id": student_id})
    student_name = f"{student.get('surname', '')} {student.get('otherNames', '')}".strip() if student else ""
    
    return {
        "student_id": student_id,
        "student_name": student_name,
        "matches": matches,
        "total_matches": len(matches)
    }


@router.get("/student-interests/statistics", response_model=InterestStatistics)
async def get_interest_statistics(
    academic_year_id: str = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    """Get statistics about student interests"""
    controller = StudentInterestController(db)
    return await controller.get_interest_statistics(academic_year_id)


@router.post("/student-interests/bulk-import", response_model=BulkImportResult)
async def bulk_import_student_interests(
    interests_data: List[dict],
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    """Bulk import student interests from external data"""
    controller = StudentInterestController(db)
    return await controller.bulk_import_student_interests(interests_data)


@router.get("/student-interests/analytics", response_model=StudentInterestAnalytics)
async def get_student_interest_analytics(
    academic_year_id: str = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    """Get advanced analytics about student interests and matching patterns"""
    controller = StudentInterestController(db)
    
    # Get basic statistics
    stats = await controller.get_interest_statistics(academic_year_id)
    
    # Calculate analytics
    total_students = await db["students"].count_documents({"deleted": {"$ne": True}})
    students_with_interests = stats["unique_students"]
    students_without_interests = total_students - students_with_interests
    
    # Most and least popular areas
    popularity = stats["project_area_popularity"]
    project_area_titles = stats["project_area_titles"]
    
    most_popular = sorted(
        [(pa_id, count, project_area_titles.get(pa_id, "")) for pa_id, count in popularity.items()],
        key=lambda x: x[1],
        reverse=True
    )[:5]
    
    least_popular = sorted(
        [(pa_id, count, project_area_titles.get(pa_id, "")) for pa_id, count in popularity.items()],
        key=lambda x: x[1]
    )[:5]
    
    most_popular_areas = [
        {"project_area_id": pa_id, "title": title, "student_count": count}
        for pa_id, count, title in most_popular
    ]
    
    least_popular_areas = [
        {"project_area_id": pa_id, "title": title, "student_count": count}
        for pa_id, count, title in least_popular
    ]
    
    # Calculate average interests per student
    avg_interests = stats["total_interests"] / students_with_interests if students_with_interests > 0 else 0
    
    return {
        "most_popular_areas": most_popular_areas,
        "least_popular_areas": least_popular_areas,
        "average_interests_per_student": round(avg_interests, 2),
        "students_without_interests": students_without_interests,
        "interest_level_trends": stats["interest_level_distribution"],
        "preference_rank_trends": stats["preference_rank_distribution"]
    }
