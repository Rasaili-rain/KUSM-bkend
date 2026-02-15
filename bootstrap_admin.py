from sqlalchemy.orm import Session
from src.database import db_engine, SessionLocal
from src.models import Base, User, UserRole
from src.routes.auth.auth_utils import get_password_hash


SUPERADMIN_EMAIL = "superadmin@gmail.com"
SUPERADMIN_PASSWORD = "qwertyuiop"


def bootstrap_users():
    Base.metadata.create_all(bind=db_engine)
    db: Session = SessionLocal()
    try:
        superadmin = User(
            email=SUPERADMIN_EMAIL,
            hashed_password=get_password_hash(SUPERADMIN_PASSWORD),
            full_name=SUPERADMIN_EMAIL.split("@")[0],
            role=UserRole.SUPER_ADMIN,
            is_active=True,
        )
        db.add(superadmin)
        db.commit()
        print(f"Super admin created: {SUPERADMIN_EMAIL}")
        print(f"Password: {SUPERADMIN_PASSWORD}")
        print("Change password after first login!")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    bootstrap_users()
