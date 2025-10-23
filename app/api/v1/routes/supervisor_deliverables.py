from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_db
from app.core.authentication.auth_middleware import get_current_token, RoleBasedAccessControl, TokenData
from pydantic import BaseModel
from typing import List, Optional
import cloudinary
import cloudinary.uploader
from datetime import datetime
import os

router = APIRouter(tags=["Supervisor Deliverables"])

require_supervisor = RoleBasedAccessControl(["projects_supervisor", "projects_coordinator"])

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)


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
            formatted_deliverable = {
                "id": str(deliverable["_id"]),
                "name": deliverable.get("name", ""),
                "start_date": deliverable.get("start_date", ""),
                "end_date": deliverable.get("end_date", ""),
                "instructions": deliverable.get("instructions", ""),
                "uploaded_template": {
                    "file_name": deliverable.get("template_file_name", ""),
                    "file_url": deliverable.get("template_file_url", ""),
                    "file_type": deliverable.get("template_file_type", ""),
                    "file_size": deliverable.get("template_file_size", 0)
                } if deliverable.get("template_file_url") else None,
                "created_at": deliverable.get("createdAt"),
                "updated_at": deliverable.get("updatedAt"),
                "total_submissions": deliverable.get("total_submissions", 0)
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


@router.post("/supervisor/deliverables")
async def create_deliverable(
    name: str = Form(...),
    start_date: str = Form(...),
    end_date: str = Form(...),
    instructions: str = Form(""),
    template_file: UploadFile = File(None),
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
        
        # Handle file upload to Cloudinary if file is provided
        template_file_info = None
        if template_file and template_file.filename:
            try:
                # Upload file to Cloudinary
                upload_result = cloudinary.uploader.upload(
                    template_file.file,
                    folder="deliverables/templates",
                    resource_type="auto",
                    public_id=f"{supervisor_academic_id}_{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                )
                
                template_file_info = {
                    "file_name": template_file.filename,
                    "file_url": upload_result["secure_url"],
                    "file_type": template_file.content_type,
                    "file_size": upload_result["bytes"],
                    "cloudinary_public_id": upload_result["public_id"]
                }
            except Exception as upload_error:
                raise HTTPException(status_code=500, detail=f"File upload failed: {str(upload_error)}")
        
        # Create deliverable data
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
        
        # Add template file info if uploaded
        if template_file_info:
            deliverable_data.update({
                "template_file_name": template_file_info["file_name"],
                "template_file_url": template_file_info["file_url"],
                "template_file_type": template_file_info["file_type"],
                "template_file_size": template_file_info["file_size"],
                "template_cloudinary_public_id": template_file_info["cloudinary_public_id"]
            })
        
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
                "uploaded_template": {
                    "file_name": created_deliverable.get("template_file_name", ""),
                    "file_url": created_deliverable.get("template_file_url", ""),
                    "file_type": created_deliverable.get("template_file_type", ""),
                    "file_size": created_deliverable.get("template_file_size", 0)
                } if created_deliverable.get("template_file_url") else None,
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
