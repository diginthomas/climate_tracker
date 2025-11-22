from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Query, Body
from bson import ObjectId
from datetime import datetime
import uuid
from typing import Optional, List

from database import events_collection, categories_collection
from models.event import EventResponse, FeatureToggleRequest
from auth.auth_utils import get_current_user  # JWT auth dependency
from utils.cloudinary_config import upload_image_to_cloudinary
from utils.pagination import get_pagination_params, create_paginated_response, PaginatedResponse
from utils.geocoding_helper import geocode_location_with_region
from constants import (
    EVENT_STATUS_PENDING,
    EVENT_STATUS_APPROVED,
    EVENT_STATUS_DELETED,
    MAX_IMAGES_PER_EVENT
)
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/event", tags=["event"])


# -------------------
# CREATE EVENT
# -------------------
@router.post("/add", response_model=EventResponse)
async def add_event(
        title: str = Form(...),
        description: str = Form(...),
        category_id: str = Form(...),
        date: str = Form(...),
        location: str = Form(...),
        impact_summary: str = Form(...),
        contact_email: str = Form(...),
        year: int = Form(...),
        severity: str = Form(...),
        region: str = Form(...),
        type: str = Form(...),
        source: Optional[str] = Form(None),
        is_featured: Optional[bool] = Form(False),
        images: List[UploadFile] = File([]),
        current_user: str = Depends(get_current_user)
) -> EventResponse:
    # Upload images to Cloudinary (max defined in constants)
    image_urls = []
    for image in images[:MAX_IMAGES_PER_EVENT]:
        try:
            # Read image data
            image_data = await image.read()

            # Upload to Cloudinary
            result = upload_image_to_cloudinary(
                image_data=image_data,
                folder="climate_events",
                public_id=f"{uuid.uuid4()}"
            )
            image_urls.append(result['secure_url'])
        except Exception as e:
            # Cloudinary upload failed - skip this image
            logger.warning(f"Cloudinary upload failed for {image.filename}: {e}")
            # Image is skipped - not added to image_urls 

    # Geocode location and validate coordinates against selected region
    # Region is highest priority - coordinates will be adjusted to fall within region
    lat = None
    lng = None
    try:
        lat, lng, was_adjusted = await geocode_location_with_region(location, region)
        if was_adjusted:
            logger.info(f"Coordinates adjusted for location '{location}' to match region '{region}'")
    except Exception as e:
        logger.warning(f"Could not geocode location '{location}': {e}. Using region center.")
        # Fallback to region center
        from config.region_mapping import REGION_ID, REGION_CENTERS
        # Map region ID to region name if needed (region might be ID like "100" or name like "Northern BC")
        region_name = None
        if region:
            # Check if region is an ID (numeric string) and map it to name
            if region.isdigit() and region in REGION_ID.values():
                # Find the region name for this ID
                region_name = next((k for k, v in REGION_ID.items() if v == region), region)
            elif region in REGION_CENTERS:
                # Region is already a name that exists in REGION_CENTERS
                region_name = region
            else:
                # Try direct lookup (in case region is already a name but needs exact match)
                region_name = region
        
        if region_name and region_name in REGION_CENTERS:
            region_center = REGION_CENTERS[region_name]
            lat = region_center["lat"]
            lng = region_center["lng"]

    event_doc = {
        "title": title,
        "description": description,
        "category_id": category_id,
        "date": datetime.fromisoformat(date),
        "uploaded_at": datetime.utcnow(),
        "uploaded_by": current_user,
        "uploaded_by_user": current_user,  # Keep for backward compatibility with frontend
        "location": location,
        "impact_summary": impact_summary,
        "contact_email": contact_email,
        "year": year,
        "severity": severity,
        "region": region,
        "type": type,
        "status": EVENT_STATUS_PENDING,
        "source": source,
        "is_featured": is_featured,
        "image_urls": image_urls,
        "lat": lat,
        "lng": lng,
    }

    result = await events_collection.insert_one(event_doc)

    # Fetch category name
    category = await categories_collection.find_one({"_id": ObjectId(category_id)})
    category_name = category["title"] if category else "Unknown"

    return EventResponse(
        event_id=str(result.inserted_id),
        category_name=category_name,
        **event_doc
    )


