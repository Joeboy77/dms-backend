from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_db
from app.core.authentication.auth_middleware import get_current_token, RoleBasedAccessControl, TokenData
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from bson import ObjectId

router = APIRouter(tags=["Supervisor Submissions"])

require_supervisor = RoleBasedAccessControl(["projects_supervisor", "projects_coordinator"])


class SubmissionStatusUpdate(BaseModel):
    status: str  # "approved", "changes_requested", "pending_review", "not_started"
    comments: Optional[str] = None


@router.get("/supervisor/submissions/dashboard")
async def get_submission_dashboard(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_supervisor)
):
    """
    Get submission dashboard with statistics for each deliverable.
    Shows total submissions, submitted, unsubmitted, and pending counts.
    """
    try:
        supervisor_academic_id = getattr(current_user, 'sub', 'LEC2025003')
        
        supervisor = await db["lecturers"].find_one({"academicId": supervisor_academic_id})
        if not supervisor:
            raise HTTPException(status_code=404, detail="Supervisor not found")
        
        supervisor_id = supervisor["_id"]
        
        deliverables = await db["deliverables"].find(
            {"supervisor_id": supervisor_id}
        ).sort("createdAt", -1).to_list(length=None)
        
        students_under_supervisor = await db["fyps"].find(
            {"supervisor": supervisor_id}
        ).to_list(length=None)
        
        student_ids = [fyp["student"] for fyp in students_under_supervisor]
        total_students = len(student_ids)
        
        supervisor_groups = await db["groups"].find(
            {"supervisor_id": supervisor_id, "status": "active"}
        ).to_list(length=None)
        
        students_in_groups = set()
        for group in supervisor_groups:
            students_in_groups.update(group.get("student_ids", []))
        
        individual_students = [sid for sid in student_ids if sid not in students_in_groups]
        total_individuals = len(individual_students)
        total_groups = len(supervisor_groups)
        
        total_entities = total_individuals + total_groups
        
        dashboard_data = []
        
        for deliverable in deliverables:
            deliverable_id = deliverable["_id"]
            
            submissions = await db["submissions"].find({
                "deliverable_id": deliverable_id
            }).to_list(length=None)
            
            submitted_count = 0
            pending_count = 0
            changes_requested_count = 0
            approved_count = 0
            not_started_count = 0
            
            for submission in submissions:
                status = submission.get("status", "not_started")
                if status == "approved":
                    approved_count += 1
                elif status == "changes_requested":
                    changes_requested_count += 1
                elif status == "pending_review":
                    pending_count += 1
                elif status in ["in_progress", "submitted"]:
                    submitted_count += 1
                else:
                    not_started_count += 1
            
            total_submitted = submitted_count + approved_count + changes_requested_count + pending_count
            unsubmitted_count = max(0, total_entities - total_submitted)
            
            if total_submitted == 0:
                not_started_count = total_entities
                unsubmitted_count = 0
            
            dashboard_data.append({
                "deliverable_id": str(deliverable["_id"]),
                "name": deliverable.get("name", ""),
                "start_date": deliverable.get("start_date", ""),
                "end_date": deliverable.get("end_date", ""),
                "total_submissions": total_entities,
                "submitted": submitted_count + approved_count,
                "unsubmitted": unsubmitted_count,
                "pending": pending_count + changes_requested_count,
                "approved": approved_count,
                "changes_requested": changes_requested_count,
                "not_started": not_started_count,
                "has_template": deliverable.get("template_file_url") is not None
            })
        
        return {
            "dashboard": dashboard_data,
            "summary": {
                "total_deliverables": len(deliverables),
                "total_students": total_students,
                "total_individuals": total_individuals,
                "total_groups": total_groups,
                "total_entities": total_entities
            },
            "supervisor_info": {
                "academic_id": supervisor_academic_id,
                "name": f"{supervisor.get('surname', '')} {supervisor.get('otherNames', '')}".strip()
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching submission dashboard: {str(e)}")


@router.get("/supervisor/submissions/deliverable/{deliverable_id}/students")
async def get_deliverable_students(
    deliverable_id: str,
    limit: int = Query(20, ge=1, le=100),
    search: str = Query(None),
    status_filter: str = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_supervisor)
):
    """
    Get all students and groups for a specific deliverable with their submission status.
    Shows the table view with student details and submission status.
    """
    try:
        supervisor_academic_id = getattr(current_user, 'sub', 'LEC2025003')
        
        supervisor = await db["lecturers"].find_one({"academicId": supervisor_academic_id})
        if not supervisor:
            raise HTTPException(status_code=404, detail="Supervisor not found")
        
        supervisor_id = supervisor["_id"]
        
        deliverable = await db["deliverables"].find_one({
            "_id": ObjectId(deliverable_id),
            "supervisor_id": supervisor_id
        })
        if not deliverable:
            raise HTTPException(status_code=404, detail="Deliverable not found")
        
        students_under_supervisor = await db["fyps"].find(
            {"supervisor": supervisor_id}
        ).to_list(length=None)
        
        student_ids = [fyp["student"] for fyp in students_under_supervisor]
        
        supervisor_groups = await db["groups"].find(
            {"supervisor_id": supervisor_id, "status": "active"}
        ).to_list(length=None)
        
        students_in_groups = set()
        for group in supervisor_groups:
            students_in_groups.update(group.get("student_ids", []))
        
        individual_student_ids = [sid for sid in student_ids if sid not in students_in_groups]
        
        students_data = []
        
        for student_id in individual_student_ids:
            student = await db["students"].find_one({"_id": student_id})
            if not student:
                continue
            
            submission = await db["submissions"].find_one({
                "deliverable_id": ObjectId(deliverable_id),
                "student_id": student_id
            })
            
            files = []
            if submission:
                files = await db["submission_files"].find({
                    "submission_id": submission["_id"]
                }).to_list(length=None)
            
            status = "not_started"
            submitted_file = None
            submission_date = None
            
            if submission:
                status = submission.get("status", "not_started")
                submission_date = submission.get("createdAt")
                if files:
                    latest_file = files[0]  # Most recent file
                    submitted_file = {
                        "file_name": latest_file.get("file_name", ""),
                        "file_url": latest_file.get("file_path", ""),
                        "file_type": latest_file.get("file_type", "")
                    }
            
            student_data = {
                "id": str(student["_id"]),
                "academic_id": student.get("academicId", ""),
                "name": f"{student.get('surname', '')} {student.get('otherNames', '')}".strip(),
                "email": student.get("email", ""),
                "program": student.get("program", ""),
                "type": "individual",
                "submission": {
                    "status": status,
                    "submitted_file": submitted_file,
                    "submission_date": submission_date,
                    "comments": submission.get("comments", "") if submission else ""
                }
            }
            
            # Apply search filter
            if search and search.lower() not in student_data["name"].lower() and search.lower() not in student_data["academic_id"].lower():
                continue
            
            # Apply status filter
            if status_filter and status != status_filter:
                continue
            
            students_data.append(student_data)
        
        # Process groups
        for group in supervisor_groups:
            # Get submission for this deliverable
            submission = await db["submissions"].find_one({
                "deliverable_id": ObjectId(deliverable_id),
                "group_id": group["_id"]
            })
            
            # Get submission files
            files = []
            if submission:
                files = await db["submission_files"].find({
                    "submission_id": submission["_id"]
                }).to_list(length=None)
            
            # Determine status
            status = "not_started"
            submitted_file = None
            submission_date = None
            
            if submission:
                status = submission.get("status", "not_started")
                submission_date = submission.get("createdAt")
                if files:
                    latest_file = files[0]  # Most recent file
                    submitted_file = {
                        "file_name": latest_file.get("file_name", ""),
                        "file_url": latest_file.get("file_path", ""),
                        "file_type": latest_file.get("file_type", "")
                    }
            
            group_data = {
                "id": str(group["_id"]),
                "academic_id": f"Group {group.get('name', '')}",
                "name": group.get("name", ""),
                "email": "",  # Groups don't have emails
                "program": group.get("project_topic", ""),
                "type": "group",
                "member_count": len(group.get("student_ids", [])),
                "submission": {
                    "status": status,
                    "submitted_file": submitted_file,
                    "submission_date": submission_date,
                    "comments": submission.get("comments", "") if submission else ""
                }
            }
            
            # Apply search filter
            if search and search.lower() not in group_data["name"].lower():
                continue
            
            # Apply status filter
            if status_filter and status != status_filter:
                continue
            
            students_data.append(group_data)
        
        # Sort by name
        students_data.sort(key=lambda x: x["name"])
        
        # Apply limit
        limited_data = students_data[:limit]
        
        return {
            "deliverable": {
                "id": str(deliverable["_id"]),
                "name": deliverable.get("name", ""),
                "start_date": deliverable.get("start_date", ""),
                "end_date": deliverable.get("end_date", ""),
                "instructions": deliverable.get("instructions", "")
            },
            "students": limited_data,
            "pagination": {
                "current_page": 1,
                "per_page": limit,
                "total": len(students_data),
                "showing": f"1-{len(limited_data)} of {len(students_data)}"
            },
            "filters": {
                "search": search,
                "status": status_filter
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching deliverable students: {str(e)}")


@router.get("/supervisor/submissions/student/{student_id}/deliverable/{deliverable_id}")
async def get_student_submission_details(
    student_id: str,
    deliverable_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_supervisor)
):
    """
    Get detailed submission information for a specific student and deliverable.
    Shows individual student profile with submission details.
    """
    try:
        supervisor_academic_id = getattr(current_user, 'sub', 'LEC2025003')
        
        supervisor = await db["lecturers"].find_one({"academicId": supervisor_academic_id})
        if not supervisor:
            raise HTTPException(status_code=404, detail="Supervisor not found")
        
        supervisor_id = supervisor["_id"]
        
        # Verify student is assigned to this supervisor
        fyp = await db["fyps"].find_one({
            "student": ObjectId(student_id),
            "supervisor": supervisor_id
        })
        if not fyp:
            raise HTTPException(status_code=404, detail="Student not found or not assigned to this supervisor")
        
        # Get student details
        student = await db["students"].find_one({"_id": ObjectId(student_id)})
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        
        # Get deliverable details
        deliverable = await db["deliverables"].find_one({
            "_id": ObjectId(deliverable_id),
            "supervisor_id": supervisor_id
        })
        if not deliverable:
            raise HTTPException(status_code=404, detail="Deliverable not found")
        
        # Get submission
        submission = await db["submissions"].find_one({
            "deliverable_id": ObjectId(deliverable_id),
            "student_id": ObjectId(student_id)
        })
        
        # Get submission files
        files = []
        if submission:
            files = await db["submission_files"].find({
                "submission_id": submission["_id"]
            }).sort("createdAt", -1).to_list(length=None)
        
        # Check if student is in a group
        group = await db["groups"].find_one({
            "student_ids": ObjectId(student_id),
            "supervisor_id": supervisor_id,
            "status": "active"
        })
        
        is_group_member = group is not None
        
        return {
            "student": {
                "id": str(student["_id"]),
                "academic_id": student.get("academicId", ""),
                "name": f"{student.get('surname', '')} {student.get('otherNames', '')}".strip(),
                "email": student.get("email", ""),
                "program": student.get("program", ""),
                "profile_image": student.get("profile_image", ""),
                "is_group_member": is_group_member,
                "group_id": str(group["_id"]) if group else None,
                "group_name": group.get("name", "") if group else None
            },
            "deliverable": {
                "id": str(deliverable["_id"]),
                "name": deliverable.get("name", ""),
                "start_date": deliverable.get("start_date", ""),
                "end_date": deliverable.get("end_date", ""),
                "instructions": deliverable.get("instructions", ""),
                "template_file": {
                    "file_name": deliverable.get("template_file_name", ""),
                    "file_url": deliverable.get("template_file_url", ""),
                    "file_type": deliverable.get("template_file_type", "")
                } if deliverable.get("template_file_url") else None
            },
            "submission": {
                "id": str(submission["_id"]) if submission else None,
                "status": submission.get("status", "not_started") if submission else "not_started",
                "comments": submission.get("comments", "") if submission else "",
                "submitted_at": submission.get("createdAt") if submission else None,
                "updated_at": submission.get("updatedAt") if submission else None,
                "files": [
                    {
                        "id": str(file["_id"]),
                        "file_name": file.get("file_name", ""),
                        "file_path": file.get("file_path", ""),
                        "file_type": file.get("file_type", ""),
                        "file_size": file.get("file_size", 0),
                        "uploaded_at": file.get("createdAt")
                    }
                    for file in files
                ]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching student submission details: {str(e)}")


@router.get("/supervisor/submissions/group/{group_id}/deliverable/{deliverable_id}")
async def get_group_submission_details(
    group_id: str,
    deliverable_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_supervisor)
):
    """
    Get detailed submission information for a specific group and deliverable.
    Shows group profile with all members and submission details.
    """
    try:
        supervisor_academic_id = getattr(current_user, 'sub', 'LEC2025003')
        
        supervisor = await db["lecturers"].find_one({"academicId": supervisor_academic_id})
        if not supervisor:
            raise HTTPException(status_code=404, detail="Supervisor not found")
        
        supervisor_id = supervisor["_id"]
        
        # Verify group belongs to this supervisor
        group = await db["groups"].find_one({
            "_id": ObjectId(group_id),
            "supervisor_id": supervisor_id,
            "status": "active"
        })
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")
        
        # Get deliverable details
        deliverable = await db["deliverables"].find_one({
            "_id": ObjectId(deliverable_id),
            "supervisor_id": supervisor_id
        })
        if not deliverable:
            raise HTTPException(status_code=404, detail="Deliverable not found")
        
        # Get all group members
        group_members = []
        for student_id in group.get("student_ids", []):
            student = await db["students"].find_one({"_id": student_id})
            if student:
                group_members.append({
                    "id": str(student["_id"]),
                    "academic_id": student.get("academicId", ""),
                    "name": f"{student.get('surname', '')} {student.get('otherNames', '')}".strip(),
                    "email": student.get("email", ""),
                    "program": student.get("program", ""),
                    "profile_image": student.get("profile_image", "")
                })
        
        # Get submission for this deliverable
        submission = await db["submissions"].find_one({
            "deliverable_id": ObjectId(deliverable_id),
            "group_id": ObjectId(group_id)
        })
        
        # Get submission files
        files = []
        if submission:
            files = await db["submission_files"].find({
                "submission_id": submission["_id"]
            }).sort("createdAt", -1).to_list(length=None)
        
        # Get all deliverables for this group to show submission status
        all_deliverables = await db["deliverables"].find({
            "supervisor_id": supervisor_id
        }).sort("createdAt", -1).to_list(length=None)
        
        deliverables_status = []
        for deliv in all_deliverables:
            deliv_submission = await db["submissions"].find_one({
                "deliverable_id": deliv["_id"],
                "group_id": ObjectId(group_id)
            })
            
            deliv_files = []
            if deliv_submission:
                deliv_files = await db["submission_files"].find({
                    "submission_id": deliv_submission["_id"]
                }).sort("createdAt", -1).to_list(length=None)
            
            status = "not_started"
            submitted_file = None
            if deliv_submission:
                status = deliv_submission.get("status", "not_started")
                if deliv_files:
                    latest_file = deliv_files[0]
                    submitted_file = {
                        "file_name": latest_file.get("file_name", ""),
                        "file_url": latest_file.get("file_path", ""),
                        "file_type": latest_file.get("file_type", "")
                    }
            
            deliverables_status.append({
                "deliverable_id": str(deliv["_id"]),
                "name": deliv.get("name", ""),
                "status": status,
                "submitted_file": submitted_file,
                "submitted_at": deliv_submission.get("createdAt") if deliv_submission else None
            })
        
        return {
            "group": {
                "id": str(group["_id"]),
                "name": group.get("name", ""),
                "project_topic": group.get("project_topic", ""),
                "created_at": group.get("created_at"),
                "member_count": len(group_members),
                "members": group_members
            },
            "deliverable": {
                "id": str(deliverable["_id"]),
                "name": deliverable.get("name", ""),
                "start_date": deliverable.get("start_date", ""),
                "end_date": deliverable.get("end_date", ""),
                "instructions": deliverable.get("instructions", ""),
                "template_file": {
                    "file_name": deliverable.get("template_file_name", ""),
                    "file_url": deliverable.get("template_file_url", ""),
                    "file_type": deliverable.get("template_file_type", "")
                } if deliverable.get("template_file_url") else None
            },
            "current_submission": {
                "id": str(submission["_id"]) if submission else None,
                "status": submission.get("status", "not_started") if submission else "not_started",
                "comments": submission.get("comments", "") if submission else "",
                "submitted_at": submission.get("createdAt") if submission else None,
                "updated_at": submission.get("updatedAt") if submission else None,
                "files": [
                    {
                        "id": str(file["_id"]),
                        "file_name": file.get("file_name", ""),
                        "file_path": file.get("file_path", ""),
                        "file_type": file.get("file_type", ""),
                        "file_size": file.get("file_size", 0),
                        "uploaded_at": file.get("createdAt")
                    }
                    for file in files
                ]
            },
            "all_deliverables_status": deliverables_status
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching group submission details: {str(e)}")


@router.patch("/supervisor/submissions/{submission_id}/status")
async def update_submission_status(
    submission_id: str,
    status_update: SubmissionStatusUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_supervisor)
):
    """
    Update the status of a submission (approve, request changes, etc.).
    """
    try:
        supervisor_academic_id = getattr(current_user, 'sub', 'LEC2025003')
        
        supervisor = await db["lecturers"].find_one({"academicId": supervisor_academic_id})
        if not supervisor:
            raise HTTPException(status_code=404, detail="Supervisor not found")
        
        supervisor_id = supervisor["_id"]
        
        # Get submission
        submission = await db["submissions"].find_one({"_id": ObjectId(submission_id)})
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")
        
        # Verify deliverable belongs to this supervisor
        deliverable = await db["deliverables"].find_one({
            "_id": submission["deliverable_id"],
            "supervisor_id": supervisor_id
        })
        if not deliverable:
            raise HTTPException(status_code=403, detail="Not authorized to update this submission")
        
        # Update submission
        update_data = {
            "status": status_update.status,
            "updatedAt": datetime.utcnow()
        }
        
        if status_update.comments:
            update_data["comments"] = status_update.comments
        
        await db["submissions"].update_one(
            {"_id": ObjectId(submission_id)},
            {"$set": update_data}
        )
        
        # Get updated submission
        updated_submission = await db["submissions"].find_one({"_id": ObjectId(submission_id)})
        
        return {
            "message": "Submission status updated successfully",
            "submission": {
                "id": str(updated_submission["_id"]),
                "status": updated_submission.get("status", ""),
                "comments": updated_submission.get("comments", ""),
                "updated_at": updated_submission.get("updatedAt")
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating submission status: {str(e)}")
