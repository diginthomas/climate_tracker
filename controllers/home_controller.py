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
    # Use aggregation pipeline with $lookup to join categories (fixes N+1 query problem)
    pipeline = [
        {"$match": {"is_featured": True, "status": 1}},
        {"$sample": {"size": 3}},  # return 3 random documents
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

    events_cursor = await events_collection.aggregate(pipeline).to_list(length=3)

    response = []
    for event in events_cursor:
        event["event_id"] = str(event["_id"])
        response.append(EventResponse(**event))

    return response