# -------------------
# GET ALL EVENTS FOR MAP (no pagination - returns all approved events by default, or all if status not specified)
# -------------------
@router.get("/all", response_model=List[EventResponse])
async def all_events_for_map(
        current_user: str = Depends(get_current_user),
        status: Optional[int] = Query(None, description="Event status (1=approved, 3=pending, 2=deleted). Omit to get all statuses.")
) -> List[EventResponse]:
    """Get all events for map display without pagination. Returns all events if status is not specified."""
    # Build match query - if status is specified, filter by it; otherwise return all
    match_query = {}
    if status is not None:
        match_query["status"] = status
    
    # Use aggregation pipeline to join categories (fixes N+1 query problem)
    pipeline = [
        {"$match": match_query},
        {
            "$lookup": {
                "from": "categories",
                "let": {"cat_id": {"$toObjectId": "$category_id"}},
                "pipeline": [
                    {"$match": {"$expr": {"$eq": ["$_id", "$$cat_id"]}}},
                    {"$project": {"title": 1}}
                ],
                "as": "category_info"
            }
        },
        {
            "$addFields": {
                "category_name": {
                    "$ifNull": [{"$arrayElemAt": ["$category_info.title", 0]}, "Unknown"]
                }
            }
        },
        {"$project": {"category_info": 0}},  # Remove the temporary lookup field
        {"$sort": {"date": -1}}  # Sort by event date (most recent first)
    ]
    
    events = []
    async for event in events_collection.aggregate(pipeline):
        event["event_id"] = str(event["_id"])
        events.append(EventResponse(**event))
    
    return events


# -------------------
# GET ALL EVENTS (with pagination)
# -------------------
@router.get("/", response_model=PaginatedResponse[EventResponse])
async def all_events(
        current_user: str = Depends(get_current_user),
        category_id: Optional[str] = Query(None),
        status: Optional[int] = Query(None),
        page: Optional[int] = Query(1, ge=1, description="Page number (1-indexed)"),
        page_size: Optional[int] = Query(20, ge=1, le=100, description="Number of items per page (max 100)")
) -> PaginatedResponse[EventResponse]:
    # Build match query
    match_query = {}
    if category_id:
        match_query["category_id"] = category_id
    if status is not None:
        match_query["status"] = status

    # Get pagination parameters
    skip, limit = get_pagination_params(page, page_size)

    # Count total documents matching the query
    total = await events_collection.count_documents(match_query)

    # Use aggregation pipeline to join categories (fixes N+1 query problem) with pagination
    pipeline = [
        {"$match": match_query},
        {
            "$lookup": {
                "from": "categories",
                "let": {"cat_id": {"$toObjectId": "$category_id"}},
                "pipeline": [
                    {"$match": {"$expr": {"$eq": ["$_id", "$$cat_id"]}}},
                    {"$project": {"title": 1}}
                ],
                "as": "category_info"
            }
        },
        {
            "$addFields": {
                "category_name": {
                    "$ifNull": [{"$arrayElemAt": ["$category_info.title", 0]}, "Unknown"]
                }
            }
        },
        {"$project": {"category_info": 0}},  # Remove the temporary lookup field
        {"$sort": {"uploaded_at": -1}},  # Sort by most recent first
        {"$skip": skip},
        {"$limit": limit}
    ]

    events = []
    async for event in events_collection.aggregate(pipeline):
        event["event_id"] = str(event["_id"])
        events.append(EventResponse(**event))
    
    return create_paginated_response(
        items=events,
        total=total,
        page=page or 1,
        page_size=page_size or 20
    )


