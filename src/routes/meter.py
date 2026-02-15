from typing import List
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from ..models import CurrentDB, EnergyDB, MeterDB, PowerDB, VoltageDB
from ..database import get_db
from ..api.iammeter import get_meter_id_by_name
from datetime import datetime, date, time


# Pydantic models for request validation
class MeterLocationUpdate(BaseModel):
    x: float = Field(
        ..., ge=0, le=100, description="X coordinate as percentage (0-100)"
    )
    y: float = Field(
        ..., ge=0, le=100, description="Y coordinate as percentage (0-100)"
    )


class MeterLocationItem(BaseModel):
    meter_id: int
    x: float = Field(..., ge=0, le=100)
    y: float = Field(..., ge=0, le=100)


class BulkLocationUpdate(BaseModel):
    locations: List[MeterLocationItem]


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
                "sn": m.sn,
                "x": m.x if hasattr(m, "x") else None,
                "y": m.y if hasattr(m, "y") else None,
            }
            for m in meters
        ],
    }


@router.get("/{meter_id}/latest")
def get_latest_meter_data(meter_id: int, db: Session = Depends(get_db)):
    row = (
        db.query(CurrentDB, VoltageDB, PowerDB, EnergyDB)
        .join(
            VoltageDB,
            (VoltageDB.meter_id == CurrentDB.meter_id)
            & (VoltageDB.timestamp == CurrentDB.timestamp),
        )
        .join(
            PowerDB,
            (PowerDB.meter_id == CurrentDB.meter_id)
            & (PowerDB.timestamp == CurrentDB.timestamp),
        )
        .join(
            EnergyDB,
            (EnergyDB.meter_id == CurrentDB.meter_id)
            & (EnergyDB.timestamp == CurrentDB.timestamp),
        )
        .filter(CurrentDB.meter_id == meter_id)
        .order_by(desc(CurrentDB.timestamp))
        .first()
    )

    if not row:
        raise HTTPException(status_code=404, detail="No data found for this meter")

    c, v, p, e = row

    return _convert_format(c, v, p, e)


@router.get("/todaysdata/{meter_name}")
def get_todays_data(meter_name: str, db: Session = Depends(get_db)):
    meter_id = get_meter_id_by_name(meter_name)
    if not meter_id:
        raise HTTPException(status_code=404, detail="Meter not found")

    today = date.today()
    start = datetime.combine(today, time.min)
    end = datetime.combine(today, time.max)
    try:
        rows = (
            db.query(CurrentDB, VoltageDB, PowerDB, EnergyDB)
            .join(
                VoltageDB,
                (VoltageDB.meter_id == CurrentDB.meter_id)
                & (VoltageDB.timestamp == CurrentDB.timestamp),
            )
            .join(
                PowerDB,
                (PowerDB.meter_id == CurrentDB.meter_id)
                & (PowerDB.timestamp == CurrentDB.timestamp),
            )
            .join(
                EnergyDB,
                (EnergyDB.meter_id == CurrentDB.meter_id)
                & (EnergyDB.timestamp == CurrentDB.timestamp),
            )
            .filter(
                CurrentDB.meter_id == meter_id, CurrentDB.timestamp.between(start, end)
            )
            .order_by(CurrentDB.timestamp)
            .all()
        )

        if not rows:
            raise HTTPException(status_code=404, detail="No Data for Today")

        data = []
        for c, v, p, e in rows:
            data.append(_convert_format(c, v, p, e))

        return {
            "success": True,
            "meter_name": meter_name,
            "count": len(data),
            "data": data,
        }
    except SQLAlchemyError as e:
        db.rollback()
        raise


@router.get("/databydate")
def get_data_by_date_range(
    meter_name: str = Query(...),
    from_date: date = Query(...),
    to_date: date = Query(...),
    db: Session = Depends(get_db),
):
    if from_date > to_date:
        raise HTTPException(
            status_code=400, detail="from_date cannot be later than to_date"
        )

    meter_id = get_meter_id_by_name(db, meter_name)
    if not meter_id:
        raise HTTPException(status_code=404, detail="Meter not found")

    start = datetime.combine(from_date, time.min)
    end = datetime.combine(to_date, time.max)
    try:
        rows = (
            db.query(CurrentDB, VoltageDB, PowerDB, EnergyDB)
            .join(
                VoltageDB,
                (VoltageDB.meter_id == CurrentDB.meter_id)
                & (VoltageDB.timestamp == CurrentDB.timestamp),
            )
            .join(
                PowerDB,
                (PowerDB.meter_id == CurrentDB.meter_id)
                & (PowerDB.timestamp == CurrentDB.timestamp),
            )
            .join(
                EnergyDB,
                (EnergyDB.meter_id == CurrentDB.meter_id)
                & (EnergyDB.timestamp == CurrentDB.timestamp),
            )
            .filter(
                CurrentDB.meter_id == meter_id, CurrentDB.timestamp.between(start, end)
            )
            .distinct(CurrentDB.timestamp)
            .order_by(CurrentDB.timestamp)
            .all()
        )

        if not rows:
            return {
                "success": False,
                "message": "No data found for the given date range",
            }

        data = []
        for c, v, p, e in rows:
            data.append(_convert_format(c, v, p, e))

        return {
            "success": True,
            "meter_name": meter_name,
            "from_date": from_date,
            "to_date": to_date,
            "count": len(data),
            "data": data,
        }
    except SQLAlchemyError as e:
        db.rollback()
        raise


@router.put("/{meter_id}/location")
def update_meter_location(
    meter_id: int, location: MeterLocationUpdate, db: Session = Depends(get_db)
):
    """Update the map location for a single meter"""
    meter = db.query(MeterDB).filter(MeterDB.meter_id == meter_id).first()

    if not meter:
        raise HTTPException(
            status_code=404, detail=f"Meter with ID {meter_id} not found"
        )

    try:
        meter.x = location.x
        meter.y = location.y
        db.commit()
        db.refresh(meter)

        return {
            "success": True,
            "message": f"Location updated for meter '{meter.name}'",
            "data": {
                "meter_id": meter.meter_id,
                "name": meter.name,
                "x": meter.x,
                "y": meter.y,
            },
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to update location: {str(e)}"
        )


def _convert_format(current, voltage, power, energy):
    return {
        "meter_id": current.meter_id,
        "timestamp": current.timestamp,
        "phase_A_current": current.phase_A_current,
        "phase_A_voltage": voltage.phase_A_voltage,
        "phase_A_active_power": power.phase_A_active_power,
        "phase_A_power_factor": power.phase_A_power_factor,
        "phase_A_grid_consumption": energy.phase_A_grid_consumption,
        "phase_A_exported_power": energy.phase_A_exported_power,
        "phase_B_current": current.phase_B_current,
        "phase_B_voltage": voltage.phase_B_voltage,
        "phase_B_active_power": power.phase_B_active_power,
        "phase_B_power_factor": power.phase_B_power_factor,
        "phase_B_grid_consumption": energy.phase_B_grid_consumption,
        "phase_B_exported_power": energy.phase_B_exported_power,
        "phase_C_current": current.phase_C_current,
        "phase_C_voltage": voltage.phase_C_voltage,
        "phase_C_active_power": power.phase_C_active_power,
        "phase_C_power_factor": power.phase_C_power_factor,
        "phase_C_grid_consumption": energy.phase_C_grid_consumption,
        "phase_C_exported_power": energy.phase_C_exported_power,
    }
