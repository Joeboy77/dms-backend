from fastapi import APIRouter, Depends, HTTPException, Query, responses, UploadFile
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.authentication.auth_middleware import get_current_token
from app.core.database import get_db
from app.schemas.submissions import SubmissionCreate, SubmissionPublic, SubmissionUpdate, Page, SubmissionDetailsResponse
from app.schemas.token import TokenData
from app.controllers.submissions import SubmissionController

router = APIRouter(tags=["Submissions"])


@router.get("/submissions", response_model=Page)
async def get_all_submissions(
    limit: int = Query(10, alias="limit", ge=1, le=100),
    cursor: str | None = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = SubmissionController(db)
    return await controller.get_all_submissions(limit=limit, cursor=cursor)


@router.get("/submissions/{id}", response_model=SubmissionPublic)
async def get_submission(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = SubmissionController(db)
    return await controller.get_submission_by_id(id)


@router.post("/submissions", response_model=SubmissionPublic)
async def create_submission(
    submission: SubmissionCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = SubmissionController(db)
    submission_data = submission.model_dump()
    return await controller.create_submission(submission_data)


@router.post("/submissions/review/{submission_id}", response_model=SubmissionPublic)
async def review_submission(
    submission_id: str,
    approved: bool,
    feedback: str | None = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = SubmissionController(db)
    return await controller.review_submission(submission_id, approved, feedback)


@router.post("/submissions/resubmit/{submission_id}", response_model=SubmissionPublic)
async def resubmit_submission(
    submission_id: str,
    file: UploadFile,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = SubmissionController(db)
    return await controller.resubmit_submission(submission_id, file)


@router.patch("/submissions/{id}", response_model=SubmissionPublic)
async def update_submission(
    id: str,
    submission: SubmissionUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = SubmissionController(db)
    update_data = submission.model_dump()
    return await controller.update_submission(id, update_data)


@router.delete("/submissions/{id}", status_code=204)
async def delete_submission(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = SubmissionController(db)
    await controller.delete_submission(id)
    return responses.Response(status_code=204)


@router.get("/submissions/deliverable/{deliverable_id}", response_model=list[SubmissionPublic])
async def get_submissions_by_deliverable(
    deliverable_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = SubmissionController(db)
    return await controller.get_submissions_by_deliverable(deliverable_id)


@router.get("/submissions/student/{student_id}", response_model=list[SubmissionPublic])
async def get_submissions_by_student(
    student_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = SubmissionController(db)
    return await controller.get_submissions_by_student(student_id)




@router.get("/deliverables/{deliverable_id}/students/{student_id}/status")
async def check_student_submission_status(
    deliverable_id: str,
    student_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = SubmissionController(db)
    return await controller.check_student_submission_status(deliverable_id, student_id)


@router.get("/groups/{group_id}/submission-details", response_model=SubmissionDetailsResponse)
async def get_submission_details_by_group(
    group_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = SubmissionController(db)
    return await controller.get_submission_details_with_group_and_files_by_group(group_id)


@router.get("/deliverables/{deliverable_id}/groups")
async def get_groups_who_submitted_to_deliverable(
    deliverable_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: TokenData = Depends(get_current_token),
):
    controller = SubmissionController(db)
    return await controller.get_groups_who_submitted_to_deliverable(deliverable_id)