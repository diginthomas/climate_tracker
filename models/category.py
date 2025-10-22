from pydantic import BaseModel


class Category(BaseModel):
    title: str
    description: str
    status:int =1 # 1 represent active

class CategoryResponse(BaseModel):
    category_id: str
    title: str
    description: str
    status: int
