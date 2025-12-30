from fastapi import APIRouter, HTTPException, Depends, Request, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session
from ..models import CurrentDB, EnergyDB, MeterDB, PowerDB, VoltageDB
from ..database import get_db
from ..init_meter import init_meter, remove_meter
from ..api.iammeter import get_meter_id_by_name
from ..utils.response_format import convert_format
from datetime import datetime, date, time
from ..api.iammeter import add_iammeter_station

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

@router.get("/{meter_id}/latest")
def get_latest_meter_data(
    meter_id: int,
    db: Session = Depends(get_db)
):
    row = (
        db.query(
            CurrentDB,
            VoltageDB,
            PowerDB,
            EnergyDB
        )
        .join(
            VoltageDB,
            (VoltageDB.meter_id == CurrentDB.meter_id) &
            (VoltageDB.timestamp == CurrentDB.timestamp)
        )
        .join(
            PowerDB,
            (PowerDB.meter_id == CurrentDB.meter_id) &
            (PowerDB.timestamp == CurrentDB.timestamp)
        )
        .join(
            EnergyDB,
            (EnergyDB.meter_id == CurrentDB.meter_id) &
            (EnergyDB.timestamp == CurrentDB.timestamp)
        )
        .filter(CurrentDB.meter_id == meter_id)
        .order_by(desc(CurrentDB.timestamp))
        .first()
    )

    if not row:
        raise HTTPException(status_code=404, detail="No data found for this meter")

    c, v, p, e = row

    return convert_format(c, v, p, e)

@router.get("/todaysdata/{meter_name}")
def get_todays_data(meter_name: str, db: Session = Depends(get_db)):
    meter_id = get_meter_id_by_name(meter_name)
    if not meter_id:
        raise HTTPException(status_code=404, detail="Meter not found")

    today = date.today()
    start = datetime.combine(today, time.min)
    end = datetime.combine(today, time.max)

    rows = (
        db.query(
            CurrentDB,
            VoltageDB,
            PowerDB,
            EnergyDB
        )
        .join(
            VoltageDB,
            (VoltageDB.meter_id == CurrentDB.meter_id) &
            (VoltageDB.timestamp == CurrentDB.timestamp)
        )
        .join(
            PowerDB,
            (PowerDB.meter_id == CurrentDB.meter_id) &
            (PowerDB.timestamp == CurrentDB.timestamp)
        )
        .join(
            EnergyDB,
            (EnergyDB.meter_id == CurrentDB.meter_id) &
            (EnergyDB.timestamp == CurrentDB.timestamp)
        )
        .filter(
            CurrentDB.meter_id == meter_id,
            CurrentDB.timestamp.between(start, end)
        )
        .order_by(CurrentDB.timestamp)
        .all()
    )

    if not rows:
        raise HTTPException(status_code=404, detail="No Data for Today")

    data = []
    for c, v, p, e in rows:
        data.append(convert_format(c, v, p, e))

    return {
        "success": True,
        "meter_name": meter_name,
        "count": len(data),
        "data": data
    }


@router.get("/databydate")
def get_data_by_date_range(
    meter_name: str = Query(...),
    from_date: date = Query(...),
    to_date: date = Query(...),
    db: Session = Depends(get_db)
):
    if from_date > to_date:
        raise HTTPException(
            status_code=400,
            detail="from_date cannot be later than to_date"
        )

    meter_id = get_meter_id_by_name(meter_name)
    if not meter_id:
        raise HTTPException(status_code=404, detail="Meter not found")

    start = datetime.combine(from_date, time.min)
    end = datetime.combine(to_date, time.max)

    rows = (
        db.query(
            CurrentDB,
            VoltageDB,
            PowerDB,
            EnergyDB
        )
        .join(
            VoltageDB,
            (VoltageDB.meter_id == CurrentDB.meter_id) &
            (VoltageDB.timestamp == CurrentDB.timestamp)
        )
        .join(
            PowerDB,
            (PowerDB.meter_id == CurrentDB.meter_id) &
            (PowerDB.timestamp == CurrentDB.timestamp)
        )
        .join(
            EnergyDB,
            (EnergyDB.meter_id == CurrentDB.meter_id) &
            (EnergyDB.timestamp == CurrentDB.timestamp)
        )
        .filter(
            CurrentDB.meter_id == meter_id,
            CurrentDB.timestamp.between(start, end)
        )
        .order_by(CurrentDB.timestamp)
        .all()
    )

    if not rows:
        return {
            "success": False,
            "message": "No data found for the given date range"
        }

    data = []
    for c, v, p, e in rows:
        data.append(convert_format(c, v, p, e))

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
    payload = await request.json()

    payload.setdefault("CountryId", "44")
    payload.setdefault("TimeZone", "5.75")
    payload.setdefault("TimeZoneName", "(GMT +05:45) Kathmandu")
    payload.setdefault("Province", "")
    payload.setdefault("City", "")
    payload.setdefault("Address", "")
    payload.setdefault("Position", "27.619399267478876, 85.5388709190866")
    payload.setdefault("DZPriceUnit", "NPR")

    if "Name" not in payload or "sn" not in payload:
        raise HTTPException(
            status_code= 422, 
            detail="Missing required fields: Name or sn"
        )

    result = add_iammeter_station(payload)

    if result is None:
        raise HTTPException(
            status_code=502, 
            detail="Failed to create station in IAMMETER"
        )

    if not result.get("successful", True):
        raise HTTPException(
            status_code=502, 
            detail=f"IAMMETER API error: {result.get('message', 'Unknown error')}"
        )

    return {
        "success": True, 
        "data": result
    }
    
@router.delete("/{sn}")
def delete_meter(sn: str, force: bool = Query(default = False), db: Session = Depends(get_db)):
    try:
        removed = remove_meter(db,sn,force=force)
        return {
            "success": True, "message": f"Meter '{removed.name}' removed successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Cannot delete meter : {e}")