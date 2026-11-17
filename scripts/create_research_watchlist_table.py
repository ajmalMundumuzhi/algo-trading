
from app.core.database import engine
from app.models import Base

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine, tables=[
        Base.metadata.tables["research_watchlist"]
    ])
    print("Research watchlist table created successfully.")
