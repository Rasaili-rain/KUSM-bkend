from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from ..models import MeterDB
from ..database import get_db
from ..api.iammeter import fetch_meter_data

router = APIRouter(prefix="/meter", tags=["meter"])

@router.get("")
def get_all_meters(db: Session = Depends(get_db)):
    meters = db.query(MeterDB).all()

    return {
        "success": True,
        "count": len(meters),
        "data": [
            {
                "meter_id": m.meter_id,
                "name": m.name,
                "sn": m.sn	
            }
            for m in meters
        ]
    }

@router.get("/{meter_sn}")
def get_meter_data(meter_sn: str):
    # TODO : @imp
    # stash these things in the db
    result = fetch_meter_data(meter_sn)

    if result is None:
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch meter data"
        )

    return {
        "success": True,
        "data": result
    }
