from fastapi import APIRouter, HTTPException, Depends, Request, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session
from ..models import MeterDB, MeterData, MeterDataDB
from ..database import get_db
from ..init_meter import init_meter, remove_meter
from ..api.iammeter import get_meter_id_by_name
from datetime import datetime, date, time

router = APIRouter(prefix="/meter", tags=["meter"])

@router.get("/")
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

# @router.get("/{meter_sn}")
# def get_meter_data(meter_sn: str):
#     # TODO : @imp
#     # stash these things in the db
#     result = fetch_meter_data(meter_sn)

#     if result is None:
#         raise HTTPException(
#             status_code=500,
#             detail="Failed to fetch meter data"
#         )

#     return {
#         "success": True,
#         "data": result
#     }

@router.get("/{meter_id}/latest", response_model=MeterData)
def get_latest_meter_data(
    meter_id: int,
    db: Session = Depends(get_db)
):
    data = (
        db.query(MeterDataDB)
        .filter(MeterDataDB.meter_id == meter_id)
        .order_by(desc(MeterDataDB.timestamp))
        .first()
    )

    if not data:
        raise HTTPException(status_code=404, detail="No data found for this meter")

    return data

@router.get("/todaysdata/{meter_name}")
def get_todays_data(meter_name: str, db: Session = Depends(get_db)):
    todays_date = date.today()
    start = datetime.combine(todays_date, time.min)
    end = datetime.combine(todays_date, time.max)
    meter_id = get_meter_id_by_name(meter_name)
    todays_data = (
        db.query(MeterDataDB)
        .filter(MeterDataDB.meter_id == meter_id, MeterDataDB.timestamp.between(start, end))
        .all())
    if not todays_data:
        raise HTTPException(status_code=404, detail="No Data for Today")
    return {
        "success": True,
        "meter_name": meter_name,
        "data": todays_data
      }


@router.get("/databydate")
def get_data_by_date_range(
    meter_name: str = Query(..., description="Meter name"),
    from_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    to_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    if from_date > to_date:
        raise HTTPException(
            status_code=400,
            detail="from_date cannot be later than to_date"
        )

    start = datetime.combine(from_date, time.min)
    end = datetime.combine(to_date, time.max)

    meter_id = get_meter_id_by_name(meter_name)
    if not meter_id:
        raise HTTPException(
            status_code=404,
            detail="Meter not found"
        )

    data = (
        db.query(MeterDataDB)
        .filter(
            MeterDataDB.meter_id == meter_id,
            MeterDataDB.timestamp.between(start, end)
        )
        .all()
    )

    if not data:
        return {
            "success": False,
            "message": "No data found for the given date range",
        }

    return {
        "success": True,
        "meter_name": meter_name,
        "from_date": from_date,
        "to_date": to_date,
        "count": len(data),
        "data": data
    }

@router.post("/addmeter")
async def add_meter(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    name = data.get("name")
    sn = data.get("sn")

    if not name or not sn:
        raise HTTPException(status_code=400, detail = "Missing 'name' or 'sn'")
    
    try: 
        added = init_meter(db, meters=[{"name": name, "sn": sn}])
        return added[0]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.delete("/{sn}")
def delete_meter(sn: str, force: bool = Query(default = False), db: Session = Depends(get_db)):
    try:
        removed = remove_meter(db,sn,force=force)
        return {"message": f"Meter '{removed.name}' removed successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
