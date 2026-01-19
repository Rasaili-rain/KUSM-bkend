from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date

from ..models import EnergyDB, BillingDB, CostPerDayDB, CostPerMeterDB
from ..database import get_db
from ..api.billing import calculate_bill

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/{year}/{month}")
def get_bill(
    year: int,
    month: int,
    db: Session = Depends(get_db)
  ):
  month_key = f"{year}-{month:02d}"

  billing = (
    db.query(
      BillingDB.total_cost,
      BillingDB.avg_cost_per_day,
      BillingDB.expensive_day,
      BillingDB.expensive_day_cost,
    )
    .filter(BillingDB.date == month_key)
    .first()
  )

  if not billing:
    calculate_bill(year, month, db)
    billing = (
      db.query(
        BillingDB.total_cost,
        BillingDB.avg_cost_per_day,
        BillingDB.expensive_day,
        BillingDB.expensive_day_cost,
      )
      .filter(BillingDB.date == month_key)
      .first()
    )

  cost_per_day = (
    db.query(
      CostPerDayDB.day,
      CostPerDayDB.cost,
    )
    .filter(CostPerDayDB.date == month_key)
    .all()
  )

  cost_per_meter = (
    db.query(
      CostPerMeterDB.meter_id,
      CostPerMeterDB.cost,
    )
    .filter(CostPerMeterDB.date == month_key)
    .all()
  )

  weekdays = {}
  week_count = {}

  for day, cost in cost_per_day:
    d = date(year, month, day)
    weekday_name = d.strftime("%A")

    if weekday_name in weekdays:
      weekdays[weekday_name] += cost
      week_count[weekday_name] += 1
    else:
      weekdays.update({weekday_name: cost})
      week_count.update({weekday_name: 1})

  avg_cost_per_week_days = {
      weekday: weekdays[weekday] / week_count[weekday]
      for weekday in weekdays
  }

  return {
    "billing": {
      "total_cost": billing.total_cost,
      "avg_cost_per_day": billing.avg_cost_per_day,
      "expensive_day": billing.expensive_day,
      "expensive_day_cost": billing.expensive_day_cost,
    },
    "cost_per_day": [
      {"day": day, "cost": cost}
      for day, cost in cost_per_day
    ],
    "cost_per_meter": [
      {"meter_id": meter_id, "cost": cost}
      for meter_id, cost in cost_per_meter
    ],
    "avg_cost_per_weekday": avg_cost_per_week_days
  }


@router.post("/{year}/{month}")
def do_bill(
    year: int,
    month: int,
    db: Session = Depends(get_db)
  ):

  month_key = f"{year}-{month:02d}"

  db.query(BillingDB).filter(BillingDB.date == month_key).delete()
  db.query(CostPerDayDB).filter(CostPerDayDB.date == month_key).delete()
  db.query(CostPerMeterDB).filter(CostPerMeterDB.date == month_key).delete()

  calculate_bill(year, month, db)
  return "Billing Calculated"
