import requests
from ..settings import settings
from sqlalchemy.orm import Session
from ..models import CurrentDB, EnergyDB, MeterDB, PowerDB, VoltageDB
from ..database import SessionLocal
from datetime import datetime


db = SessionLocal()
URL = 'https://www.iammeter.com/api/v1/site/meterdata2/'
IAMMETER_ADD_STATION_URL = 'https://www.iammeter.com/dz/user/BIZ_DZ_DianZhanSave/0'


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

    current = CurrentDB(
        meter_id=meter_id,
        timestamp=ts,
        phase_A_current=a["current"],
        phase_B_current=b["current"],
        phase_C_current=c["current"],
    )
    
    voltage = VoltageDB(
        meter_id=meter_id,
        timestamp=ts,
        phase_A_voltage=a["voltage"],
        phase_B_voltage=b["voltage"],
        phase_C_voltage=c["voltage"],
    )


    power = PowerDB(
        meter_id=meter_id,
        timestamp=ts,
        phase_A_active_power=a["active_power"],
        phase_A_power_factor=a["power_factor"],

        phase_B_active_power=b["active_power"],
        phase_B_power_factor=b["power_factor"],

        phase_C_active_power=c["active_power"],
        phase_C_power_factor=c["power_factor"],
    )

    energy = EnergyDB(
        meter_id=meter_id,
        timestamp=ts,
        phase_A_grid_consumption=a["grid_consumption"],
        phase_A_exported_power=a["exported_power"],

        phase_B_grid_consumption=b["grid_consumption"],
        phase_B_exported_power=b["exported_power"],

        phase_C_grid_consumption=c["grid_consumption"],
        phase_C_exported_power=c["exported_power"],
    )

    db.add_all([current, voltage, power, energy])

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

def add_iammeter_station(station_data: dict):
    headers = {
        "Content-Type": "application/json",
        "Cookie": settings.IAMMETER_COOKIE
    }

    try:
        r = requests.post(
            IAMMETER_ADD_STATION_URL,
            json=station_data,
            headers=headers,
            timeout=10
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print("IAMMETER station error:", e)
        return None
    
def calculate_unbalance(A, B, C):
    avg = (A + B + C) / 3
    if avg == 0:
        return 0.0
    
    max_dev = max(
        abs(A - avg),
        abs(B - avg),
        abs(C - avg)
    )

    return round((max_dev / avg) * 100, 2)

def voltage_status(unbalance):
    if unbalance < 1:
        return "NORMAL"
    elif unbalance < 2:
        return "ACCEPTABLE"
    elif unbalance < 3: 
        return "WARNING"
    else:
        return "CRITICAL"
    
def current_status(unbalance):
    if unbalance < 10:
        return "NORMAL"
    elif unbalance < 20:
        return "WARNING"
    else:
        return "CRITICAL"
