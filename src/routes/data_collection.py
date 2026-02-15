from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timedelta
from typing import Optional
import asyncio
from sqlalchemy.orm import Session
from zoneinfo import ZoneInfo

from src.api import iammeter
from src.routes.auth.auth_utils import require_admin, get_current_user
from src.models import User, DataCollectionScheduleDB
from src.database import get_db

router = APIRouter(prefix="/data-collection", tags=["Data Collection"])

NEPAL_TZ = ZoneInfo("Asia/Kathmandu")


def get_nepal_time() -> datetime:
    return datetime.now(NEPAL_TZ)


class ScheduleInput(BaseModel):
    start_datetime: str = Field(..., example="2025-02-15T08:00")
    end_datetime: str = Field(..., example="2025-02-15T18:00")
    interval_minutes: int = Field(..., ge=1, le=1440, example=5)

    @field_validator("start_datetime", "end_datetime")
    @classmethod
    def validate_datetime_format(cls, v):
        try:
            # Handle various ISO format inputs
            # "2025-02-15T14:30" or "2025-02-15T14:30:00"
            if "T" in v:
                # Add seconds if missing
                if v.count(":") == 1:  # Only has hours and minutes
                    v = v + ":00"
                # Try parsing
                datetime.fromisoformat(v.replace("Z", "+00:00"))
            else:
                raise ValueError("DateTime must include both date and time")
            return v
        except ValueError as e:
            raise ValueError(
                f"DateTime must be in ISO format (YYYY-MM-DDTHH:MM or YYYY-MM-DDTHH:MM:SS): {e}"
            )

    @field_validator("end_datetime")
    @classmethod
    def validate_end_after_start(cls, v, info):
        if info.data.get("start_datetime"):
            start = datetime.fromisoformat(
                info.data["start_datetime"].replace("Z", "+00:00")
            )
            end = datetime.fromisoformat(v.replace("Z", "+00:00"))
            if end <= start:
                raise ValueError("end_datetime must be after start_datetime")
        return v


# Global state
class CollectionState:
    def __init__(self):
        self.is_running = False
        self.task: Optional[asyncio.Task] = None
        self.schedule: Optional[ScheduleInput] = None
        self.last_run: Optional[datetime] = None
        self.next_run: Optional[datetime] = None

    def is_within_schedule(self) -> bool:
        if not self.schedule:
            return True
        now = get_nepal_time()
        # Parse the datetime strings (they're in Nepal time)
        start = datetime.fromisoformat(
            self.schedule.start_datetime.replace("Z", "+00:00")
        )
        end = datetime.fromisoformat(self.schedule.end_datetime.replace("Z", "+00:00"))

        # Ensure timezone awareness
        if start.tzinfo is None:
            start = start.replace(tzinfo=NEPAL_TZ)
        if end.tzinfo is None:
            end = end.replace(tzinfo=NEPAL_TZ)

        return start <= now <= end

    def calculate_next_run(self) -> datetime:
        if not self.schedule:
            # No schedule, just add interval to now
            interval = 5 * 60  # default 5 minutes
            return get_nepal_time() + timedelta(seconds=interval)

        interval = self.schedule.interval_minutes * 60
        now = get_nepal_time()
        next_time = now + timedelta(seconds=interval)

        # Parse schedule datetimes
        start_dt = datetime.fromisoformat(
            self.schedule.start_datetime.replace("Z", "+00:00")
        )
        end_dt = datetime.fromisoformat(
            self.schedule.end_datetime.replace("Z", "+00:00")
        )

        # Ensure timezone awareness
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=NEPAL_TZ)
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=NEPAL_TZ)

        # If next run is after end datetime, we're done with this schedule
        if next_time > end_dt:
            # Schedule has ended, return end time
            return end_dt

        # If we're currently before start time, schedule for start time
        if now < start_dt:
            return start_dt

        return next_time


state = CollectionState()


