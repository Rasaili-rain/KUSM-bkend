from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Index, String, DateTime, Boolean, Float, Integer, ForeignKey, desc, Text, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel, EmailStr

Base = declarative_base()

class UserDB(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    picture = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class User(BaseModel):
    id: str
    email: EmailStr
    name: Optional[str] = None
    picture: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MeterDB(Base):
    __tablename__ = "meters"

    meter_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    sn = Column(String)

class Meter(BaseModel):
    meter_id: int
    name: str
    sn: str

    class Config:
        from_attributes = True

# ------------------------
class CurrentDB(Base):
    __tablename__ = "current"

    id = Column(Integer, primary_key=True, autoincrement=True)
    meter_id = Column(Integer, ForeignKey("meters.meter_id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime, nullable=False)

    phase_A_current = Column(Float, nullable=False)
    phase_B_current = Column(Float, nullable=False)
    phase_C_current = Column(Float, nullable=False)

    __table_args__ = (
        Index("idx_current_meter_timestamp", "meter_id", desc("timestamp")),
    )

class VoltageDB(Base):
    __tablename__ = "voltage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    meter_id = Column(Integer, ForeignKey("meters.meter_id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime, nullable=False)

    phase_A_voltage = Column(Float, nullable=False)
    phase_B_voltage = Column(Float, nullable=False)
    phase_C_voltage = Column(Float, nullable=False)

    __table_args__ = (
        Index("idx_voltage_meter_timestamp", "meter_id", desc("timestamp")),
    )

class PowerDB(Base):
    __tablename__ = "power"

    id = Column(Integer, primary_key=True, autoincrement=True)
    meter_id = Column(Integer, ForeignKey("meters.meter_id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime, nullable=False)

    phase_A_active_power = Column(Float, nullable=False)
    phase_A_power_factor = Column(Float, nullable=False)

    phase_B_active_power = Column(Float, nullable=False)
    phase_B_power_factor = Column(Float, nullable=False)

    phase_C_active_power = Column(Float, nullable=False)
    phase_C_power_factor = Column(Float, nullable=False)

    __table_args__ = (
        Index("idx_power_meter_timestamp", "meter_id", desc("timestamp")),
    )

class EnergyDB(Base):
    __tablename__ = "energy"

    id = Column(Integer, primary_key=True, autoincrement=True)
    meter_id = Column(Integer, ForeignKey("meters.meter_id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime, nullable=False)

    phase_A_grid_consumption = Column(Float, nullable=False)
    phase_A_exported_power = Column(Float, nullable=False)

    phase_B_grid_consumption = Column(Float, nullable=False)
    phase_B_exported_power = Column(Float, nullable=False)

    phase_C_grid_consumption = Column(Float, nullable=False)
    phase_C_exported_power = Column(Float, nullable=False)

    __table_args__ = (
        Index("idx_energy_meter_timestamp", "meter_id", desc("timestamp")),
    )

class BillingDB(Base):
    __tablename__ = "billing"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Text, nullable=False)
    total_cost = Column(Float, nullable=False)
    avg_cost_per_day = Column(Float, nullable=False)
    expensive_day = Column(Integer, nullable=False)
    expensive_day_cost = Column(Float, nullable=False)

class CostPerDayDB(Base):
    __tablename__ = "cost_per_day"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Text, nullable=False)
    day = Column(Integer, nullable=False)
    cost = Column(Float, nullable=False)

class CostPerMeterDB(Base):
    __tablename__ = "cost_per_meter"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Text, nullable=False)
    meter_id = Column(
        Integer,
        ForeignKey("meters.meter_id", ondelete="CASCADE"),
        nullable=False
    )
    cost = Column(Float, nullable=False)

    __table_args__ = (
        UniqueConstraint("date", "meter_id", name="unique_constraint"),
    )
