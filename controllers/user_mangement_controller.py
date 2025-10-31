from typing import List

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from auth.user_role_utils import verify_admin
from database import users_collection
from models.user_model import UserResponse, PatchUserRequest

router = APIRouter(prefix="/user/manage", tags=["user_management"],)


@router.get("/", response_model=List[UserResponse], dependencies=[Depends(verify_admin)])
async def get_non_admin_users():
    users = list(users_collection.find({"role": {"$ne": "Admin"}}))

    # Convert MongoDB documents to Pydantic models
    return [UserResponse(**user, user_id=str(user["_id"])) for user in users]


@router.patch("/", response_model=UserResponse, dependencies=[Depends(verify_admin)])
async def patch_user(request: PatchUserRequest):
    user = users_collection.find_one({"_id": ObjectId(request.user_id)})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Toggle boolean status
    new_status = not user.get("status", False)

    users_collection.update_one(
        {"_id": ObjectId(request.user_id)},
        {"$set": {"status": new_status}}
    )

    # Return updated user
    user["status"] = new_status
    return UserResponse(
        user_id=str(user["_id"]),
        username=user.get("username"),
        email=user.get("email"),
        role=user.get("role"),
        status=new_status
    )