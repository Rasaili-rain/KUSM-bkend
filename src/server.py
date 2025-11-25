from fastapi import FastAPI
from src.hello_world import router as hello_router

app = FastAPI(title="KUSM Backend API")

@app.get("/")
def read_root():
    return {"message": "Welcome to the KUSM-backend API! Running with FastAPI."}

app.include_router(hello_router)
