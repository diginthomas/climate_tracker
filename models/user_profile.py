from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class UserProfile(BaseModel):
    user_id: Optional[str] = None
    role: Optional[str] = "EndUser"
    bio: Optional[str] = None
    location: Optional[str] = None
    country: Optional[str] = None
    created_at: Optional[datetime] = None
    last_updated_at: Optional[datetime] = None
    linked_in_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None


class UserProfileResponse(BaseModel):
    profile_id: str
    user_id: str
    username: str
    email: EmailStr
    role: Optional[str] = "EndUser"
    bio: Optional[str] = None
    location: Optional[str] = None
    country: Optional[str] = None
    created_at: Optional[datetime] = None
    last_updated_at: Optional[datetime] = None
    linked_in_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
