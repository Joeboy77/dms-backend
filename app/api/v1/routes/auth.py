"""
Authentication API endpoints for student PIN-based login.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
import bcrypt
from bson import ObjectId
from datetime import datetime, timezone

from app.core.database import get_db
from pydantic import BaseModel

router = APIRouter(tags=["Authentication"])


class LoginRequest(BaseModel):
    academic_id: str
    pin: str


class LoginResponse(BaseModel):
    success: bool
    message: str
    student_info: dict | None = None
    roles: list[dict] | None = None


@router.post("/auth/student-login", response_model=LoginResponse)
async def authenticate_student(
    login_request: LoginRequest,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Authenticate a student using their academic ID and PIN.
    """
    try:
        # Find login record by academic ID
        login_record = await db.logins.find_one({
            "academicId": login_request.academic_id
        })
        
        if not login_record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"No login found for student ID: {login_request.academic_id}"
            )
        
        # Verify PIN
        stored_pin = login_record.get("pin")
        if not stored_pin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No PIN set for this student"
            )
        
        # Check PIN using bcrypt
        pin_matches = bcrypt.checkpw(
            login_request.pin.encode('utf-8'), 
            stored_pin.encode('utf-8')
        )
        
        if not pin_matches:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid PIN"
            )
        
        # Get role details
        role_details = []
        role_ids = login_record.get("roles", [])
        
        if not role_ids:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"No role found for student ID: {login_request.academic_id}"
            )
        
        for role_id in role_ids:
            role = await db.roles.find_one({"_id": role_id})
            if role and not role.get("deleted", False):
                role_details.append({
                    "role_id": str(role["_id"]),
                    "title": role.get("title", ""),
                    "slug": role.get("slug", ""),
                    "status": role.get("status", ""),
                    "description": role.get("description", "")
                })
        
        if not role_details:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"No valid roles found for student ID: {login_request.academic_id}"
            )
        
        # Get student information
        student = await db.students.find_one({
            "academicId": login_request.academic_id
        })
        
        student_info = None
        if student:
            student_info = {
                "student_id": str(student["_id"]),
                "name": f"{student.get('title', '')} {student.get('surname', '')} {student.get('otherNames', '')}".strip(),
                "email": student.get("email", ""),
                "academic_id": student.get("academicId", ""),
                "type": student.get("type", "")
            }
        
        # Update last login time
        await db.logins.update_one(
            {"_id": login_record["_id"]},
            {
                "$set": {
                    "lastLogin": datetime.now(timezone.utc),
                    "updatedAt": datetime.now(timezone.utc)
                }
            }
        )
        
        return LoginResponse(
            success=True,
            message="Authentication successful",
            student_info=student_info,
            roles=role_details
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication error: {str(e)}"
        )


@router.get("/auth/student-info/{academic_id}")
async def get_student_auth_info(
    academic_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Get authentication information for a student (for debugging/admin purposes).
    """
    try:
        # Find login record
        login_record = await db.logins.find_one({
            "academicId": academic_id
        })
        
        if not login_record:
            raise HTTPException(
                status_code=404,
                detail=f"No login found for student ID: {academic_id}"
            )
        
        # Get role details
        role_details = []
        for role_id in login_record.get("roles", []):
            role = await db.roles.find_one({"_id": role_id})
            if role:
                role_details.append({
                    "role_id": str(role["_id"]),
                    "title": role.get("title", ""),
                    "slug": role.get("slug", ""),
                    "status": role.get("status", ""),
                    "deleted": role.get("deleted", False)
                })
        
        # Get student info
        student = await db.students.find_one({
            "academicId": academic_id
        })
        
        return {
            "academic_id": academic_id,
            "has_login": True,
            "has_pin": bool(login_record.get("pin")),
            "roles": role_details,
            "last_login": login_record.get("lastLogin"),
            "student_exists": bool(student),
            "student_name": f"{student.get('title', '')} {student.get('surname', '')} {student.get('otherNames', '')}".strip() if student else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting student info: {str(e)}"
        )
