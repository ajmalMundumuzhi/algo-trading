
from sqlalchemy import text

from app.core.database import engine

try:
    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT current_database(), version()")
        )
        database_name, version = result.fetchone()

        print("Database connection successful!")
        print(f"Database: {database_name}")
        print(f"PostgreSQL: {version}")

except Exception as error:
    print("Database connection failed!")
    print(error)
