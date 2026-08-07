from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from core.settings import setting

connect_args = {"check_same_thread": False} if setting.DB_URL.startswith("sqlite") else {}

engine = create_engine(setting.DB_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from models import Base
    from utils.seed import seed_database
    from sqlalchemy import inspect, text

    Base.metadata.create_all(bind=engine)

    # Auto-migrate new columns for SQLite database
    inspector = inspect(engine)
    if "server_status" in inspector.get_table_names():
        columns = [c["name"] for c in inspector.get_columns("server_status")]
        with engine.begin() as conn:
            if "cpu_allocated_m" not in columns:
                conn.execute(text("ALTER TABLE server_status ADD COLUMN cpu_allocated_m INTEGER DEFAULT 800"))
            if "memory_allocated_gb" not in columns:
                conn.execute(text("ALTER TABLE server_status ADD COLUMN memory_allocated_gb FLOAT DEFAULT 0.6"))

    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()