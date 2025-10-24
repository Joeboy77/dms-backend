from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_db
from app.core.authentication.auth_middleware import get_current_token, RoleBasedAccessControl, TokenData
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

router = APIRouter(tags=["Supervisor Students"])

require_supervisor = RoleBasedAccessControl(["projects_supervisor", "projects_coordinator"])


class CreateGroupRequest(BaseModel):
    student_ids: List[str]
    group_name: str
    project_topic: Optional[str] = None


class CreateDirectGroupRequest(BaseModel):
    group_name: str
    project_topic: Optional[str] = None


@router.get("/supervisor/students")
async def get_supervisor_students(
    view: str = Query("all", regex="^(all|individual|groups)$"),
    limit: int = Query(20, ge=1, le=100),
    search: str = Query(None),
    project_status: str = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_supervisor)
):
    """
    Get students and groups for the current supervisor.
    Supports three views: 'all', 'individual', 'groups'
    - 'all': Shows both individual students and groups
    - 'individual': Shows only individual students (not in groups)
    - 'groups': Shows only existing groups
    Includes images, IDs, names, programs, and project status.
    Supports search and filtering by project status.
    """
    try:
        from bson import ObjectId
        from datetime import datetime
        
        supervisor_academic_id = current_user.email
        if not supervisor_academic_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing supervisor ID")
        
        supervisor = await db["lecturers"].find_one({"academicId": supervisor_academic_id})
        if not supervisor:
            raise HTTPException(status_code=404, detail="Supervisor not found")
        
        supervisor_id = supervisor["_id"]
        
        students_under_supervisor = await db["fyps"].find(
            {"supervisor": supervisor_id},
            {"student": 1}
        ).to_list(length=None)
        
        student_ids = [fyp["student"] for fyp in students_under_supervisor]
        
        supervisor_groups = await db["groups"].find(
            {"supervisor": supervisor_id, "status": "active"}
        ).to_list(length=None)
        
        result_data = []
        individual_count = 0
        groups_count = len(supervisor_groups)
        
        if view == "groups" or view == "all":
            for group in supervisor_groups:
                group_member_ids = group.get("members", [])
                group_members = []
                member_images = []
                
                for member_id in group_member_ids:
                    member = await db["students"].find_one({"_id": member_id})
                    if member:
                        group_members.append({
                            "id": str(member["_id"]),
                            "name": f"{member.get('surname', '')} {member.get('otherNames', '')}".strip(),
                            "academic_id": member.get("academicId", ""),
                            "image": member.get("image", "")
                        })
                        if member.get("image"):
                            member_images.append(member["image"])
                
                group_project_status = await get_group_project_status(group_member_ids, db)
                
                group_data = {
                    "id": str(group["_id"]),
                    "type": "group",
                    "name": group.get("name", ""),
                    "project_topic": group.get("project_topic", ""),
                    "member_count": len(group_members),
                    "member_images": member_images,  # For overlapping display
                    "members": group_members,
                    "project_status": group_project_status,
                    "reports_count": await get_group_reports_count(str(group["_id"]), db),
                    "created_at": group.get("created_at")
                }
                result_data.append(group_data)
        
        if view == "individual" or view == "all":
            for student_id in student_ids:
                student = await db["students"].find_one({"_id": ObjectId(student_id)})
                if student:
                    is_in_group = await db["groups"].find_one({
                        "members": ObjectId(student_id)
                    })
                    
                    if is_in_group:
                        continue
                    

                    program_field = student.get("program", "")
                    if isinstance(program_field, str) and len(program_field) == 24:
                        program = await db["programs"].find_one({"_id": ObjectId(program_field)})
                        program_name = program.get("name", "Unknown Program") if program else "Unknown Program"
                    else:

                        program_name = program_field if program_field else "Unknown Program"
                    
                    project_status_value = await get_student_project_status(student_id, db)
                    
                    student_data = {
                        "id": str(student["_id"]),
                        "type": "individual",
                        "academic_id": student.get("academicId", ""),
                        "name": f"{student.get('surname', '')} {student.get('otherNames', '')}".strip(),
                        "program": program_name,
                        "project_status": project_status_value,
                        "image": student.get("image", ""),
                        "email": student.get("email", ""),
                        "reports_count": await get_student_reports_count(student_id, db)
                    }
                    result_data.append(student_data)
                    individual_count += 1
        
        if search:
            result_data = [
                item for item in result_data
                if search.lower() in item.get("name", "").lower() or
                   search.lower() in item.get("academic_id", "").lower() or
                   (item.get("type") == "individual" and search.lower() in item.get("program", "").lower())
            ]
        
        if project_status:
            result_data = [
                item for item in result_data
                if item.get("project_status", "").lower() == project_status.lower()
            ]
        
        total_items = len(result_data)
        start_index = 0
        end_index = min(start_index + limit, total_items)
        paginated_data = result_data[start_index:end_index]
        
        return {
            "data": paginated_data,
            "view": view,
            "counts": {
                "total": total_items,
                "individual_students": individual_count,
                "groups": groups_count,
                "all": individual_count + groups_count
            },
            "supervisor_info": {
                "academic_id": supervisor_academic_id,
                "name": f"{supervisor.get('surname', '')} {supervisor.get('otherNames', '')}".strip(),
                "students_count": len(student_ids)
            },
            "pagination": {
                "current_page": 1,
                "per_page": limit,
                "total": total_items,
                "showing": f"1-{len(paginated_data)} of {total_items}"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching supervisor students: {str(e)}")


@router.post("/supervisor/students/create-group")
async def create_group_from_students(
    group_request: CreateGroupRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_supervisor)
):
    """
    Create a group from selected students for the current supervisor.
    """
    try:
        from bson import ObjectId
        from datetime import datetime
        
        supervisor_academic_id = current_user.email
        if not supervisor_academic_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing supervisor ID")
        
        supervisor = await db["lecturers"].find_one({"academicId": supervisor_academic_id})
        if not supervisor:
            raise HTTPException(status_code=404, detail="Supervisor not found")
        
        supervisor_id = supervisor["_id"]
        
        for student_id in group_request.student_ids:
            fyp = await db["fyps"].find_one({
                "student": ObjectId(student_id),
                "supervisor": supervisor_id
            })
            if not fyp:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Student {student_id} is not assigned to this supervisor"
                )
        
        group_data = {
            "name": group_request.group_name,
            "project_topic": group_request.project_topic or "",
            "supervisor": supervisor_id,
            "members": [ObjectId(sid) for sid in group_request.student_ids],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "status": "active"
        }
        
        result = await db["groups"].insert_one(group_data)
        created_group = await db["groups"].find_one({"_id": result.inserted_id})
        
        return {
            "message": "Group created successfully",
            "group": {
                "id": str(created_group["_id"]),
                "name": created_group["name"],
                "project_topic": created_group["project_topic"],
                "member_count": len(group_request.student_ids),
                "created_at": created_group["created_at"]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating group: {str(e)}")


@router.post("/supervisor/groups")
async def create_direct_group(
    group_request: CreateDirectGroupRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_supervisor)
):
    """
    Create a new group directly (without selecting students first).
    Students can be added to the group later.
    """
    try:
        from bson import ObjectId
        from datetime import datetime
        
        supervisor_academic_id = current_user.email
        if not supervisor_academic_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing supervisor ID")
        
        supervisor = await db["lecturers"].find_one({"academicId": supervisor_academic_id})
        if not supervisor:
            raise HTTPException(status_code=404, detail="Supervisor not found")
        
        supervisor_id = supervisor["_id"]
        
        group_data = {
            "name": group_request.group_name,
            "project_topic": group_request.project_topic or "",
            "supervisor": supervisor_id,
            "members": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "status": "active"
        }
        
        result = await db["groups"].insert_one(group_data)
        created_group = await db["groups"].find_one({"_id": result.inserted_id})
        
        return {
            "message": "Group created successfully",
            "group": {
                "id": str(created_group["_id"]),
                "name": created_group["name"],
                "project_topic": created_group["project_topic"],
                "student_count": 0,
                "created_at": created_group["created_at"]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating group: {str(e)}")


async def get_group_project_status(group_member_ids: list, db: AsyncIOMotorDatabase) -> str:
    """
    Determine group's project status based on group submissions and deliverables.
    Returns: "Not Started", "In Progress", "Changes Requested", or "Completed"
    """
    try:
        if not group_member_ids:
            return "Not Started"
        
        # Find the group that contains these members
        group = await db["groups"].find_one({
            "members": {"$in": group_member_ids},
            "status": "active"
        })
        
        if not group:
            return "Not Started"
        
        group_id = group["_id"]
        
        # Get group submissions (not individual student submissions)
        group_submissions = await db["submissions"].find({
            "group_id": group_id
        }).to_list(length=None)
        
        # Get deliverables for the supervisor of this group
        supervisor_id = group.get("supervisor")
        if not supervisor_id:
            return "Not Started"
            
        total_deliverables = await db["deliverables"].count_documents({
            "supervisor_id": supervisor_id
        })
        
        if not group_submissions and total_deliverables == 0:
            return "Not Started"
        elif not group_submissions:
            return "Not Started"
        
        # Check submission statuses
        approved_count = 0
        changes_requested_count = 0
        in_progress_count = 0
        
        for submission in group_submissions:
            status = submission.get("status", "not_started")
            if status == "approved":
                approved_count += 1
            elif status == "changes_requested":
                changes_requested_count += 1
            elif status in ["in_progress", "pending_review"]:
                in_progress_count += 1
        
        # Determine overall status
        if changes_requested_count > 0:
            return "Changes Requested"
        elif approved_count == total_deliverables and total_deliverables > 0:
            return "Completed"
        elif in_progress_count > 0 or len(group_submissions) > 0:
            return "In Progress"
        else:
            return "Not Started"
            
    except Exception:
        return "Not Started"


async def get_group_reports_count(group_id: str, db: AsyncIOMotorDatabase) -> int:
    """
    Get the count of reports/submissions for a group.
    """
    try:
        from bson import ObjectId
        
        group = await db["groups"].find_one({"_id": ObjectId(group_id)})
        if not group:
            return 0
        
        member_ids = group.get("members", [])
        if not member_ids:
            return 0
        
        reports_count = await db["submissions"].count_documents({
            "student_id": {"$in": member_ids}
        })
        
        return reports_count
        
    except Exception:
        return 0


async def get_student_project_status(student_id: str, db: AsyncIOMotorDatabase) -> str:
    """
    Determine student's project status based on submissions and deliverables.
    """
    try:
        from bson import ObjectId
        
        submissions_count = await db["submissions"].count_documents({
            "student_id": ObjectId(student_id)
        })
        
        deliverables_count = await db["deliverables"].count_documents({
            "members": ObjectId(student_id)
        })
        
        if submissions_count == 0 and deliverables_count == 0:
            return "Not Started"
        elif submissions_count > 0:
            completed_submissions = await db["submissions"].count_documents({
                "student_id": ObjectId(student_id),
                "status": "completed"
            })
            
            if completed_submissions >= deliverables_count and deliverables_count > 0:
                return "Completed"
            else:
                return "In Progress"
        else:
            return "In Progress"
            
    except Exception:
        return "Not Started"


async def get_student_group_info(student_id: str, db: AsyncIOMotorDatabase) -> dict:
    """
    Get group information for a student.
    """
    try:
        from bson import ObjectId
        
        group = await db["groups"].find_one({
            "members": ObjectId(student_id),
            "status": "active"
        })
        
        if group:
            other_students = []
            for other_student_id in group["members"]:
                if str(other_student_id) != student_id:
                    other_student = await db["students"].find_one({"_id": other_student_id})
                    if other_student:
                        other_students.append({
                            "id": str(other_student["_id"]),
                            "name": f"{other_student.get('surname', '')} {other_student.get('otherNames', '')}".strip(),
                            "image": other_student.get("image", "")
                        })
            
            return {
                "group_id": str(group["_id"]),
                "group_name": group["name"],
                "is_grouped": True,
                "group_members": other_students
            }
        else:
            return {
                "group_id": None,
                "group_name": None,
                "is_grouped": False,
                "group_members": []
            }
            
    except Exception:
        return {
            "group_id": None,
            "group_name": None,
            "is_grouped": False,
            "group_members": []
        }


async def get_student_reports_count(student_id: str, db: AsyncIOMotorDatabase) -> int:
    """
    Get the count of reports/submissions for a student.
    """
    try:
        from bson import ObjectId
        
        reports_count = await db["submissions"].count_documents({
            "student_id": ObjectId(student_id)
        })
        
        return reports_count
        
    except Exception:
        return 0


@router.get("/supervisor/groups/{group_id}/details")
async def get_group_details(
    group_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_supervisor)
):
    """
    Get detailed information about a group including all members and submissions.
    """
    try:
        supervisor_academic_id = current_user.email
        if not supervisor_academic_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing supervisor ID")
        
        supervisor = await db["lecturers"].find_one({"academicId": supervisor_academic_id})
        if not supervisor:
            raise HTTPException(status_code=404, detail="Supervisor not found")
        
        supervisor_id = supervisor["_id"]
        
        # Get group details
        group = await db["groups"].find_one({
            "_id": ObjectId(group_id),
            "supervisor": supervisor_id,
            "status": "active"
        })
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")
        
        # Get all group members with their details
        group_members = []
        for student_id in group.get("members", []):  # Changed from "student_ids" to "members"
            student = await db["students"].find_one({"_id": student_id})
            if student:
                # Check if program is an ObjectId or a string
                program_field = student.get("program", "")
                if isinstance(program_field, str) and len(program_field) == 24:
                    # It's an ObjectId, look it up
                    program = await db["programs"].find_one({"_id": ObjectId(program_field)})
                    program_name = program.get("name", "Unknown Program") if program else "Unknown Program"
                else:
                    # It's already a program name
                    program_name = program_field if program_field else "Unknown Program"
                
                group_members.append({
                    "id": str(student["_id"]),
                    "academic_id": student.get("academicId", ""),
                    "name": student.get("name", ""),  # Use direct name field
                    "program": program_name,
                    "image": student.get("image", ""),
                    "email": student.get("email", "")
                })
        
        # Get all deliverables for this supervisor
        deliverables = await db["deliverables"].find({
            "supervisor_id": supervisor_id
        }).sort("created_at", 1).to_list(length=None)
        
        # Get submissions for each deliverable
        submissions_data = []
        for deliverable in deliverables:
            deliverable_id = deliverable["_id"]
            
            # Get submission for this group and deliverable
            submission = await db["submissions"].find_one({
                "group_id": ObjectId(group_id),
                "deliverable_id": deliverable_id
            })
            
            # Get files for this submission
            files = []
            if submission:
                files = await db["submission_files"].find({
                    "submission_id": submission["_id"]
                }).to_list(length=None)
            
            submissions_data.append({
                "deliverable_id": str(deliverable_id),
                "deliverable_name": deliverable.get("name", ""),
                "status": submission.get("status", "not_started") if submission else "not_started",
                "submitted_at": submission.get("createdAt") if submission else None,
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
            "submissions": submissions_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching group details: {str(e)}")


@router.get("/supervisor/students/{student_id}/profile")
async def get_student_profile(
    student_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_supervisor)
):
    """
    Get detailed information about an individual student including their submissions.
    """
    try:
        supervisor_academic_id = current_user.email
        if not supervisor_academic_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing supervisor ID")
        
        supervisor = await db["lecturers"].find_one({"academicId": supervisor_academic_id})
        if not supervisor:
            raise HTTPException(status_code=404, detail="Supervisor not found")
        
        supervisor_id = supervisor["_id"]
        
        # Check if student is assigned to this supervisor
        fyp_assignment = await db["fyps"].find_one({
            "student": ObjectId(student_id),
            "supervisor": supervisor_id
        })
        
        if not fyp_assignment:
            raise HTTPException(status_code=404, detail="Student not found or not assigned to supervisor")
        
        # Get student details
        student = await db["students"].find_one({"_id": ObjectId(student_id)})
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        
        # Get student's project topic from FYP assignment
        project_topic = fyp_assignment.get("project_topic", "")
        
        # Get submissions for the student - only show deliverables created by this supervisor
        submissions = []
        deliverables = await db["deliverables"].find({
            "supervisor_id": supervisor_id
        }).to_list(length=None)
        
        for deliverable in deliverables:
            submission = await db["submissions"].find_one({
                "student_id": ObjectId(student_id),
                "deliverable_id": deliverable["_id"]
            })
            
            files = []
            if submission:
                file_ids = submission.get("files", [])
                for file_id in file_ids:
                    file_doc = await db["files"].find_one({"_id": ObjectId(file_id)})
                    if file_doc:
                        files.append({
                            "id": str(file_doc["_id"]),
                            "file_name": file_doc.get("filename", ""),
                            "file_path": file_doc.get("url", ""),
                            "file_type": file_doc.get("content_type", ""),
                            "file_size": file_doc.get("size", 0),
                            "uploaded_at": file_doc.get("created_at", "").isoformat() if file_doc.get("created_at") else None
                        })
            
            submissions.append({
                "deliverable_id": str(deliverable["_id"]),
                "deliverable_name": deliverable.get("name", ""),
                "status": submission.get("status", "not_started") if submission else "not_started",
                "submitted_at": submission.get("submitted_at", "").isoformat() if submission and submission.get("submitted_at") else None,
                "files": files
            })
        
        return {
            "id": str(student["_id"]),
            "academic_id": student.get("academicId", ""),
            "name": student.get("name", ""),
            "program": student.get("program", ""),
            "image": student.get("image", ""),
            "email": student.get("email", ""),
            "project_topic": project_topic,
            "submissions": submissions
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching student profile: {str(e)}")


@router.post("/supervisor/groups/{group_id}/add-students")
async def add_students_to_group(
    group_id: str,
    request: dict,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_supervisor)
):
    """
    Add students to an existing group.
    """
    try:
        supervisor_academic_id = current_user.email
        if not supervisor_academic_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing supervisor ID")
        
        supervisor = await db["lecturers"].find_one({"academicId": supervisor_academic_id})
        if not supervisor:
            raise HTTPException(status_code=404, detail="Supervisor not found")
        
        supervisor_id = supervisor["_id"]
        
        # Get the group
        group = await db["groups"].find_one({
            "_id": ObjectId(group_id),
            "supervisor": supervisor_id
        })
        
        if not group:
            raise HTTPException(status_code=404, detail="Group not found or not assigned to supervisor")
        
        student_ids = request.get("student_ids", [])
        if not student_ids:
            raise HTTPException(status_code=400, detail="No student IDs provided")
        
        # Validate that all students are assigned to this supervisor and not already in groups
        for student_id in student_ids:
            # Check if student is assigned to this supervisor
            fyp_assignment = await db["fyps"].find_one({
                "student": ObjectId(student_id),
                "supervisor": supervisor_id
            })
            
            if not fyp_assignment:
                raise HTTPException(status_code=400, detail=f"Student {student_id} is not assigned to this supervisor")
            
            # Check if student is already in a group
            existing_group = await db["groups"].find_one({
                "members": ObjectId(student_id)
            })
            
            if existing_group:
                raise HTTPException(status_code=400, detail=f"Student {student_id} is already in a group")
        
        # Add students to the group
        await db["groups"].update_one(
            {"_id": ObjectId(group_id)},
            {
                "$addToSet": {
                    "members": {"$each": [ObjectId(sid) for sid in student_ids]}
                }
            }
        )
        
        # Update member_count
        updated_group = await db["groups"].find_one({"_id": ObjectId(group_id)})
        member_count = len(updated_group.get("members", []))
        
        await db["groups"].update_one(
            {"_id": ObjectId(group_id)},
            {"$set": {"member_count": member_count}}
        )
        
        return {"message": f"Successfully added {len(student_ids)} student(s) to the group"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding students to group: {str(e)}")
