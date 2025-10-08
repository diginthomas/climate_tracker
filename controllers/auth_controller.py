from fastapi import APIRouter

router = APIRouter()

@router.get("/login")
def login():
    return {"THIS IS A LOGIN"}

@router.get("/logout")
def logout():
    return {"THIS IS A LOGOUT"}

@router.get("register")
def register():
    return {"THIS IS A REGISTER"}