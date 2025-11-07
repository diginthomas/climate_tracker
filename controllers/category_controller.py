from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from auth.user_role_utils import verify_admin
from models.category import Category, CategoryResponse
from database import categories_collection
from typing import List

router = APIRouter(prefix="/category", tags=["Category"])

# ⚙️ Note:
# 1 = Active
# 2 = Deactivated


# 🧾 Get all categories (anyone can view)
@router.get("/", response_model=List[CategoryResponse])
async def all_categories():
    categories_cursor = categories_collection.find()
    categories = []
    async for category in categories_cursor:  # ✅ async iteration
        categories.append({
            "category_id": str(category["_id"]),
            "title": category["title"],
            "description": category["description"],
            "status": category["status"]
        })
    return categories


# ➕ Add category (🔒 protected)
@router.post("/add", response_model=CategoryResponse,dependencies=[Depends(verify_admin)])
async def add_category(category: Category):
    # existing = categories_collection.find_one({"title": category.title})
    # if existing:
    #     raise HTTPException(status_code=400, detail="Category already exists")

    category_result = await categories_collection.insert_one(category.model_dump())
    return CategoryResponse(
        category_id=str(category_result.inserted_id),
        title=category.title,
        description=category.description,
        status=category.status
    )


# 🔍 Get category by ID (anyone can view)
@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(category_id: str):
    category = categories_collection.find_one({"_id": ObjectId(category_id)})
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    return CategoryResponse(
        category_id=str(category["_id"]),
        title=category["title"],
        description=category["description"],
        status=category["status"]
    )


# ✏️ Update category (🔒 protected)
@router.put("/{category_id}", response_model=CategoryResponse,dependencies=[Depends(verify_admin)])
async def update_category(category_id: str, updated_data: Category):
    category = categories_collection.find_one({"_id": ObjectId(category_id)})
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    categories_collection.update_one(
        {"_id": ObjectId(category_id)},
        {"$set": updated_data.model_dump()}
    )

    return CategoryResponse(
        category_id=category_id,
        title=updated_data.title,
        description=updated_data.description,
        status=updated_data.status
    )


# ❌ Soft delete category (🔒 protected)
@router.delete("/{category_id}",dependencies=[Depends(verify_admin)])
async def delete_category(category_id: str):
    category = categories_collection.find_one({"_id": ObjectId(category_id)})
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    categories_collection.update_one(
        {"_id": ObjectId(category_id)},
        {"$set": {"status": 2}}
    )

    return {"message": f"Category '{category['title']}' has been deactivated"}
