from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List
from datetime import datetime

from ..database import get_db
from ..models import CurrentDB, VoltageDB, PowerDB, EnergyDB


router = APIRouter(tags=["meter"])

@router.get("/live-data")
async def get_live_data(db: Session = Depends(get_db)):
    """
    Get the most recent readings for all data types across all meters.
    """
    try:
        current = _get_latest_current(db)
        voltage = _get_latest_voltage(db)
        power = _get_latest_power(db)
        energy = _get_latest_energy(db)
        
        return {
            "current": current,
            "voltage": voltage,
            "power": power,
            "energy": energy,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching live data: {str(e)}")



# helpers
def _get_latest_current(db: Session):
    subquery = (
        db.query(
            CurrentDB.meter_id,
            func.max(CurrentDB.timestamp).label("max_timestamp")
        )
        .group_by(CurrentDB.meter_id)
        .subquery()
    )
    
    results = (
        db.query(CurrentDB)
        .join(
            subquery,
            and_(
                CurrentDB.meter_id == subquery.c.meter_id,
                CurrentDB.timestamp == subquery.c.max_timestamp
            )
        )
        .all()
    )
    
    return [
        {
            "id": r.id,
            "meter_id": r.meter_id,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            "phase_A_current": r.phase_A_current,
            "phase_B_current": r.phase_B_current,
            "phase_C_current": r.phase_C_current,
        }
        for r in results
    ]


def _get_latest_voltage(db: Session):
    subquery = (
        db.query(
            VoltageDB.meter_id,
            func.max(VoltageDB.timestamp).label("max_timestamp")
        )
        .group_by(VoltageDB.meter_id)
        .subquery()
    )
    
    results = (
        db.query(VoltageDB)
        .join(
            subquery,
            and_(
                VoltageDB.meter_id == subquery.c.meter_id,
                VoltageDB.timestamp == subquery.c.max_timestamp
            )
        )
        .all()
    )
    
    return [
        {
            "id": r.id,
            "meter_id": r.meter_id,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            "phase_A_voltage": r.phase_A_voltage,
            "phase_B_voltage": r.phase_B_voltage,
            "phase_C_voltage": r.phase_C_voltage,
        }
        for r in results
    ]


def _get_latest_power(db: Session):
    subquery = (
        db.query(
            PowerDB.meter_id,
            func.max(PowerDB.timestamp).label("max_timestamp")
        )
        .group_by(PowerDB.meter_id)
        .subquery()
    )
    
    results = (
        db.query(PowerDB)
        .join(
            subquery,
            and_(
                PowerDB.meter_id == subquery.c.meter_id,
                PowerDB.timestamp == subquery.c.max_timestamp
            )
        )
        .all()
    )
    
    return [
        {
            "id": r.id,
            "meter_id": r.meter_id,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            "phase_A_active_power": r.phase_A_active_power,
            "phase_A_power_factor": r.phase_A_power_factor,
            "phase_B_active_power": r.phase_B_active_power,
            "phase_B_power_factor": r.phase_B_power_factor,
            "phase_C_active_power": r.phase_C_active_power,
            "phase_C_power_factor": r.phase_C_power_factor,
        }
        for r in results
    ]


def _get_latest_energy(db: Session):
    subquery = (
        db.query(
            EnergyDB.meter_id,
            func.max(EnergyDB.timestamp).label("max_timestamp")
        )
        .group_by(EnergyDB.meter_id)
        .subquery()
    )
    
    results = (
        db.query(EnergyDB)
        .join(
            subquery,
            and_(
                EnergyDB.meter_id == subquery.c.meter_id,
                EnergyDB.timestamp == subquery.c.max_timestamp
            )
        )
        .all()
    )
    
    return [
        {
            "id": r.id,
            "meter_id": r.meter_id,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            "phase_A_grid_consumption": r.phase_A_grid_consumption,
            "phase_A_exported_power": r.phase_A_exported_power,
            "phase_B_grid_consumption": r.phase_B_grid_consumption,
            "phase_B_exported_power": r.phase_B_exported_power,
            "phase_C_grid_consumption": r.phase_C_grid_consumption,
            "phase_C_exported_power": r.phase_C_exported_power,
        }
        for r in results
    ]

