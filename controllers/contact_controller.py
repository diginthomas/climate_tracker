from http.client import HTTPException
from datetime import datetime
from bson import ObjectId
from fastapi import APIRouter, Body

from database import contacts_collection
from models.contact import ContactResponse, Contact

router = APIRouter(prefix="/contact", tags=["Contact"])


@router.post("/", response_model=ContactResponse)
async def create_contact(contact: Contact):
    new_contact = contact.dict()
    new_contact["created_at"] = datetime.utcnow()
    new_contact["updated_at"] = datetime.utcnow()
    new_contact["is_deleted"] = False

    result = await contacts_collection.insert_one(new_contact)

    return ContactResponse(
        id=str(result.inserted_id),
        **new_contact
    )


@router.get("/", response_model=list[ContactResponse])
async def get_all_contacts():
    contacts = []
    async for contact in contacts_collection.find({"is_deleted": False}):
        contacts.append(ContactResponse(
            id=str(contact["_id"]),
            name=contact["name"],
            email=contact["email"],
            subject=contact["subject"],
            message=contact["message"],
            status=contact["status"],
            created_at=contact["created_at"],
            updated_at=contact["updated_at"],
            is_deleted=contact["is_deleted"]
        ))
    return contacts


@router.get("/{contact_id}", response_model=ContactResponse)
async def get_single_contact(contact_id: str):
    contact = await contacts_collection.find_one({"_id": ObjectId(contact_id)})

    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    return ContactResponse(
        id=str(contact["_id"]),
        name=contact["name"],
        email=contact["email"],
        subject=contact["subject"],
        message=contact["message"],
        status=contact["status"],
        created_at=contact["created_at"],
        updated_at=contact["updated_at"],
        is_deleted=contact["is_deleted"]
    )


@router.put("/{contact_id}", response_model=ContactResponse)
async def update_contact_status(
    contact_id: str,
    data: dict = Body(...)
):
    status = data.get("status")

    updated = await contacts_collection.find_one_and_update(
        {"_id": ObjectId(contact_id)},
        {"$set": {"status": status, "updated_at": datetime.utcnow()}},
        return_document=True
    )

    if not updated:
        raise HTTPException(status_code=404, detail="Contact not found")

    return ContactResponse(
        id=str(updated["_id"]),
        name=updated["name"],
        email=updated["email"],
        subject=updated["subject"],
        message=updated["message"],
        status=updated["status"],
        created_at=updated["created_at"],
        updated_at=updated["updated_at"],
        is_deleted=updated["is_deleted"]
    )


@router.delete("/{contact_id}")
async def delete_contact(contact_id: str):
    deleted = await contacts_collection.find_one_and_update(
        {"_id": ObjectId(contact_id)},
        {"$set": {"is_deleted": True, "updated_at": datetime.utcnow()}}
    )

    if not deleted:
        raise HTTPException(status_code=404, detail="Contact not found")

    return {"message": "Contact deleted successfully"}
