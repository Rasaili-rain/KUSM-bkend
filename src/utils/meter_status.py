from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import os
import asyncio

from src.models import PowerDB, MeterDB, MeterStatusDB
from src.utils.email_service import send_email

WINDOW_MINUTES = 60
EPS = 1
MIN_POINTS = 10


def is_flatline(values: list[float]) -> bool:
    vals = [int(round(v)) for v in values]  # float-safe strict W
    return max(vals) - min(vals) <= EPS


def run_async_blocking(coro):
    # Best for scheduler: actually wait until email is sent
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        new_loop = asyncio.new_event_loop()
        try:
            return new_loop.run_until_complete(coro)
        finally:
            new_loop.close()
    else:
        return asyncio.run(coro)


def update_flatline_status(db: Session):
    now = datetime.utcnow()
    start = now - timedelta(minutes=WINDOW_MINUTES)

    alert_to = os.environ.get("ADMIN_EMAIL")
    if not alert_to:
        print("ALERT_TO_EMAIL not set; skipping email alerts")

    meters = db.query(MeterDB.meter_id, MeterDB.name, MeterDB.sn).all()

    for meter_id, name, sn in meters:
        rows = (
            db.query(
                PowerDB.phase_A_active_power,
                PowerDB.phase_B_active_power,
                PowerDB.phase_C_active_power,
            )
            .filter(PowerDB.meter_id == meter_id, PowerDB.timestamp >= start)
            .all()
        )

        status = db.get(MeterStatusDB, meter_id)
        if not status:
            status = MeterStatusDB(meter_id=meter_id)

        if len(rows) < MIN_POINTS:
            status.is_flatline = False
            status.checked_at = now
            db.add(status)
            continue

        a = [r.phase_A_active_power for r in rows]
        b = [r.phase_B_active_power for r in rows]
        c = [r.phase_C_active_power for r in rows]

        flat = is_flatline(a) and is_flatline(b) and is_flatline(c)

        status.is_flatline = flat
        status.checked_at = now

        if flat and alert_to:
            subject = f"🚨 Meter DOWN (Flatline) — ID {meter_id}"
            body = (
                f"Meter is DOWN (flatline still detected)\n\n"
                f"Meter ID : {meter_id}\n"
                f"Name     : {name}\n"
                f"SN       : {sn}\n"
                f"Checked  : {now.isoformat()} UTC\n"
                f"Window   : {WINDOW_MINUTES} minutes\n"
                f"EPS      : {EPS} watt\n"
            )
            try:
                run_async_blocking(send_email(alert_to, subject, body))
                status.last_alert_sent_at = now  # keep this if column exists
            except Exception as e:
                print(f"Email send failed for meter {meter_id}: {e}")

        db.add(status)

    db.commit()
