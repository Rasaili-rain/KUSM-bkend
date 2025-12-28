from fastapi import APIRouter, HTTPException, Depends, Request, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session
from ..models import MeterDB, MeterData, MeterDataDB
from ..database import get_db
from ..init_meter import init_meter, remove_meter

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

@router.post("/")
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
