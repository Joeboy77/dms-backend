from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_db
from app.core.authentication.auth_middleware import get_current_token, RoleBasedAccessControl, TokenData
from pydantic import BaseModel
from typing import List, Optional

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
            {"supervisor_id": supervisor_id, "status": "active"}
        ).to_list(length=None)
        
        result_data = []
        individual_count = 0
        groups_count = len(supervisor_groups)
        
        if view == "groups" or view == "all":
            for group in supervisor_groups:
                group_member_ids = group.get("student_ids", [])
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
                        "student_ids": ObjectId(student_id),
                        "status": "active"
                    })
                    
                    if is_in_group:
                        continue
                    
                    program = await db["programs"].find_one({"_id": student.get("program")})
                    program_name = program.get("name", "Unknown Program") if program else "Unknown Program"
                    
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
            "student_ids": [ObjectId(sid) for sid in group_request.student_ids],
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
                "student_count": len(group_request.student_ids),
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
            "student_ids": [],
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
    Determine group's project status based on member submissions and deliverables.
    Returns: "Not Started", "In Progress", "Changes Requested", or "Completed"
    """
    try:
        if not group_member_ids:
            return "Not Started"
        
        total_submissions = 0
        completed_submissions = 0
        
        for member_id in group_member_ids:
            member_submissions = await db["submissions"].count_documents({
                "student_id": member_id
            })
            total_submissions += member_submissions
            
            member_completed = await db["submissions"].count_documents({
                "student_id": member_id,
                "status": "completed"
            })
            completed_submissions += member_completed
        
        group_deliverables = await db["deliverables"].count_documents({
            "student_ids": {"$in": group_member_ids}
        })
        
        if total_submissions == 0 and group_deliverables == 0:
            return "Not Started"
        elif completed_submissions >= group_deliverables and group_deliverables > 0:
            return "Completed"
        elif total_submissions > 0:
            changes_requested = await db["submissions"].count_documents({
                "student_id": {"$in": group_member_ids},
                "status": "changes_requested"
            })
            if changes_requested > 0:
                return "Changes Requested"
            else:
                return "In Progress"
        else:
            return "In Progress"
            
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
        
        member_ids = group.get("student_ids", [])
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
            "student_ids": ObjectId(student_id)
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
            "student_ids": ObjectId(student_id),
            "status": "active"
        })
        
        if group:
            other_students = []
            for other_student_id in group["student_ids"]:
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
