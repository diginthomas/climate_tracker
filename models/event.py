from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List

class Event(BaseModel):
    title: str
    description: str
    category_id: str
    date: datetime
    uploaded_at: datetime
    uploaded_by: str
    source: Optional[str] = None
    is_featured: Optional[bool] = None
    status: int= 3 #pending
    image_urls: Optional[List[str]] = []

class EventResponse(BaseModel):
    event_id: str
    title: str
    description: str
    category_id: str
    category_name: str
    date: datetime
    uploaded_at: datetime
    uploaded_by: str
    uploaded_by_user :str
    source: Optional[str] = None
    is_featured: Optional[bool] = None
    status: int
    image_urls: Optional[List[str]] = []
