from datetime import datetime

from pydantic import BaseModel, EmailStr


class Contact(BaseModel):
    name:str
    email:EmailStr
    subject:str
    message:str
    status:bool=False
    created_at:datetime
    updated_at:datetime
    is_deleted:bool=False


class ContactResponse(BaseModel):
    id:str
    name:str
    email:EmailStr
    subject:str
    message:str
    status:bool
    created_at: datetime
    updated_at: datetime
    is_deleted: bool