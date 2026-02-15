from datetime import datetime
from enum import Enum
from sqlalchemy import (
    Column,
    Index,
    String,
    DateTime,
    Boolean,
    Float,
    Integer,
    ForeignKey,
    desc,
    Text,
    UniqueConstraint,
    Enum as SQLEnum,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from zoneinfo import ZoneInfo


Base = declarative_base()

# Nepal timezone
NEPAL_TZ = ZoneInfo("Asia/Kathmandu")


def get_nepal_time():
    """Get current time in Nepal timezone"""
    return datetime.now(NEPAL_TZ)


class MeterDB(Base):
    __tablename__ = "meters"

    meter_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    sn = Column(String)
    x = Column(Float, nullable=True)  # Map X coordinate (0-100%)
    y = Column(Float, nullable=True)  # Map Y coordinate (0-100%)


class CurrentDB(Base):
    __tablename__ = "current"

    id = Column(Integer, primary_key=True, autoincrement=True)
    meter_id = Column(
        Integer, ForeignKey("meters.meter_id", ondelete="CASCADE"), nullable=False
    )
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
    meter_id = Column(
        Integer, ForeignKey("meters.meter_id", ondelete="CASCADE"), nullable=False
    )
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
    meter_id = Column(
        Integer, ForeignKey("meters.meter_id", ondelete="CASCADE"), nullable=False
    )
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
    meter_id = Column(
        Integer, ForeignKey("meters.meter_id", ondelete="CASCADE"), nullable=False
    )
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
        Integer, ForeignKey("meters.meter_id", ondelete="CASCADE"), nullable=False
    )
    cost = Column(Float, nullable=False)

    __table_args__ = (UniqueConstraint("date", "meter_id", name="unique_constraint"),)


class MeterStatusDB(Base):
    __tablename__ = "meter_status"

    meter_id = Column(
        Integer, ForeignKey("meters.meter_id", ondelete="CASCADE"), primary_key=True
    )

    is_flatline = Column(Boolean, nullable=False, default=False)
    checked_at = Column(DateTime, default=datetime.utcnow)

    last_alert_sent_at = Column(DateTime, nullable=True)
    alert_active = Column(Boolean, nullable=False, default=False)


class DataCollectionScheduleDB(Base):
    """Stores the current data collection schedule configuration"""

    __tablename__ = "data_collection_schedule"

    id = Column(Integer, primary_key=True, autoincrement=True)
    start_datetime = Column(
        DateTime(timezone=True), nullable=False
    )  # Full datetime with timezone (Nepal time)
    end_datetime = Column(
        DateTime(timezone=True), nullable=False
    )  # Full datetime with timezone (Nepal time)
    interval_minutes = Column(Integer, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=get_nepal_time, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=get_nepal_time,
        onupdate=get_nepal_time,
        nullable=True,
    )
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    def __repr__(self):
        return (
            f"<DataCollectionSchedule(id={self.id}, "
            f"start={self.start_datetime}, end={self.end_datetime}, "
            f"interval={self.interval_minutes}min, active={self.is_active})>"
        )


class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    role = Column(SQLEnum(UserRole), default=UserRole.ADMIN, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(Integer, nullable=True)
