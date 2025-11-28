from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .routes import oauth, users
from .database import db_engine
from .models import Base

# Create database tables
Base.metadata.create_all(bind=db_engine)

app = FastAPI(title="KU Smart Meeter", version="1.0.0")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(oauth.router)
app.include_router(users.router)

@app.get("/")
async def root():
    return {"message": "KU Smart Meter API is running", "status": "healthy"}