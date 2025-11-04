from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List
from datetime import datetime

from app.core.authentication.auth_middleware import RoleBasedAccessControl, get_current_token
from app.core.database import get_db
from app.core.config import settings
from app.schemas.announcements import (
    AnnouncementCreate,
    AnnouncementPublic,
    AnnouncementUpdate,
    Page
)
from app.schemas.token import TokenData
from app.controllers.announcements import AnnouncementController
from bson import ObjectId
import cloudinary
import cloudinary.uploader

router = APIRouter(tags=["Announcements"])

require_supervisor = RoleBasedAccessControl(["projects_supervisor"])
require_student = RoleBasedAccessControl(["student"])


@router.post("/announcements", response_model=AnnouncementPublic)
async def create_announcement(
    announcement_data: AnnouncementCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_supervisor)
):
    supervisor = await db["lecturers"].find_one({"academicId": current_user.email})
    if not supervisor:
        raise HTTPException(status_code=404, detail="Supervisor not found")
    
    supervisor_doc = await db["supervisors"].find_one({"lecturer_id": supervisor["_id"]})
    if not supervisor_doc:
        raise HTTPException(status_code=404, detail="Supervisor record not found")
    
    controller = AnnouncementController(db)
    return await controller.create_announcement(announcement_data, str(supervisor_doc["_id"]))


@router.get("/announcements", response_model=Page)
async def get_supervisor_announcements(
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_supervisor)
):
    supervisor = await db["lecturers"].find_one({"academicId": current_user.email})
    if not supervisor:
        raise HTTPException(status_code=404, detail="Supervisor not found")
    
    supervisor_doc = await db["supervisors"].find_one({"lecturer_id": supervisor["_id"]})
    if not supervisor_doc:
        raise HTTPException(status_code=404, detail="Supervisor record not found")
    
    controller = AnnouncementController(db)
    return await controller.get_supervisor_announcements(str(supervisor_doc["_id"]), limit, cursor)


@router.get("/announcements/student", response_model=Page)
async def get_student_announcements(
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_student)
):
    student = await db["students"].find_one({"academicId": current_user.email})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    controller = AnnouncementController(db)
    return await controller.get_student_announcements(str(student["_id"]), limit, cursor)


@router.get("/announcements/{announcement_id}", response_model=AnnouncementPublic)
async def get_announcement(
    announcement_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(get_current_token)
):
    controller = AnnouncementController(db)
    return await controller.get_announcement_by_id(announcement_id)


@router.patch("/announcements/{announcement_id}", response_model=AnnouncementPublic)
async def update_announcement(
    announcement_id: str,
    update_data: AnnouncementUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_supervisor)
):
    supervisor = await db["lecturers"].find_one({"academicId": current_user.email})
    if not supervisor:
        raise HTTPException(status_code=404, detail="Supervisor not found")
    
    supervisor_doc = await db["supervisors"].find_one({"lecturer_id": supervisor["_id"]})
    if not supervisor_doc:
        raise HTTPException(status_code=404, detail="Supervisor record not found")
    
    controller = AnnouncementController(db)
    return await controller.update_announcement(announcement_id, update_data, str(supervisor_doc["_id"]))


@router.delete("/announcements/{announcement_id}")
async def delete_announcement(
    announcement_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_supervisor)
):
    supervisor = await db["lecturers"].find_one({"academicId": current_user.email})
    if not supervisor:
        raise HTTPException(status_code=404, detail="Supervisor not found")
    
    supervisor_doc = await db["supervisors"].find_one({"lecturer_id": supervisor["_id"]})
    if not supervisor_doc:
        raise HTTPException(status_code=404, detail="Supervisor record not found")
    
    controller = AnnouncementController(db)
    return await controller.delete_announcement(announcement_id, str(supervisor_doc["_id"]))


@router.post("/announcements/upload")
async def upload_announcement_files(
    files: List[UploadFile] = File(...),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_supervisor)
):
    """
    Upload files for announcements (images, documents).
    Files are uploaded to Cloudinary and URLs are returned.
    """
    try:
        if not files:
            raise HTTPException(status_code=400, detail="No files provided")
        
        supervisor = await db["lecturers"].find_one({"academicId": current_user.email})
        if not supervisor:
            raise HTTPException(status_code=404, detail="Supervisor not found")
        
        supervisor_academic_id = current_user.email
        
        # Configure Cloudinary
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET
        )
        
        uploaded_urls = []
        
        for file in files:
            if not file.filename:
                continue
            
            try:
                # Determine resource type based on file extension
                file_ext = file.filename.split('.')[-1].lower()
                resource_type = "auto"
                if file_ext in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg']:
                    resource_type = "image"
                elif file_ext in ['pdf', 'doc', 'docx', 'txt', 'xls', 'xlsx', 'ppt', 'pptx']:
                    resource_type = "raw"
                
                # Upload to Cloudinary
                upload_result = cloudinary.uploader.upload(
                    file.file,
                    folder="announcements",
                    resource_type=resource_type,
                    public_id=f"{supervisor_academic_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename.rsplit('.', 1)[0]}"
                )
                
                uploaded_urls.append(upload_result["secure_url"])
            except Exception as upload_error:
                raise HTTPException(status_code=500, detail=f"Failed to upload {file.filename}: {str(upload_error)}")
        
        if not uploaded_urls:
            raise HTTPException(status_code=400, detail="No files were successfully uploaded")
        
        return {"urls": uploaded_urls, "count": len(uploaded_urls)}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading files: {str(e)}")

