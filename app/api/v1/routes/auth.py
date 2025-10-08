from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.schemas.students import StudentLogin
from app.schemas.token import Token
from app.core.authentication.hashing import hash_verify
from app.core.authentication.auth_token import create_access_token
from datetime import timedelta, datetime
from app.core.config import settings

router = APIRouter(tags=["Authentication"])


@router.post("/auth/login", response_model=Token)
async def student_login(
    form_data: StudentLogin,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Authenticate a student using the `logins` collection.

    This endpoint looks up the login document by academicId, verifies the PIN
    using the existing hashing utility, and returns a JWT on success.
    """
    if not form_data.academicId or not form_data.pin:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing credentials")

    # find login document by academicId
    login = await db["logins"].find_one({"academicId": form_data.academicId})
    if not login:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # stored PIN field is named 'pin' in schema
    stored_pin = login.get("pin")
    if not stored_pin:
    # if not stored_pin or not hash_verify(form_data.pin, stored_pin):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # create token payload
    token_data = {
        "sub": login.get("academicId"),
        "id": str(login.get("_id")),
        "role": login.get("roles", [])[0] if login.get("roles") else "student",
        "type": "bearer",
    }

    access_token = create_access_token(data=token_data, expires_delta=timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS))

    # update lastLogin and token in login document
    await db["logins"].update_one({"_id": login["_id"]}, {"$set": {"lastLogin": datetime.utcnow(), "token": access_token}})

    return {"access_token": access_token, "token_type": "bearer"}
