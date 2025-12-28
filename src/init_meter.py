from sqlalchemy.orm import Session
from .models import MeterDB, MeterDataDB

DEFAULT_METERS = [
        {"name": "Physics Department (Block 6)", "sn": "CD0FF6AB"},
        {"name": "Bio-Tech Department (Block 7)", "sn": "57DB095D"},
        {"name": "Block 11 (Department of Civil Engineering)", "sn": "DAD94549"},
        {"name": "Block 10 (Department of Management Information)", "sn": "8FA834AC"},
        {"name": "Block 8 (Department of Electrical and Electronics)", "sn": "C249361B"},
        {"name": "Boys Hostel", "sn": "D4C3566B"},
        {"name": "Main Transformer", "sn": "F51C3384"},
    ]

def init_meter(db: Session, meters: list[dict] | None = None):
    

    if meters is None:
        meters = DEFAULT_METERS

    added_meters = []
    for meter in meters:
        exists = db.query(MeterDB).filter_by(sn=meter["sn"]).first()
        if not exists:
            new_meter = MeterDB(**meter)
            db.add(new_meter)
            added_meters.append(new_meter)

    db.commit()

    for meter in added_meters:
        db.refresh(meter)

    return added_meters


def add_meter(db: Session, name: str, sn: str):
    existing = db.query(MeterDB).filter(
        (MeterDB.sn == sn) | (MeterDB.name == name)
    ).first()

    if existing:
        raise ValueError("Meter already exists")

    meter = MeterDB(name=name, sn=sn)
    db.add(meter)
    db.commit()
    db.refresh(meter)
    return meter


def remove_meter(db: Session, sn: str, force: bool = False):
    meter = db.query(MeterDB).filter(MeterDB.sn == sn).first()
    if not meter:
        raise ValueError("Meter not found")
    
    has_data = db.query(MeterDataDB).filter(MeterDataDB.meter_id == meter.meter_id).first()
    if has_data and not force:
        raise ValueError("Cannot delete meter: it has recorded data")
    
    if has_data and force:
        db.query(MeterDataDB).filter(MeterDataDB.meter_id == meter.meter_id).delete()

    db.delete(meter)
    db.commit()
    return meter


def get_all_meters(db: Session):
    return db.query(MeterDB).all()
