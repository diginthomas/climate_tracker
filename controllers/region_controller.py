from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from typing import List

from auth.user_role_utils import verify_admin
from models.region import Region, RegionResponse
from database import regions_collection

router = APIRouter(prefix="/region", tags=["Region"])

# ⚙️ Notes:
# status: 1 = Active, 2 = Deactivated


# 🧾 Get all regions (public)
@router.get("/", response_model=List[RegionResponse])
async def all_regions():
    regions_cursor = regions_collection.find()
    regions = []
    async for region in regions_cursor:
        regions.append({
            "region_id": str(region["_id"]),
            "name": region["name"],
            "description": region.get("description", ""),
            "status": region["status"],
            "lat" :region["lat"],
            "lng" :region["lng"]
        })
    return regions


# ➕ Add new region (admin)
@router.post("/add", response_model=RegionResponse, dependencies=[Depends(verify_admin)])
async def add_region(region: Region):
    existing = await regions_collection.find_one({"name": region.name})
    if existing:
        raise HTTPException(status_code=400, detail="Region already exists")

    region_data = region.model_dump()
    result = await regions_collection.insert_one(region_data)

    return RegionResponse(
        region_id=str(result.inserted_id),
        name=region.name,
        description=region.description,
        status=region.status,
        lat=region.lat,
        lng=region.lng
    )


# 🔍 Get region by ID (public)
@router.get("/{region_id}", response_model=RegionResponse)
async def get_region(region_id: str):
    if not ObjectId.is_valid(region_id):
        raise HTTPException(status_code=400, detail="Invalid region ID")

    region = await regions_collection.find_one({"_id": ObjectId(region_id)})
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")

    return RegionResponse(
        region_id=str(region["_id"]),
        name=region["name"],
        description=region.get("description", ""),
        status=region["status"],
        lat=region["lat"],
        lng=region["lng"]
    )


# ✏️ Update region (admin)
@router.put("/{region_id}", response_model=RegionResponse, dependencies=[Depends(verify_admin)])
async def update_region(region_id: str, updated_data: Region):
    if not ObjectId.is_valid(region_id):
        raise HTTPException(status_code=400, detail="Invalid region ID")

    region = await regions_collection.find_one({"_id": ObjectId(region_id)})
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")

    await regions_collection.update_one(
        {"_id": ObjectId(region_id)},
        {"$set": updated_data.model_dump()}
    )

    return RegionResponse(
        region_id=region_id,
        name=updated_data.name,
        description=updated_data.description,
        status=updated_data.status,
        lat=updated_data.lat,
        lng=updated_data.lng
    )


# ❌ Deactivate (soft delete) region (admin)
@router.delete("/{region_id}", dependencies=[Depends(verify_admin)])
async def delete_region(region_id: str):
    if not ObjectId.is_valid(region_id):
        raise HTTPException(status_code=400, detail="Invalid region ID")

    region = await regions_collection.find_one({"_id": ObjectId(region_id)})
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")

    await regions_collection.update_one(
        {"_id": ObjectId(region_id)},
        {"$set": {"status": 2}}
    )

    return {"message": f"Region '{region['name']}' has been deactivated"}
