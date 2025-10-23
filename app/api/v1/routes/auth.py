# from fastapi import APIRouter, Depends, HTTPException, status
# from motor.motor_asyncio import AsyncIOMotorDatabase

# from app.core.database import get_db
# from app.schemas.students import StudentLogin
# from app.schemas.token import Token
# from app.core.authentication.hashing import hash_verify
# from app.core.authentication.auth_token import create_access_token
# from datetime import timedelta, datetime
# from app.core.config import settings

# router = APIRouter(tags=["Authentication"])


# @router.post("/auth/login", response_model=Token)
# async def student_login(
#     form_data: StudentLogin,
#     db: AsyncIOMotorDatabase = Depends(get_db),
# ):
#     """Authenticate a student using the `logins` collection.

#     This endpoint looks up the login document by academicId, verifies the PIN
#     using the existing hashing utility, and returns a JWT on success.
#     """
#     if not form_data.academicId or not form_data.pin:
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing credentials")

#     # find login document by academicId
#     login = await db["logins"].find_one({"academicId": form_data.academicId})
#     if not login:
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

#     # stored PIN field is named 'pin' in schema - verify hashed pin
#     stored_pin = login.get("pin")
#     if form_data.pin != stored_pin:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid credentials"
#         )

#     # determine role: if roles contains ObjectId(s), fetch the first role document and use its slug
#     role_value = "student"
#     roles_list = login.get("roles", []) or []
#     if roles_list:
#         try:
#             # assume roles are stored as ObjectId(s) in the array
#             first_role = await db["roles"].find_one({"_id": roles_list[0]})
#             if first_role:
#                 # prefer slug, fallback to title or id string
#                 role_value = first_role.get("slug") or first_role.get("title") or str(first_role.get("_id"))
#             else:
#                 # if roles are strings (already slugs), just use the first
#                 if isinstance(roles_list[0], str):
#                     role_value = roles_list[0]
#         except Exception:
#             # fallback: if roles contain raw strings
#             if isinstance(roles_list[0], str):
#                 role_value = roles_list[0]

#     token_data = {
#         "sub": login.get("academicId"),
#         "id": str(login.get("_id")),
#         "role": role_value,
#         "type": "bearer",
#     }

#     access_token = create_access_token(data=token_data, expires_delta=timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS))

#     # update lastLogin and token in login document
#     await db["logins"].update_one({"_id": login["_id"]}, {"$set": {"lastLogin": datetime.utcnow(), "token": access_token}})

#     return {"access_token": access_token, "token_type": "bearer"}

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
            role_value = "projects_coordinator"
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

    # ---- Update last login and token ----
    await db[user_type + "s"].update_one(
        {"_id": login["_id"]},
        {"$set": {"lastLogin": datetime.utcnow(), "token": access_token}},
    )

    return {"access_token": access_token, "token_type": "bearer"}
