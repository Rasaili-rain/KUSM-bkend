import requests
from ..settings import settings
from sqlalchemy.orm import Session
from ..models import MeterDB, MeterDataDB, Phase
from ..database import SessionLocal
from datetime import datetime

db = SessionLocal()
URL = 'https://www.iammeter.com/api/v1/site/meterdata2/'

import requests

def fetch_meter_data(meter_sn:str):
    params = {
        "token": settings.IAMMETER_TOKEN
    }
    try:
        r = requests.get(URL+meter_sn, timeout=10, params=params)
        r.raise_for_status()
        payload = r.json()

        if not payload.get("successful"):
            print("API error:", payload.get("message"))
            return None

        data = payload["data"]

        fields = [
            "voltage",
            "current",
            "active_power",
            "power_factor",
            "grid_consumption",
            "exported_power",
        ]

        readings = {}

        for phase, values in zip(["A","B","C"], data["values"]):
            readings[phase] = dict(zip(fields, values))

        return {
            "times": {
                "local": data["localTime"],
                "gmt": data["gmtTime"]
            },
            "phases": readings
        }

    except Exception as e:
        print("Fetch failed:", e)
        return None

def insert_meterdata(db: Session, readings, time_str: str, phase: Phase, meter_id: int):
    data = MeterDataDB(
        phase=phase,
        current=readings['current'],
        voltage=readings['voltage'],
        active_power=readings['active_power'],
        power_factor=readings['power_factor'],
        grid_consumption=readings['grid_consumption'],
        exported_power=readings['exported_power'],
        timestamp=datetime.strptime(time_str, "%Y/%m/%d %H:%M:%S"),
        meter_id=meter_id,
    )
    db.add(data)


def store_all_meter_data():
    db: Session = SessionLocal()
    try:
        meters = db.query(MeterDB).all()

        for meter in meters:
            meter_data = fetch_meter_data(meter.sn)
            if meter_data is None:
                continue

            phases = meter_data['phases']
            time_str = meter_data['times']['local']

            insert_meterdata(db, phases["A"], time_str, Phase.PHASE_A, meter.meter_id)
            insert_meterdata(db, phases["B"], time_str, Phase.PHASE_B, meter.meter_id)
            insert_meterdata(db, phases["C"], time_str, Phase.PHASE_C, meter.meter_id)

            print(f"data stored for meter {meter.meter_id}")

        db.commit()
    except Exception as e:
        db.rollback()
        print("store_all_meter_data error:", e)
        raise
    finally:
        db.close()
    
    
