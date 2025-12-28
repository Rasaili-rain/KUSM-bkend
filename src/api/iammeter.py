import requests
from ..settings import settings
from sqlalchemy.orm import Session
from ..models import MeterDB, MeterDataDB
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

        phaseAdata = dict(zip(fields, data["values"][0]))
        phaseBdata = dict(zip(fields, data["values"][1]))
        phaseCdata = dict(zip(fields, data["values"][2]))

        return {
            "timestamp": data["localTime"],
            "phaseAdata": phaseAdata,
            "phaseBdata": phaseBdata,
            "phaseCdata": phaseCdata,
        }

    except Exception as e:
        print("Fetch failed:", e)
        return None

def insert_meterdata(db: Session, meter_id: int, meter_data: dict):
    ts = datetime.strptime(meter_data["timestamp"], "%Y/%m/%d %H:%M:%S")

    a = meter_data["phaseAdata"]
    b = meter_data["phaseBdata"]
    c = meter_data["phaseCdata"]

    data = MeterDataDB(
        meter_id=meter_id,
        timestamp=ts,

        phase_A_current=a["current"],
        phase_A_voltage=a["voltage"],
        phase_A_active_power=a["active_power"],
        phase_A_power_factor=a["power_factor"],
        phase_A_grid_consumption=a["grid_consumption"],
        phase_A_exported_power=a["exported_power"],

        phase_B_current=b["current"],
        phase_B_voltage=b["voltage"],
        phase_B_active_power=b["active_power"],
        phase_B_power_factor=b["power_factor"],
        phase_B_grid_consumption=b["grid_consumption"],
        phase_B_exported_power=b["exported_power"],

        phase_C_current=c["current"],
        phase_C_voltage=c["voltage"],
        phase_C_active_power=c["active_power"],
        phase_C_power_factor=c["power_factor"],
        phase_C_grid_consumption=c["grid_consumption"],
        phase_C_exported_power=c["exported_power"],
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
            insert_meterdata(db, meter.meter_id, meter_data)
            print(f"data stored for meter {meter.meter_id}")

        db.commit()
    except Exception as e:
        db.rollback()
        print("store_all_meter_data error:", e)
        raise
    finally:
        db.close()
    
def get_meter_id_by_name(meter_name):
    try:
        meter_id = db.query(MeterDB.meter_id).filter(MeterDB.name == meter_name).scalar()
        return meter_id
    except Exception as e:
        return e