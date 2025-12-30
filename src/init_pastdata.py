import pandas as pd
from datetime import datetime
from .models import EnergyDB
from .api.iammeter import get_meter_id_by_name
from .database import SessionLocal
from sqlalchemy.orm import Session

db: Session = SessionLocal()
DEFAULT_METERS = [
        {"name": "Physics Department (Block 6)", "path": "./src/data/Physics.csv"},
        {"name": "Bio-Tech Department (Block 7)", "path": "./src/data/Bio-Tech.csv"},
        {"name": "Block 11 (Department of Civil Engineering)", "path": "./src/data/Civil.csv"},
        {"name": "Block 10 (Department of Management Information)", "path": "./src/data/Management.csv"},
        {"name": "Block 8 (Department of Electrical and Electronics)", "path": "./src/data/Electrical.csv"},
        {"name": "Boys Hostel", "path": "./src/data/Boys_Hostel.csv"},
        {"name": "Main Transformer", "path": "./src/data/Main_Transformer.csv"},
    ]

def insert_past_data(
    csv_path: str,
    meter_name: str
):
    df = pd.read_csv(csv_path)
    meter_id = get_meter_id_by_name(meter_name)

    for _, row in df.iterrows():
        ts = datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M")

        energy = EnergyDB(
            meter_id=meter_id,
            timestamp=ts,

            phase_A_grid_consumption=row["phase_A_grid_consumption"],
            phase_A_exported_power=row["phase_A_exported_power"],

            phase_B_grid_consumption=row["phase_B_grid_consumption"],
            phase_B_exported_power=row["phase_B_exported_power"],

            phase_C_grid_consumption=row["phase_C_grid_consumption"],
            phase_C_exported_power=row["phase_C_exported_power"],
        )

        db.add(energy)

    db.commit()
 
for meter in DEFAULT_METERS:
    insert_past_data(meter["path"], meter["name"])

