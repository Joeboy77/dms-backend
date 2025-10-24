from pydantic import BaseModel
from typing import Optional

class UserInfo(BaseModel):
    academicId: str
    role: str
    user_type: str
    isFirstLogin: Optional[bool] = False

class Token(BaseModel):
    access_token: str
    token_type: str
    user: Optional[UserInfo] = None


class TokenData(BaseModel):
    id: str
    email: str
    role: str
    type: str


class EmailVerificationToken(BaseModel):
    verification_token: str
