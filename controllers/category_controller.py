from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from auth.user_role_utils import verify_admin
from models.category import Category, CategoryResponse
from database import categories_collection
from typing import List
from utils.pagination import get_pagination_params, create_paginated_response, PaginatedResponse
from constants import CATEGORY_STATUS_ACTIVE, CATEGORY_STATUS_DEACTIVATED

router = APIRouter(prefix="/category", tags=["Category"])


# 🧾 Get all categories (anyone can view) - with pagination
@router.get("/", response_model=PaginatedResponse[CategoryResponse])
async def all_categories(
    page: Optional[int] = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: Optional[int] = Query(20, ge=1, le=100, description="Number of items per page (max 100)")
) -> PaginatedResponse[CategoryResponse]:
    # Get pagination parameters
    skip, limit = get_pagination_params(page, page_size)
    
    # Count total documents
    total = await categories_collection.count_documents({})
    
    # Fetch categories with pagination
    categories_cursor = categories_collection.find().skip(skip).limit(limit).sort("title", 1)
    categories = []
    async for category in categories_cursor:
        categories.append(CategoryResponse(
            category_id=str(category["_id"]),
            title=category["title"],
            description=category["description"],
            status=category["status"]
        ))
    
    return create_paginated_response(
        items=categories,
        total=total,
        page=page or 1,
        page_size=page_size or 20
    )


# ➕ Add category (🔒 protected)
@router.post("/add", response_model=CategoryResponse,dependencies=[Depends(verify_admin)])
async def add_category(category: Category) -> CategoryResponse:
    existing = await categories_collection.find_one({"title": category.title})
    if existing:
        raise HTTPException(status_code=400, detail="Category already exists")

    category_result = await categories_collection.insert_one(category.model_dump())
    return CategoryResponse(
        category_id=str(category_result.inserted_id),
        title=category.title,
        description=category.description,
        status=category.status
    )


# 🔍 Get category by ID (anyone can view)
@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(category_id: str) -> CategoryResponse:
    category = await categories_collection.find_one({"_id": ObjectId(category_id)})
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
async def update_category(category_id: str, updated_data: Category) -> CategoryResponse:
    category = await categories_collection.find_one({"_id": ObjectId(category_id)})
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    await categories_collection.update_one(
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
async def delete_category(category_id: str) -> dict[str, str]:
    category = await categories_collection.find_one({"_id": ObjectId(category_id)})
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    await categories_collection.update_one(
        {"_id": ObjectId(category_id)},
        {"$set": {"status": CATEGORY_STATUS_DEACTIVATED}}
    )

    return {"message": f"Category '{category['title']}' has been deactivated"}
