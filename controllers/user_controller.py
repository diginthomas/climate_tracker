from fastapi import APIRouter, Depends, HTTPException
from models.user_model import UserResponse
from database import users_collection
from auth.auth_utils import get_current_user

router = APIRouter(prefix="/user", tags=["user"])

@router.get("/profile", response_model=UserResponse)
async def user_details(current_email: str = Depends(get_current_user)):
    user = await users_collection.find_one({"email": current_email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse(
        user_id=str(user["_id"]),
        username=user["username"],
        email=user["email"],
        role=user.get("role", "EndUser"),
        profile_info=user.get("profile_info", None)
    )
