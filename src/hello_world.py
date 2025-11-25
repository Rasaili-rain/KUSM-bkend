from fastapi import APIRouter

router = APIRouter()

@router.get("/hello_world")
def hello_world():
    return {"message": "Hello, world!"}
