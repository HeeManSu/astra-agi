from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


# Default to SQLite for the starter template
DATABASE_URL = "sqlite:///./astra.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency to get DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
