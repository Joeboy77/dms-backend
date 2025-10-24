from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import timedelta, datetime

from app.core.database import get_db
from app.schemas.students import StudentLogin
from app.schemas.token import Token
from app.core.authentication.hashing import hash_verify
from app.core.authentication.auth_token import create_access_token
from app.core.config import settings

router = APIRouter(tags=["Authentication"])


@router.post("/auth/login", response_model=Token)
async def login_user(
    form_data: StudentLogin,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Authenticate a user (student or lecturer).
    Checks the `logins` and `lecturers` collections for academicId and verifies pin.
    Returns a JWT on success with the appropriate role context.
    """
    if not form_data.academicId or not form_data.pin:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing credentials")

    # ---- Try student login first ----
    login = await db["students"].find_one({"academicId": form_data.academicId})
    user_type = "student"

    # ---- If not found, check lecturers collection ----
    if not login:
        login = await db["lecturers"].find_one({"academicId": form_data.academicId})
        user_type = "lecturer" if login else None

    if not login:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # ---- Verify PIN ----
    stored_pin = login.get("pin")
    # if pin is hashed
    try:
        is_valid = hash_verify(form_data.pin, stored_pin)
    except Exception:
        # fallback to plain match (if hashing not yet implemented)
        is_valid = form_data.pin == stored_pin

    if not is_valid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # ---- Determine role ----
    role_value = user_type
    
    # Special role mapping for lecturers
    if user_type == "lecturer":
        academic_id = login.get("academicId")
        if academic_id == "LEC2025003":
            role_value = "projects_coordinator"  # LEC2025003 is both coordinator and supervisor
        else:
            role_value = "projects_supervisor"
    else:
        # For students, check roles from database if available
        roles_list = login.get("roles", []) or []
        if roles_list:
            try:
                first_role = await db["roles"].find_one({"_id": roles_list[0]})
                if first_role:
                    role_value = first_role.get("slug") or first_role.get("title") or str(first_role.get("_id"))
                elif isinstance(roles_list[0], str):
                    role_value = roles_list[0]
            except Exception:
                if isinstance(roles_list[0], str):
                    role_value = roles_list[0]

    # ---- Create JWT ----
    token_data = {
        "sub": login.get("academicId"),
        "id": str(login.get("_id")),
        "role": role_value,
        "type": "bearer",
    }

    access_token = create_access_token(
        data=token_data,
        expires_delta=timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS),
    )

    # ---- Check if this is first login ----
    is_first_login = False
    if user_type == "student":
        # Check if lastLogin field exists and is None/empty
        last_login = login.get("lastLogin")
        if last_login is None:
            is_first_login = True

    # ---- Update last login and token ----
    await db[user_type + "s"].update_one(
        {"_id": login["_id"]},
        {"$set": {"lastLogin": datetime.utcnow(), "token": access_token}},
    )

    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user": {
            "academicId": login.get("academicId"),
            "role": role_value,
            "user_type": user_type,
            "isFirstLogin": is_first_login
        }
    }


@router.post("/auth/logout")
async def logout_user(
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Logout endpoint to invalidate user session.
    In a stateless JWT system, logout is typically handled client-side by removing the token.
    This endpoint can be used for logging purposes or to invalidate tokens on the server side.
    """

    
    return {"message": "Logout successful", "success": True}
