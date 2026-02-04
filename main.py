#!/usr/bin/env python

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio

from src.scheduler import scheduler 
from src.routes import meter, prediction, analysis, billing, data_collection, meter_status
from src.database import db_engine, get_db
from src.models import Base
from src.init_meter import init_meter
from src.ml_model import power_prediction_service

# Create database tables
# tun only when db changes
# Base.metadata.create_all(bind=db_engine)

@asynccontextmanager
async def lifespan(app: FastAPI):

    # db = next(get_db())
    # try:
    #     init_meter(db)
    # finally:
    #     db.close()

    # Load ML model on startup
    try:
        power_prediction_service.load_model()
        print("ML prediction model loaded successfully")
    except FileNotFoundError:
        print("ML model not found. Train a model using /api/prediction/train endpoint")
    except Exception as e:
        print(f"Failed to load ML model: {e}")
    
    
    # Start scheduler
    scheduler.start()
    # Data collection starts as OFF by default
    # Will be controlled via API endpoint
    try:
        yield
    finally:
        print("Shutting down...")
        
        # Stop data collection task
        if data_collection.data_collection_state.task:
            data_collection.data_collection_state.stop()
            if not data_collection.data_collection_state.task.done():
                data_collection.data_collection_state.task.cancel()
                try:
                    await asyncio.wait_for(
                        data_collection.data_collection_state.task, 
                        timeout=5.0
                    )
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass
        
        # Shutdown scheduler
        try:
            scheduler.shutdown(wait=False)
        except Exception as e:
            print(f"Error shutting down scheduler: {e}")
        
        print("Shutdown complete")


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
app.include_router(meter.router)
app.include_router(analysis.router)
app.include_router(billing.router)
app.include_router(data_collection.router)
app.include_router(prediction.router)
app.include_router(meter_status.router)




@app.get("/")
async def root():
    return {"message": "KU Smart Meter API is running", "status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000, 
        reload=True
    )
    