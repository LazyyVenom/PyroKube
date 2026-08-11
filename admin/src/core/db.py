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

    if "user_services" in inspector.get_table_names():
        usr_cols = [c["name"] for c in inspector.get_columns("user_services")]
        with engine.begin() as conn:
            if "git_repo" not in usr_cols:
                conn.execute(text("ALTER TABLE user_services ADD COLUMN git_repo VARCHAR"))
            if "git_branch" not in usr_cols:
                conn.execute(text("ALTER TABLE user_services ADD COLUMN git_branch VARCHAR DEFAULT 'main'"))
            if "dockerfile_path" not in usr_cols:
                conn.execute(text("ALTER TABLE user_services ADD COLUMN dockerfile_path VARCHAR DEFAULT 'Dockerfile'"))
            if "port" not in usr_cols:
                conn.execute(text("ALTER TABLE user_services ADD COLUMN port INTEGER DEFAULT 8000"))
            if "build_status" not in usr_cols:
                conn.execute(text("ALTER TABLE user_services ADD COLUMN build_status VARCHAR DEFAULT 'Success'"))

    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()