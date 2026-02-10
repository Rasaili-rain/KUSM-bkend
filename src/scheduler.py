from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from sqlalchemy.orm import Session

from .database import SessionLocal
from .api.billing import calculate_bill
from .utils.meter_status import update_flatline_status

def meter_status_job():
    db: Session = SessionLocal()
    try:
        update_flatline_status(db)
        print(f"Meter status job completed at {datetime.utcnow()}")
    except Exception as e:
        print(f"Error in meter status job: {e}")
    finally:
        db.close()

scheduler = BackgroundScheduler()

def daily_billing_job():
    db: Session = SessionLocal()
    try:
        now = datetime.now()
        year = now.year
        month = now.month

        calculate_bill(year, month, db)
        print(f"Daily billing job completed for {year}-{month:02d} at {now}")
    except Exception as e:
        print(f"Error in daily billing job: {e}")
    finally:
        db.close()



scheduler.add_job(
    daily_billing_job,
    trigger="interval",
    hours=1,
    id="daily_billing_job",
    replace_existing=True
)

scheduler.add_job(
    meter_status_job,
    trigger="interval",
    hours=12,
    id="meter_status_job",
    replace_existing=True
)
