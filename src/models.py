from datetime import datetime
from sqlalchemy import Column, Index, String, DateTime, Boolean, Float, Integer, ForeignKey, desc, Text, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class MeterDB(Base):
    __tablename__ = "meters"

    meter_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    sn = Column(String)
    x = Column(Float, nullable=True)  # Map X coordinate (0-100%)
    y = Column(Float, nullable=True)  # Map Y coordinate (0-100%)


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

class MeterStatusDB(Base):
    __tablename__ = "meter_status"

    meter_id = Column(Integer, ForeignKey("meters.meter_id", ondelete="CASCADE"), primary_key=True)

    is_flatline = Column(Boolean, nullable=False, default=False)
    checked_at = Column(DateTime, default=datetime.utcnow)

    last_alert_sent_at = Column(DateTime, nullable=True)
    alert_active = Column(Boolean, nullable=False, default=False)
