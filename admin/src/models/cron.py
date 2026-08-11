from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base


class CronJobRecord(Base):
    __tablename__ = "cron_job_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    schedule: Mapped[str] = mapped_column(String, nullable=False, default="0 2 * * *")
    target_service: Mapped[str] = mapped_column(String, nullable=False)
    command: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="Active")
    last_run: Mapped[str] = mapped_column(String, nullable=True)
