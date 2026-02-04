from fastapi import APIRouter, HTTPException
import asyncio
from typing import Optional
from src.api import iammeter

router = APIRouter(prefix="/data-collection", tags=["Data Collection"])

# Global state for data collection
class DataCollectionState:
    def __init__(self):
        self.is_running = False
        self.repeat_interval = 5 * 60  # 5 minutes
        self.task: Optional[asyncio.Task] = None
    
    def start(self):
        self.is_running = True
    
    def stop(self):
        self.is_running = False

data_collection_state = DataCollectionState()


async def data_collection_task():
    
    while data_collection_state.is_running:
        try:
            await asyncio.to_thread(iammeter.store_all_meter_data)
        except Exception as e:
            print(f"Error in data collection: {e}")
        await asyncio.sleep(data_collection_state.repeat_interval)  #


@router.get("/status")
async def get_data_collection_status():
    return {
        "is_running": data_collection_state.is_running,
        "collection_interval_seconds": data_collection_state.repeat_interval
    }


@router.post("/start")
async def start_data_collection():
    if data_collection_state.is_running:
        raise HTTPException(status_code=400, detail="Data collection is already running")
    
    if data_collection_state.task and not data_collection_state.task.done():
        raise HTTPException(status_code=400, detail="Data collection task already exists")
    
    data_collection_state.start()
    data_collection_state.task = asyncio.create_task(data_collection_task())
    
    return {
        "message": "Data collection started successfully",
        "is_running": True
    }


@router.post("/stop")
async def stop_data_collection():
    if not data_collection_state.is_running:
        raise HTTPException(status_code=400, detail="Data collection is not running")
    
    data_collection_state.stop()
    
    if data_collection_state.task and not data_collection_state.task.done():
        data_collection_state.task.cancel()
        try:
            await data_collection_state.task
        except asyncio.CancelledError:
            pass
        data_collection_state.task = None
    
    return {
        "message": "Data collection stopped successfully",
        "is_running": False
    }