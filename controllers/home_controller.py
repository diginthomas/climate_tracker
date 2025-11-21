from typing import List

from fastapi import APIRouter

from database import events_collection
from models.event import EventResponse

router = APIRouter()

@router.get("/")
def read_root():
    return {"Hello": "Wj"}



@router.get("/featured", response_model=List[EventResponse])
async def featured_events():
    pipeline = [
        {"$match": {"is_featured": True, "status": 1}},
        {"$sample": {"size": 3}}  # return 3 random documents
    ]

    events_cursor = await events_collection.aggregate(pipeline).to_list(length=3)

    response = []
    for event in events_cursor:
        response.append(EventResponse(
            event_id=str(event["_id"]),
            title=event["title"],
            description=event["description"],
            category_id=event["category_id"],
            category_name=event.get("category_name", ""),
            date=event["date"],
            uploaded_at=event["uploaded_at"],
            uploaded_by=event["uploaded_by"],
            uploaded_by_user=event["uploaded_by_user"],
            location=event["location"],
            impact_summary=event["impact_summary"],
            contact_email=event["contact_email"],
            year=event["year"],
            severity=event["severity"],
            region=event.get("region"),
            type=event.get("type"),
            source=event.get("source"),
            is_featured=event.get("is_featured"),
            status=event["status"],
            image_urls=event.get("image_urls", [])
        ))

    return response
