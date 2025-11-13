from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId
from datetime import datetime
from typing import Optional

from database import users_collection, profiles_collection
from auth.auth_utils import get_current_user
from models.user_profile import UserProfile, UserProfileResponse

router = APIRouter(prefix="/profile", tags=["profile"])


# 🟢 Create or Update User Profile
@router.post("/update", response_model=UserProfileResponse)
async def create_or_update_profile(
    profile_data: UserProfile,
    current_email: str = Depends(get_current_user)
):
    # Find the user by email (from JWT)
    user = await users_collection.find_one({"email": current_email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user_id = str(user["_id"])
    now = datetime.utcnow()

    # Check if profile already exists
    existing_profile = await profiles_collection.find_one({"user_id": user_id})

    # Build profile document from provided fields (ignore None)
    profile_doc = {k: v for k, v in profile_data.dict().items() if v is not None}
    profile_doc["user_id"] = user_id
    profile_doc["last_updated_at"] = now

    if existing_profile:
        # Update existing profile
        await profiles_collection.update_one({"user_id": user_id}, {"$set": profile_doc})
    else:
        profile_doc["created_at"] = now
        await profiles_collection.insert_one(profile_doc)

    # Fetch updated profile
    updated_profile = await profiles_collection.find_one({"user_id": user_id})

    return UserProfileResponse(
        profile_id=str(updated_profile["_id"]),
        user_id=user_id,
        username=user["username"],
        email=user["email"],
        role=updated_profile.get("role", "EndUser"),
        bio=updated_profile.get("bio"),
        location=updated_profile.get("location"),
        country=updated_profile.get("country"),
        created_at=updated_profile.get("created_at", now),
        last_updated_at=updated_profile.get("last_updated_at", now),
        linked_in_url=updated_profile.get("linked_in_url"),
        github_url=updated_profile.get("github_url"),
        portfolio_url=updated_profile.get("portfolio_url"),
    )


@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(current_email: str = Depends(get_current_user)):
    user = await users_collection.find_one({"email": current_email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user_id = str(user["_id"])
    profile = await profiles_collection.find_one({"user_id": user_id})

    # Return empty/default profile if none exists
    return UserProfileResponse(
        profile_id=str(profile["_id"]) if profile else "",
        user_id=user_id,
        username=user["username"],
        email=user["email"],
        role=profile.get("role", "EndUser") if profile else user.get("role", "EndUser"),
        bio=profile.get("bio") if profile else None,
        location=profile.get("location") if profile else None,
        country=profile.get("country") if profile else None,
        created_at=profile.get("created_at") if profile else None,
        last_updated_at=profile.get("last_updated_at") if profile else None,
        linked_in_url=profile.get("linked_in_url") if profile else None,
        github_url=profile.get("github_url") if profile else None,
        portfolio_url=profile.get("portfolio_url") if profile else None,
    )