# -------------------
# GET SINGLE EVENT
# -------------------
@router.get("/{event_id}", response_model=EventResponse)
async def get_event(event_id: str, current_user: str = Depends(get_current_user)) -> EventResponse:
    # Validate ObjectId format
    try:
        event_oid = ObjectId(event_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid event ID format")

    # Use aggregation pipeline to join category (fixes N+1 query problem)
    pipeline = [
        {"$match": {"_id": event_oid}},
        {
            "$lookup": {
                "from": "categories",
                "let": {"cat_id": {"$toObjectId": "$category_id"}},
                "pipeline": [
                    {"$match": {"$expr": {"$eq": ["$_id", "$$cat_id"]}}},
                    {"$project": {"title": 1}}
                ],
                "as": "category_info"
            }
        },
        {
            "$addFields": {
                "category_name": {
                    "$ifNull": [{"$arrayElemAt": ["$category_info.title", 0]}, "Unknown"]
                }
            }
        },
        {"$project": {"category_info": 0}}  # Remove the temporary lookup field
    ]

    event = await events_collection.aggregate(pipeline).to_list(length=1)
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    event = event[0]
    event["event_id"] = str(event["_id"])
    
    return EventResponse(**event)


# -------------------
# UPDATE EVENT
# -------------------
@router.post("/{event_id}", response_model=EventResponse)
async def update_event(
        event_id: str,
        title: str = Form(...),
        description: str = Form(...),
        category_id: str = Form(...),
        date: str = Form(...),
        location: str = Form(...),
        impact_summary: str = Form(...),
        contact_email: str = Form(...),
        year: int = Form(...),
        severity: str = Form(...),
        region: str = Form(...),
        type: str = Form(...),
        source: Optional[str] = Form(None),
        is_featured: Optional[bool] = Form(False),
        images: List[UploadFile] = File([]),
        current_user: str = Depends(get_current_user)
) -> EventResponse:
    event = await events_collection.find_one({"_id": ObjectId(event_id)})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Geocode location and validate coordinates against selected region
    # Region is highest priority - coordinates will be adjusted to fall within region
    lat = event.get("lat")
    lng = event.get("lng")
    
    # Re-geocode if location or region changed
    if location != event.get("location") or region != event.get("region"):
        try:
            lat, lng, was_adjusted = await geocode_location_with_region(location, region)
            if was_adjusted:
                logger.info(f"Coordinates adjusted for location '{location}' to match region '{region}'")
        except Exception as e:
            logger.warning(f"Could not geocode location '{location}': {e}. Using existing or region center.")
            # Fallback to region center if no existing coordinates
            if not lat or not lng:
                from config.region_mapping import REGION_ID, REGION_CENTERS
                # Map region ID to region name if needed
                region_name = None
                if region:
                    if region.isdigit() and region in REGION_ID.values():
                        region_name = next((k for k, v in REGION_ID.items() if v == region), region)
                    elif region in REGION_CENTERS:
                        region_name = region
                    else:
                        region_name = region
                
                if region_name and region_name in REGION_CENTERS:
                    region_center = REGION_CENTERS[region_name]
                    lat = region_center["lat"]
                    lng = region_center["lng"]

    # Get existing image URLs (preserve existing URLs - Cloudinary or legacy local URLs)
    image_urls = event.get("image_urls", [])

    # Upload new images to Cloudinary (max defined in constants)
    for image in images[:MAX_IMAGES_PER_EVENT]:
        if len(image_urls) >= MAX_IMAGES_PER_EVENT:
            break
        try:
            # Read image data
            image_data = await image.read()

            # Upload to Cloudinary
            result = upload_image_to_cloudinary(
                image_data=image_data,
                folder="climate_events",
                public_id=f"{uuid.uuid4()}"
            )
            image_urls.append(result['secure_url'])
        except Exception as e:
            # Cloudinary upload failed - skip this image
            logger.warning(f"Cloudinary upload failed for {image.filename}: {e}")
            # Image is skipped - not added to image_urls

    # Limit to MAX_IMAGES_PER_EVENT images total
    image_urls = image_urls[:MAX_IMAGES_PER_EVENT]

    updated_doc = {
        "title": title,
        "description": description,
        "category_id": category_id,
        "date": datetime.fromisoformat(date),
        "uploaded_by": current_user,
        "uploaded_by_user": current_user,  # Keep for backward compatibility with frontend
        "location": location,
        "impact_summary": impact_summary,
        "contact_email": contact_email,
        "year": year,
        "severity": severity,
        "region": region,
        "type": type,
        "source": source,
        "is_featured": is_featured,
        "status": event.get("status", EVENT_STATUS_PENDING),
        "image_urls": image_urls,
        "lat": lat,
        "lng": lng,
    }

    await events_collection.update_one({"_id": ObjectId(event_id)}, {"$set": updated_doc})

    category = await categories_collection.find_one({"_id": ObjectId(category_id)})
    category_name = category["title"] if category else "Unknown"

    return EventResponse(
        event_id=event_id,
        category_name=category_name,
        **updated_doc,
        uploaded_at=event.get("uploaded_at", datetime.utcnow())
    )


# -------------------
# DELETE (SOFT DELETE)
# -------------------
@router.delete("/{event_id}")
async def delete_event(event_id: str, current_user: str = Depends(get_current_user)) -> dict[str, str]:
    event = await events_collection.find_one({"_id": ObjectId(event_id)})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    await events_collection.update_one({"_id": ObjectId(event_id)}, {"$set": {"status": EVENT_STATUS_DELETED}})
    return {"message": "Event deactivated successfully"}


# -------------------
# APPROVE EVENT
# -------------------
@router.patch("/{event_id}/approve")
async def approve_event(event_id: str, current_user: str = Depends(get_current_user)) -> dict[str, str]:
    event = await events_collection.find_one({"_id": ObjectId(event_id)})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    await events_collection.update_one({"_id": ObjectId(event_id)}, {"$set": {"status": EVENT_STATUS_APPROVED}})
    return {"message": "Event approved successfully"}


# ---------------------------
# TOGGLE FEATURED STATUS
# ---------------------------
@router.patch("/{event_id}/feature")
async def toggle_featured(
    event_id: str,
    request: FeatureToggleRequest,
    current_user: str = Depends(get_current_user)
) -> dict[str, str]:
    event = await events_collection.find_one({"_id": ObjectId(event_id)})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    await events_collection.update_one(
        {"_id": ObjectId(event_id)},
        {"$set": {"is_featured": request.is_featured}}
    )
    return {"message": f"Event {'featured' if request.is_featured else 'unfeatured'} successfully"}

