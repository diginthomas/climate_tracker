from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Query
from bson import ObjectId
from datetime import datetime
import os, uuid
from typing import Optional, List

from database import events_collection, categories_collection
from models.event import Event, EventResponse
from auth_utils import get_current_user  # JWT auth dependency

router = APIRouter(prefix="/event", tags=["event"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

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
    source: Optional[str] = Form(None),
    is_featured: Optional[bool] = Form(False),
    images: List[UploadFile] = File([]),
    current_user: str = Depends(get_current_user)
):
    # Upload images (max 5)
    image_urls = []
    for image in images[:5]:
        filename = f"{uuid.uuid4()}_{image.filename}"
        path = os.path.join(UPLOAD_DIR, filename)
        with open(path, "wb") as f:
            f.write(await image.read())
        image_urls.append(f"/uploads/{filename}")

    event_doc = {
        "title": title,
        "description": description,
        "category_id": category_id,
        "date": datetime.fromisoformat(date),
        "uploaded_at": datetime.utcnow(),
        "uploaded_by": current_user,
        "uploaded_by_user": current_user,
        "location": location,
        "impact_summary": impact_summary,
        "contact_email": contact_email,
        "year": year,
        "status": 3,  # pending
        "source": source,
        "is_featured": is_featured,
        "image_urls": image_urls,
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
# GET ALL EVENTS
# -------------------
@router.get("/", response_model=List[EventResponse])
async def all_events(
    current_user: str = Depends(get_current_user),
    category_id: Optional[str] = Query(None),
    status: Optional[int] = Query(None)
):
    query = {}
    if category_id:
        query["category_id"] = category_id
    if status is not None:
        query["status"] = status

    events_cursor = events_collection.find(query)
    events = []
    async for event in events_cursor:
        category = await categories_collection.find_one({"_id": ObjectId(event["category_id"])})
        category_name = category["title"] if category else "Unknown"
        events.append(EventResponse(
            event_id=str(event["_id"]),
            category_name=category_name,
            **event
        ))
    return events

# -------------------
# GET SINGLE EVENT
# -------------------
@router.get("/{event_id}", response_model=EventResponse)
async def get_event(event_id: str, current_user: str = Depends(get_current_user)):
    event = await events_collection.find_one({"_id": ObjectId(event_id)})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    category = await categories_collection.find_one({"_id": ObjectId(event["category_id"])})
    category_name = category["title"] if category else "Unknown"

    return EventResponse(
        event_id=event_id,
        category_name=category_name,
        **event
    )

# -------------------
# UPDATE EVENT
# -------------------
@router.put("/{event_id}", response_model=EventResponse)
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
    source: Optional[str] = Form(None),
    is_featured: Optional[bool] = Form(False),
    images: List[UploadFile] = File([]),
    current_user: str = Depends(get_current_user)
):
    event = await events_collection.find_one({"_id": ObjectId(event_id)})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    image_urls = event.get("image_urls", [])
    for image in images[:5]:
        filename = f"{uuid.uuid4()}_{image.filename}"
        path = os.path.join(UPLOAD_DIR, filename)
        with open(path, "wb") as f:
            f.write(await image.read())
        image_urls.append(f"/uploads/{filename}")
    image_urls = image_urls[:5]

    updated_doc = {
        "title": title,
        "description": description,
        "category_id": category_id,
        "date": datetime.fromisoformat(date),
        "uploaded_by": current_user,
        "uploaded_by_user": current_user,
        "location": location,
        "impact_summary": impact_summary,
        "contact_email": contact_email,
        "year": year,
        "source": source,
        "is_featured": is_featured,
        "status": event.get("status", 3),
        "image_urls": image_urls
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
async def delete_event(event_id: str, current_user: str = Depends(get_current_user)):
    event = await events_collection.find_one({"_id": ObjectId(event_id)})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    await events_collection.update_one({"_id": ObjectId(event_id)}, {"$set": {"status": 2}})
    return {"message": "Event deactivated successfully"}

# -------------------
# APPROVE EVENT
# -------------------
@router.patch("/{event_id}/approve")
async def approve_event(event_id: str, current_user: str = Depends(get_current_user)):
    event = await events_collection.find_one({"_id": ObjectId(event_id)})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    await events_collection.update_one({"_id": ObjectId(event_id)}, {"$set": {"status": 1}})
    return {"message": "Event approved successfully"}

# ---------------------------
# TOGGLE FEATURED STATUS
# ---------------------------
@router.patch("/{event_id}/feature")
async def toggle_featured(
    event_id: str,
    is_featured: bool = True,
    current_user: str = Depends(get_current_user)
):
    event = await events_collection.find_one({"_id": ObjectId(event_id)})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    await events_collection.update_one(
        {"_id": ObjectId(event_id)},
        {"$set": {"is_featured": is_featured}}
    )
    return {"message": f"Event {'featured' if is_featured else 'unfeatured'} successfully"}
