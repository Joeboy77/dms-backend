from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_db
from app.core.authentication.auth_middleware import get_current_token, RoleBasedAccessControl, TokenData
from app.core.config import settings
from pydantic import BaseModel
from typing import List, Optional
import cloudinary
import cloudinary.uploader
from datetime import datetime
import os

router = APIRouter(tags=["Supervisor Deliverables"])

require_supervisor = RoleBasedAccessControl(["projects_supervisor", "projects_coordinator"])

# Cloudinary configuration will be set in the upload function to ensure env vars are loaded


class DeliverableCreate(BaseModel):
    name: str
    start_date: str
    end_date: str
    instructions: Optional[str] = None


class DeliverableUpdate(BaseModel):
    name: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    instructions: Optional[str] = None


@router.get("/supervisor/deliverables")
async def get_supervisor_deliverables(
    limit: int = Query(20, ge=1, le=100),
    search: str = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_supervisor)
):
    """
    Get all deliverables created by the current supervisor.
    """
    try:
        from bson import ObjectId
        
        supervisor_academic_id = current_user.email
        if not supervisor_academic_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing supervisor ID")
        
        supervisor = await db["lecturers"].find_one({"academicId": supervisor_academic_id})
        if not supervisor:
            raise HTTPException(status_code=404, detail="Supervisor not found")
        
        supervisor_id = supervisor["_id"]
        
        query = {"supervisor_id": supervisor_id}
        if search:
            query["name"] = {"$regex": search, "$options": "i"}
        
        deliverables = await db["deliverables"].find(query).sort("createdAt", -1).limit(limit).to_list(length=limit)
        
        formatted_deliverables = []
        for deliverable in deliverables:
            actual_submission_count = await db["submissions"].count_documents({
                "deliverable_id": deliverable["_id"]
            })
            
            formatted_deliverable = {
                "id": str(deliverable["_id"]),
                "name": deliverable.get("name", ""),
                "start_date": deliverable.get("start_date", ""),
                "end_date": deliverable.get("end_date", ""),
                "instructions": deliverable.get("instructions", ""),
                "uploaded_templates": deliverable.get("template_files", []),
                "created_at": deliverable.get("createdAt"),
                "updated_at": deliverable.get("updatedAt"),
                "total_submissions": actual_submission_count
            }
            formatted_deliverables.append(formatted_deliverable)
        
        total_deliverables = await db["deliverables"].count_documents(query)
        
        return {
            "deliverables": formatted_deliverables,
            "supervisor_info": {
                "academic_id": supervisor_academic_id,
                "name": f"{supervisor.get('surname', '')} {supervisor.get('otherNames', '')}".strip()
            },
            "pagination": {
                "current_page": 1,
                "per_page": limit,
                "total": total_deliverables,
                "showing": f"1-{len(formatted_deliverables)} of {total_deliverables}"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching deliverables: {str(e)}")


@router.get("/supervisor/deliverables/{deliverable_id}/submissions")
async def get_deliverable_submissions(
    deliverable_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_supervisor)
):
    """
    Get all submissions for a specific deliverable.
    """
    try:
        from bson import ObjectId
        
        supervisor_academic_id = current_user.email
        if not supervisor_academic_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing supervisor ID")
        
        supervisor = await db["lecturers"].find_one({"academicId": supervisor_academic_id})
        if not supervisor:
            raise HTTPException(status_code=404, detail="Supervisor not found")
        
        supervisor_id = supervisor["_id"]
        
        # Verify the deliverable belongs to this supervisor
        deliverable = await db["deliverables"].find_one({
            "_id": ObjectId(deliverable_id),
            "supervisor_id": supervisor_id
        })
        
        if not deliverable:
            raise HTTPException(status_code=404, detail="Deliverable not found")
        
        # Get all submissions for this deliverable
        submissions = await db["submissions"].find({
            "deliverable_id": ObjectId(deliverable_id)
        }).to_list(length=None)
        
        # Format submissions with group/student details
        formatted_submissions = []
        for submission in submissions:
            submission_data = {
                "id": str(submission["_id"]),
                "status": submission.get("status", "not_started"),
                "created_at": submission.get("createdAt"),
                "updated_at": submission.get("updatedAt"),
                "deliverable_name": deliverable.get("name", ""),
                "files": []
            }
            
            # Get submission files
            files = await db["submission_files"].find({
                "submission_id": submission["_id"]
            }).to_list(length=None)
            
            for file in files:
                submission_data["files"].append({
                    "id": str(file["_id"]),
                    "file_name": file.get("file_name", ""),
                    "file_url": file.get("file_url", ""),
                    "file_type": file.get("file_type", ""),
                    "file_size": file.get("file_size", 0),
                    "uploaded_at": file.get("uploaded_at")
                })
            
            # Check if it's a group submission or individual submission
            if submission.get("group_id"):
                # Group submission
                group = await db["groups"].find_one({"_id": submission["group_id"]})
                if group:
                    submission_data["type"] = "group"
                    submission_data["group_id"] = str(submission["group_id"])
                    submission_data["group_name"] = group.get("name", "")
                    submission_data["member_count"] = len(group.get("members", []))
                    
                    # Get member images for the group
                    member_images = []
                    for member_id in group.get("members", []):
                        student = await db["students"].find_one({"_id": member_id})
                        if student and student.get("image"):
                            member_images.append(student["image"])
                    submission_data["member_images"] = member_images
            elif submission.get("student_id"):
                # Individual submission
                student = await db["students"].find_one({"_id": submission["student_id"]})
                if student:
                    submission_data["type"] = "individual"
                    submission_data["student_id"] = str(submission["student_id"])
                    submission_data["student_name"] = student.get("name", "")
                    submission_data["student_academic_id"] = student.get("academicId", "")
                    submission_data["student_image"] = student.get("image", "")
            
            formatted_submissions.append(submission_data)
        
        return {
            "deliverable": {
                "id": str(deliverable["_id"]),
                "name": deliverable.get("name", ""),
                "start_date": deliverable.get("start_date", ""),
                "end_date": deliverable.get("end_date", ""),
                "instructions": deliverable.get("instructions", "")
            },
            "submissions": formatted_submissions,
            "total_submissions": len(formatted_submissions)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching submissions: {str(e)}")


@router.put("/supervisor/submissions/{submission_id}")
async def update_submission_status(
    submission_id: str,
    request: dict,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_supervisor)
):
    """
    Update submission status and add comments if needed.
    """
    try:
        from bson import ObjectId
        
        # Extract data from request
        status = request.get("status")
        comments = request.get("comments", "")
        
        if not status:
            raise HTTPException(status_code=400, detail="Status is required")
        
        supervisor_academic_id = current_user.email
        if not supervisor_academic_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing supervisor ID")
        
        supervisor = await db["lecturers"].find_one({"academicId": supervisor_academic_id})
        if not supervisor:
            raise HTTPException(status_code=404, detail="Supervisor not found")
        
        supervisor_id = supervisor["_id"]
        
        # Find the submission
        submission = await db["submissions"].find_one({"_id": ObjectId(submission_id)})
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")
        
        # Verify the submission belongs to a deliverable created by this supervisor
        deliverable = await db["deliverables"].find_one({
            "_id": submission["deliverable_id"],
            "supervisor_id": supervisor_id
        })
        if not deliverable:
            raise HTTPException(status_code=403, detail="You don't have permission to update this submission")
        
        # Validate status
        valid_statuses = ["not_started", "in_progress", "pending_review", "changes_requested", "approved"]
        if status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
        
        # Prepare update data
        update_data = {
            "status": status,
            "updatedAt": datetime.utcnow()
        }
        
        # Add comments if status is changes_requested
        if status == "changes_requested" and comments.strip():
            update_data["supervisor_comments"] = comments.strip()
        
        # Update the submission
        await db["submissions"].update_one(
            {"_id": ObjectId(submission_id)},
            {"$set": update_data}
        )
        
        return {
            "message": "Submission status updated successfully",
            "submission_id": submission_id,
            "status": status,
            "comments": comments.strip() if status == "changes_requested" else None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating submission: {str(e)}")


@router.post("/supervisor/deliverables")
async def create_deliverable(
    name: str = Form(...),
    start_date: str = Form(...),
    end_date: str = Form(...),
    instructions: str = Form(""),
    template_files: List[UploadFile] = File(None),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_supervisor)
):
    """
    Create a new deliverable for the current supervisor.
    Includes file upload to Cloudinary.
    """
    try:
        from bson import ObjectId
        
        supervisor_academic_id = current_user.email
        if not supervisor_academic_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing supervisor ID")
        
        supervisor = await db["lecturers"].find_one({"academicId": supervisor_academic_id})
        if not supervisor:
            raise HTTPException(status_code=404, detail="Supervisor not found")
        
        supervisor_id = supervisor["_id"]
        
        template_files_info = []
        if template_files:
            # Configure Cloudinary with settings
            cloudinary.config(
                cloud_name=settings.CLOUDINARY_CLOUD_NAME,
                api_key=settings.CLOUDINARY_API_KEY,
                api_secret=settings.CLOUDINARY_API_SECRET
            )
            
            for i, template_file in enumerate(template_files):
                if template_file and template_file.filename:
                    try:
                        upload_result = cloudinary.uploader.upload(
                            template_file.file,
                            folder="deliverables/templates",
                            resource_type="auto",
                            public_id=f"{supervisor_academic_id}_{name}_{i}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        )
                        
                        template_files_info.append({
                            "file_name": template_file.filename,
                            "file_url": upload_result["secure_url"],
                            "file_type": template_file.content_type,
                            "file_size": upload_result["bytes"],
                            "cloudinary_public_id": upload_result["public_id"]
                        })
                    except Exception as upload_error:
                        raise HTTPException(status_code=500, detail=f"File upload failed: {str(upload_error)}")
        
        deliverable_data = {
            "name": name,
            "start_date": start_date,
            "end_date": end_date,
            "instructions": instructions,
            "supervisor_id": supervisor_id,
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
            "total_submissions": 0
        }
        
        if template_files_info:
            deliverable_data["template_files"] = template_files_info
        
        # Insert deliverable
        result = await db["deliverables"].insert_one(deliverable_data)
        created_deliverable = await db["deliverables"].find_one({"_id": result.inserted_id})
        
        return {
            "message": "Deliverable created successfully",
            "deliverable": {
                "id": str(created_deliverable["_id"]),
                "name": created_deliverable["name"],
                "start_date": created_deliverable["start_date"],
                "end_date": created_deliverable["end_date"],
                "instructions": created_deliverable["instructions"],
                "uploaded_templates": created_deliverable.get("template_files", []),
                "created_at": created_deliverable["createdAt"],
                "total_submissions": 0
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating deliverable: {str(e)}")


@router.patch("/supervisor/deliverables/{deliverable_id}")
async def update_deliverable(
    deliverable_id: str,
    name: str = Form(None),
    start_date: str = Form(None),
    end_date: str = Form(None),
    instructions: str = Form(None),
    template_file: UploadFile = File(None),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_supervisor)
):
    """
    Update an existing deliverable.
    """
    try:
        from bson import ObjectId
        
        supervisor_academic_id = current_user.email
        if not supervisor_academic_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing supervisor ID")
        
        supervisor = await db["lecturers"].find_one({"academicId": supervisor_academic_id})
        if not supervisor:
            raise HTTPException(status_code=404, detail="Supervisor not found")
        
        supervisor_id = supervisor["_id"]
        
        # Check if deliverable exists and belongs to supervisor
        deliverable = await db["deliverables"].find_one({
            "_id": ObjectId(deliverable_id),
            "supervisor_id": supervisor_id
        })
        
        if not deliverable:
            raise HTTPException(status_code=404, detail="Deliverable not found")
        
        # Prepare update data
        update_data = {"updatedAt": datetime.utcnow()}
        
        if name is not None:
            update_data["name"] = name
        if start_date is not None:
            update_data["start_date"] = start_date
        if end_date is not None:
            update_data["end_date"] = end_date
        if instructions is not None:
            update_data["instructions"] = instructions
        
        # Handle file upload if new file is provided
        if template_file and template_file.filename:
            try:
                # Configure Cloudinary with settings
                cloudinary.config(
                    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
                    api_key=settings.CLOUDINARY_API_KEY,
                    api_secret=settings.CLOUDINARY_API_SECRET
                )
                
                # Delete old file from Cloudinary if exists
                if deliverable.get("template_cloudinary_public_id"):
                    try:
                        cloudinary.uploader.destroy(deliverable["template_cloudinary_public_id"])
                    except:
                        pass  # Ignore errors when deleting old file
                
                # Upload new file to Cloudinary
                upload_result = cloudinary.uploader.upload(
                    template_file.file,
                    folder="deliverables/templates",
                    resource_type="auto",
                    public_id=f"{supervisor_academic_id}_{name or deliverable['name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                )
                
                update_data.update({
                    "template_file_name": template_file.filename,
                    "template_file_url": upload_result["secure_url"],
                    "template_file_type": template_file.content_type,
                    "template_file_size": upload_result["bytes"],
                    "template_cloudinary_public_id": upload_result["public_id"]
                })
            except Exception as upload_error:
                raise HTTPException(status_code=500, detail=f"File upload failed: {str(upload_error)}")
        
        # Update deliverable
        await db["deliverables"].update_one(
            {"_id": ObjectId(deliverable_id)},
            {"$set": update_data}
        )
        
        # Get updated deliverable
        updated_deliverable = await db["deliverables"].find_one({"_id": ObjectId(deliverable_id)})
        
        return {
            "message": "Deliverable updated successfully",
            "deliverable": {
                "id": str(updated_deliverable["_id"]),
                "name": updated_deliverable["name"],
                "start_date": updated_deliverable["start_date"],
                "end_date": updated_deliverable["end_date"],
                "instructions": updated_deliverable["instructions"],
                "uploaded_template": {
                    "file_name": updated_deliverable.get("template_file_name", ""),
                    "file_url": updated_deliverable.get("template_file_url", ""),
                    "file_type": updated_deliverable.get("template_file_type", ""),
                    "file_size": updated_deliverable.get("template_file_size", 0)
                } if updated_deliverable.get("template_file_url") else None,
                "created_at": updated_deliverable["createdAt"],
                "updated_at": updated_deliverable["updatedAt"],
                "total_submissions": updated_deliverable.get("total_submissions", 0)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating deliverable: {str(e)}")


@router.put("/supervisor/deliverables/{deliverable_id}")
async def update_deliverable(
    deliverable_id: str,
    request: dict,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_supervisor)
):
    """
    Update a deliverable.
    """
    try:
        from bson import ObjectId
        
        supervisor_academic_id = current_user.email
        if not supervisor_academic_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing supervisor ID")
        
        supervisor = await db["lecturers"].find_one({"academicId": supervisor_academic_id})
        if not supervisor:
            raise HTTPException(status_code=404, detail="Supervisor not found")
        
        supervisor_id = supervisor["_id"]
        
        # Check if deliverable exists and belongs to supervisor
        deliverable = await db["deliverables"].find_one({
            "_id": ObjectId(deliverable_id),
            "supervisor_id": supervisor_id
        })
        
        if not deliverable:
            raise HTTPException(status_code=404, detail="Deliverable not found")
        
        # Extract update data from request
        update_data = {
            "updatedAt": datetime.utcnow()
        }
        
        if "name" in request:
            update_data["name"] = request["name"]
        if "start_date" in request:
            update_data["start_date"] = request["start_date"]
        if "end_date" in request:
            update_data["end_date"] = request["end_date"]
        if "instructions" in request:
            update_data["instructions"] = request["instructions"]
        
        # Update the deliverable
        await db["deliverables"].update_one(
            {"_id": ObjectId(deliverable_id)},
            {"$set": update_data}
        )
        
        # Get the updated deliverable
        updated_deliverable = await db["deliverables"].find_one({"_id": ObjectId(deliverable_id)})
        
        return {
            "message": "Deliverable updated successfully",
            "deliverable": {
                "id": str(updated_deliverable["_id"]),
                "name": updated_deliverable["name"],
                "start_date": updated_deliverable["start_date"],
                "end_date": updated_deliverable["end_date"],
                "instructions": updated_deliverable.get("instructions", ""),
                "uploaded_templates": updated_deliverable.get("template_files", []),
                "created_at": updated_deliverable["createdAt"],
                "updated_at": updated_deliverable["updatedAt"],
                "total_submissions": updated_deliverable.get("total_submissions", 0)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating deliverable: {str(e)}")


@router.delete("/supervisor/deliverables/{deliverable_id}")
async def delete_deliverable(
    deliverable_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_supervisor)
):
    """
    Delete a deliverable and its associated file from Cloudinary.
    """
    try:
        from bson import ObjectId
        
        supervisor_academic_id = current_user.email
        if not supervisor_academic_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing supervisor ID")
        
        supervisor = await db["lecturers"].find_one({"academicId": supervisor_academic_id})
        if not supervisor:
            raise HTTPException(status_code=404, detail="Supervisor not found")
        
        supervisor_id = supervisor["_id"]
        
        # Check if deliverable exists and belongs to supervisor
        deliverable = await db["deliverables"].find_one({
            "_id": ObjectId(deliverable_id),
            "supervisor_id": supervisor_id
        })
        
        if not deliverable:
            raise HTTPException(status_code=404, detail="Deliverable not found")
        
        # Delete file from Cloudinary if exists
        if deliverable.get("template_cloudinary_public_id"):
            try:
                cloudinary.uploader.destroy(deliverable["template_cloudinary_public_id"])
            except:
                pass  # Ignore errors when deleting file
        
        # Delete deliverable from database
        await db["deliverables"].delete_one({"_id": ObjectId(deliverable_id)})
        
        return {
            "message": "Deliverable deleted successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting deliverable: {str(e)}")
