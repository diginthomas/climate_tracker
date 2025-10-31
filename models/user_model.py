# models/user_model.py
from pydantic import BaseModel, EmailStr
from typing import Optional

class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str
    status:bool = True

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    user_id: str
    username: str
    email: EmailStr
    role: str = "EndUser"
    status: bool
    profile_info: Optional[str] = None


class PatchUserRequest(BaseModel):
    user_id: str