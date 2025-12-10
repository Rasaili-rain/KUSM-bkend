from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio

from .routes import meter, oauth, users
from .database import db_engine
from .models import Base
from .api import iammeter
from .init_meter import init_meter

# Create database tables
Base.metadata.create_all(bind=db_engine)

# Creating entries in db for existing meters
init_meter()


async def data_collection():
    while True:
        try:
            await asyncio.to_thread(iammeter.store_all_meter_data)
        except Exception as e:
            print(f"Error: {e}")
        await asyncio.sleep(300)


@asynccontextmanager
async def lifespan(app: FastAPI):
 
    task = asyncio.create_task(data_collection())
    try:
        yield  
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="KU Smart Meeter",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],  # when in prod use the fend url
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(oauth.router)
app.include_router(users.router)
app.include_router(meter.router)


@app.get("/")
async def root():
    return {"message": "KU Smart Meter API is running", "status": "healthy"}
