from pydantic import BaseModel
from typing import Optional


class Region(BaseModel):
    name: str
    description: Optional[str] = None
    status: int = 1  # 1 = Active, 2 = Deactivated
    lat:str
    lng:str


class RegionResponse(BaseModel):
    region_id: str
    name: str
    description: Optional[str] = None
    status: int
    lat:str
    lng:str
