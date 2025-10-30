from fastapi import APIRouter, Depends, Query, responses, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel
from bson import ObjectId

from app.core.database import get_db
from app.core.authentication.auth_middleware import RoleBasedAccessControl, TokenData, get_current_token
from app.schemas.complaints import ComplaintCreate, ComplaintPublic, ComplaintUpdate, Page
from app.controllers.complaints import ComplaintController

router = APIRouter(tags=["Complaints"])

require_supervisor = RoleBasedAccessControl(["projects_supervisor"])


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
    current_user: TokenData = Depends(get_current_token),
):
    """
    Add feedback to a complaint. Can be used by supervisors, coordinators, or admins.
    """
    # Get current user info
    supervisor = await db["lecturers"].find_one({"academicId": current_user.email})
    if not supervisor:
        raise HTTPException(status_code=404, detail="User not found")
    
    controller = ComplaintController(db)
    feedback_data = feedback.model_dump()
    feedback_data["provided_by"] = str(supervisor["_id"])
    return await controller.add_feedback(id, feedback_data)


@router.patch("/complaints/{id}/status", response_model=ComplaintPublic)
async def update_complaint_status(
    id: str,
    status_update: UpdateStatusRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    controller = ComplaintController(db)
    return await controller.update_status(id, status_update.status, status_update.notes)


# Removed: Supervisors cannot create complaints, they only view and provide feedback on student complaints


@router.get("/supervisor/complaints", response_model=Page)
async def get_supervisor_complaints(
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = None,
    status: str | None = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_supervisor)
):
    """
    Get all complaints from students assigned to the current supervisor.
    """
    supervisor = await db["lecturers"].find_one({"academicId": current_user.email})
    if not supervisor:
        raise HTTPException(status_code=404, detail="Supervisor not found")
    
    supervisor_id = supervisor["_id"]
    
    # Get all students assigned to this supervisor (from FYPs)
    fyps = await db["fyps"].find(
        {"supervisor": supervisor_id},
        {"student": 1}
    ).to_list(length=None)
    
    student_ids = [fyp["student"] for fyp in fyps if fyp.get("student")]
    
    # Also get students from groups supervised by this supervisor
    groups = await db["groups"].find(
        {"supervisor": supervisor_id, "status": "active"},
        {"members": 1}
    ).to_list(length=None)
    
    for group in groups:
        members = group.get("members", [])
        for member_id in members:
            if member_id not in student_ids:
                student_ids.append(member_id)
    
    # Convert student IDs to strings for querying complaints
    student_id_strings = [str(sid) for sid in student_ids]
    
    if not student_id_strings:
        # Return empty page if no students assigned
        return {
            "items": [],
            "next_cursor": None
        }
    
    # Find complaints created by these students
    query = {
        "createdBy.user_id": {"$in": student_id_strings},
        "deleted": {"$ne": True}
    }
    
    if status:
        query["status"] = status
    
    if cursor:
        query["_id"] = {"$gt": ObjectId(cursor)}
    
    complaints = await db["complaints"].find(query).sort("createdAt", -1).limit(limit).to_list(limit)
    
    # Format complaints
    from app.api.v1.routes.database import convert_objectid_to_str
    formatted_complaints = convert_objectid_to_str(complaints)
    
    next_cursor = None
    if len(complaints) == limit:
        next_cursor = str(complaints[-1]["_id"])
    
    return {
        "items": formatted_complaints,
        "next_cursor": next_cursor
    }