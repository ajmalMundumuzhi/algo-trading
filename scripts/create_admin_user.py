
from getpass import getpass

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import User, UserRole


def main():
    email = input("Admin email: ").strip().lower()
    full_name = input("Admin full name: ").strip()

    password = getpass("Admin password: ")
    confirm_password = getpass("Confirm password: ")

    if not email or not full_name:
        print("Email and full name are required.")
        return

    if len(password) < 12:
        print("Use a password with at least 12 characters.")
        return

    if password != confirm_password:
        print("Passwords do not match.")
        return

    db = SessionLocal()

    try:
        existing_user = db.scalar(
            select(User).where(User.email == email)
        )

        if existing_user:
            print("A user with this email already exists.")
            return

        admin = User(
            email=email,
            full_name=full_name,
            password_hash=hash_password(password),
            role=UserRole.ADMIN,
            is_active=True,
        )

        db.add(admin)
        db.commit()
        db.refresh(admin)

        print("Admin reviewer created successfully.")
        print("Email:", admin.email)
        print("Role:", admin.role.value)
        print("Active:", admin.is_active)

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
