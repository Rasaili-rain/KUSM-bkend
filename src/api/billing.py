from datetime import datetime, timedelta
import calendar
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import func
import json

from ..models import EnergyDB, BillingDB, CostPerDayDB, CostPerMeterDB
from ..database import get_db


TARIFF = 8.0


def get_power_per_meter_per_day(year: int, month: int, day: int, db: Session):
  start = datetime(year, month, day)
  end = start + timedelta(days=1)

  daily_energy = (
    db.query(
      EnergyDB.meter_id,
      func.sum(EnergyDB.phase_A_grid_consumption).label("phase_a_kwh"),
      func.sum(EnergyDB.phase_B_grid_consumption).label("phase_b_kwh"),
      func.sum(EnergyDB.phase_C_grid_consumption).label("phase_c_kwh"),
    )
    .filter(
      EnergyDB.timestamp >= start,
      EnergyDB.timestamp < end
    )
    .group_by(EnergyDB.meter_id)
    .all()
  )

  if not daily_energy:
    return None

  meter_to_energy = {}

  for data in daily_energy:
    total = data.phase_a_kwh or 0 + data.phase_b_kwh or 0 + data.phase_c_kwh or 0
    meter_to_energy.update({ data.meter_id: total })

  return meter_to_energy

def calculate_bill(year: int, month: int, db: Session):
  month_key = f"{year}-{month:02d}"
  _, total_days = calendar.monthrange(year, month)

  # Load existing billing row
  billing = (
    db.query(BillingDB)
    .filter(BillingDB.date == month_key)
    .first()
  )

  # Create default
  if not billing:
    billing = BillingDB(
      date=month_key,
      total_cost=0,
      avg_cost_per_day=0,
      expensive_day=0,
      expensive_day_cost=0,
    )
    db.add(billing)
    db.commit()

  # Get existing days
  existing_days = {
    row.day
    for row in db.query(CostPerDayDB.day)
    .filter(CostPerDayDB.date == month_key)
    .all()
  }

  # Main calculation
  for day in range(1, total_days + 1):
    if day in existing_days:
      continue

    meter_to_energy = get_power_per_meter_per_day(year, month, day, db)

    total_per_day = 0
    for meter_id, energy in meter_to_energy.items():
      cost = energy * TARIFF
      total_per_day += cost

      stmt = insert(CostPerMeterDB).values(
        date=month_key,
        meter_id=meter_id,
        cost=cost
      ).on_conflict_do_update(
        constraint="unique_constraint",
        set_={
          "cost": CostPerMeterDB.cost + cost
        }
      )
      db.execute(stmt)

    # store daily cost
    db.add(
      CostPerDayDB(
        date=month_key,
        day=day,
        cost=total_per_day
      )
    )

    billing.total_cost += total_per_day

    # update expensive day
    if total_per_day > billing.expensive_day_cost:
      billing.expensive_day = day
      billing.expensive_day_cost = total_per_day


  db.flush()

  # Calculate average per day
  days_count = db.query(CostPerDayDB).filter(
      CostPerDayDB.date == month_key
  ).count()

  billing.avg_cost_per_day = (
      billing.total_cost / days_count if days_count else 0
  )

  db.commit()
