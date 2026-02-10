from datetime import datetime, timedelta
import calendar
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import func

from ..models import EnergyDB, BillingDB, CostPerDayDB, CostPerMeterDB


TARIFF = 8.0


def get_power_per_meter_per_day(year: int, month: int, day: int, db: Session):
    start = datetime(year, month, day)
    end = start + timedelta(days=1)
    
    # Get first and last readings for each meter/phase
    from sqlalchemy import and_
    
    # Subquery for first reading of the day
    first_reading = (
        db.query(
            EnergyDB.meter_id,
            func.min(EnergyDB.timestamp).label("first_time")
        )
        .filter(
            EnergyDB.timestamp >= start,
            EnergyDB.timestamp < end
        )
        .group_by(EnergyDB.meter_id)
        .subquery()
    )
    
    # Subquery for last reading of the day
    last_reading = (
        db.query(
            EnergyDB.meter_id,
            func.max(EnergyDB.timestamp).label("last_time")
        )
        .filter(
            EnergyDB.timestamp >= start,
            EnergyDB.timestamp < end
        )
        .group_by(EnergyDB.meter_id)
        .subquery()
    )
    
    # Get first values
    first_values = (
        db.query(
            EnergyDB.meter_id,
            EnergyDB.phase_A_grid_consumption.label("first_a"),
            EnergyDB.phase_B_grid_consumption.label("first_b"),
            EnergyDB.phase_C_grid_consumption.label("first_c"),
        )
        .join(
            first_reading,
            and_(
                EnergyDB.meter_id == first_reading.c.meter_id,
                EnergyDB.timestamp == first_reading.c.first_time
            )
        )
        .all()
    )
    
    # Get last values
    last_values = (
        db.query(
            EnergyDB.meter_id,
            EnergyDB.phase_A_grid_consumption.label("last_a"),
            EnergyDB.phase_B_grid_consumption.label("last_b"),
            EnergyDB.phase_C_grid_consumption.label("last_c"),
        )
        .join(
            last_reading,
            and_(
                EnergyDB.meter_id == last_reading.c.meter_id,
                EnergyDB.timestamp == last_reading.c.last_time
            )
        )
        .all()
    )
    
    # Create lookup dictionaries
    first_dict = {row.meter_id: row for row in first_values}
    last_dict = {row.meter_id: row for row in last_values}
    
    meter_to_energy = {}
    
    for meter_id in first_dict.keys():
        if meter_id not in last_dict:
            continue
            
        first = first_dict[meter_id]
        last = last_dict[meter_id]
        
        # Calculate consumption as difference
        phase_a = (last.last_a or 0) - (first.first_a or 0)
        phase_b = (last.last_b or 0) - (first.first_b or 0)
        phase_c = (last.last_c or 0) - (first.first_c or 0)
        
        total = phase_a + phase_b + phase_c
        
        # Handle meter rollover (if meter resets to 0)
        if total < 0:
            # This might indicate a meter reset or error
            # You may want to log this or handle differently
            continue
            
        meter_to_energy[meter_id] = total
    
    return meter_to_energy

def calculate_bill(year: int, month: int, db: Session):
    month_key = f"{year}-{month:02d}"
    _, total_days = calendar.monthrange(year, month)
    
    # Track total cost per meter for the entire month
    meter_total_costs = {}
    
    # Temporary storage for new data
    new_daily_costs = []
    total_cost = 0
    expensive_day = 0
    expensive_day_cost = 0
    
    # Main calculation
    for day in range(1, total_days + 1):
        meter_to_energy = get_power_per_meter_per_day(year, month, day, db)
        total_per_day = 0
        
        for meter_id, energy in meter_to_energy.items():
            cost = energy * TARIFF
            total_per_day += cost
            
            # Accumulate cost for this meter across all days
            if meter_id not in meter_total_costs:
                meter_total_costs[meter_id] = 0
            meter_total_costs[meter_id] += cost
        
        # Store daily cost in temporary list
        new_daily_costs.append(
            CostPerDayDB(
                date=month_key,
                day=day,
                cost=total_per_day
            )
        )
        
        total_cost += total_per_day
        
        # Update expensive day
        if total_per_day > expensive_day_cost:
            expensive_day = day
            expensive_day_cost = total_per_day
    
    # Calculate average per day
    days_count = len(new_daily_costs)
    avg_cost_per_day = total_cost / days_count if days_count else 0
    
    # Now delete old data and insert new data atomically
    db.query(CostPerDayDB).filter(CostPerDayDB.date == month_key).delete()
    db.query(CostPerMeterDB).filter(CostPerMeterDB.date == month_key).delete()
    db.query(BillingDB).filter(BillingDB.date == month_key).delete()
    
    # Insert all new daily costs
    for daily_cost in new_daily_costs:
        db.add(daily_cost)
    
    # Insert all meter costs
    for meter_id, total_meter_cost in meter_total_costs.items():
        db.add(CostPerMeterDB(
            date=month_key,
            meter_id=meter_id,
            cost=total_meter_cost
        ))
    
    # Create fresh billing record
    billing = BillingDB(
        date=month_key,
        total_cost=total_cost,
        avg_cost_per_day=avg_cost_per_day,
        expensive_day=expensive_day,
        expensive_day_cost=expensive_day_cost,
    )
    db.add(billing)
    
    db.commit()