async def collection_task():
    """Background task that collects data on schedule"""
    while state.is_running:
        try:
            if state.is_within_schedule():
                print(f"[{get_nepal_time()}] Collecting data...")
                await asyncio.to_thread(iammeter.store_all_meter_data)
                state.last_run = get_nepal_time()
                print(f"[{get_nepal_time()}] Collection complete")
            else:
                print(f"[{get_nepal_time()}] Outside schedule window, skipping")

        except Exception as e:
            print(f"Collection error: {e}")

        # Calculate next run time
        interval = state.schedule.interval_minutes * 60 if state.schedule else 5 * 60
        state.next_run = get_nepal_time() + timedelta(seconds=interval)

        # Adjust next_run if outside schedule window
        if state.schedule:
            now = get_nepal_time()
            end_dt = datetime.fromisoformat(
                state.schedule.end_datetime.replace("Z", "+00:00")
            )
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=NEPAL_TZ)

            # If we've passed the end datetime, stop the collection
            if now > end_dt:
                print(f"[{get_nepal_time()}] Schedule ended, stopping collection")
                state.is_running = False
                break

            # If next run would be after end time, schedule for end time
            if state.next_run > end_dt:
                state.next_run = end_dt

        await asyncio.sleep(interval)


@router.get("/current-time")
async def get_current_time(current_user: User = Depends(get_current_user)):
    """Get current Nepal time"""
    nepal_time = get_nepal_time()
    return {
        "current_time": nepal_time.strftime("%H:%M"),
        "current_datetime": nepal_time.isoformat(),
        "timezone": "Asia/Kathmandu",
    }


@router.get("/status")
async def get_status(current_user: User = Depends(get_current_user)):
    """Get current collection status"""
    return {
        "is_running": state.is_running,
        "schedule": {
            "start_datetime": state.schedule.start_datetime,
            "end_datetime": state.schedule.end_datetime,
            "interval_minutes": state.schedule.interval_minutes,
        }
        if state.schedule
        else None,
        "last_run": state.last_run.isoformat() if state.last_run else None,
        "next_run": state.next_run.isoformat() if state.next_run else None,
        "is_within_schedule": state.is_within_schedule() if state.is_running else None,
        "current_nepal_time": get_nepal_time().isoformat(),
    }


@router.post("/start")
async def start_collection(
    schedule: ScheduleInput,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Start data collection with schedule"""
    if state.is_running:
        raise HTTPException(status_code=400, detail="Already running")

    # Save to database
    db.query(DataCollectionScheduleDB).update({"is_active": False})
    new_schedule = DataCollectionScheduleDB(
        start_datetime=schedule.start_datetime,
        end_datetime=schedule.end_datetime,
        interval_minutes=schedule.interval_minutes,
        is_active=True,
        created_by=current_user.id,
        created_at=get_nepal_time(),
    )
    db.add(new_schedule)
    db.commit()

    # Start collection
    state.is_running = True
    state.schedule = schedule
    state.next_run = state.calculate_next_run()
    state.task = asyncio.create_task(collection_task())

    return {"message": "Collection started", "is_running": True}


@router.post("/stop")
async def stop_collection(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Stop data collection"""
    if not state.is_running:
        raise HTTPException(status_code=400, detail="Not running")

    state.is_running = False
    if state.task:
        state.task.cancel()
        try:
            await state.task
        except asyncio.CancelledError:
            pass
        state.task = None

    # Mark schedule as inactive in DB
    db.query(DataCollectionScheduleDB).filter(
        DataCollectionScheduleDB.is_active
    ).update({"is_active": False})
    db.commit()

    # Clear next run when stopped
    state.next_run = None

    return {"message": "Collection stopped", "is_running": False}


@router.post("/run-now")
async def run_now(current_user: User = Depends(require_admin)):
    """Manually trigger data collection once"""
    try:
        await asyncio.to_thread(iammeter.store_all_meter_data)
        state.last_run = get_nepal_time()
        return {
            "message": "Collection executed",
            "timestamp": get_nepal_time().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
