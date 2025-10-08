from fastapi import APIRouter

router = APIRouter()

@router.get("/g")
def read_root():
    return {"Hello": "Wj"}
