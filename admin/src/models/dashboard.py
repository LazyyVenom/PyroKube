from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base


class ServerStatus(Base):
    __tablename__ = "server_status"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nodes_healthy: Mapped[int] = mapped_column(Integer, default=3)
    nodes_total: Mapped[int] = mapped_column(Integer, default=3)
    api_server_status: Mapped[str] = mapped_column(String, default="Ready")
    cpu_usage_pct: Mapped[int] = mapped_column(Integer, default=18)
    cpu_cores: Mapped[int] = mapped_column(Integer, default=12)
    memory_used_gb: Mapped[float] = mapped_column(Float, default=4.2)
    memory_max_gb: Mapped[float] = mapped_column(Float, default=32.0)
    storage_used_gb: Mapped[int] = mapped_column(Integer, default=120)
    storage_max_gb: Mapped[int] = mapped_column(Integer, default=500)
    storage_assigned_gb: Mapped[int] = mapped_column(Integer, default=250)
    cpu_allocated_m: Mapped[int] = mapped_column(Integer, default=800)
    memory_allocated_gb: Mapped[float] = mapped_column(Float, default=0.6)


class UserService(Base):
    __tablename__ = "user_services"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    tag: Mapped[str] = mapped_column(String, nullable=False)
    tag_color: Mapped[str] = mapped_column(String, default="text-kube")
    ready_pods: Mapped[int] = mapped_column(Integer, default=1)
    total_pods: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String, default="Running")
    restarts: Mapped[int] = mapped_column(Integer, default=0)
    image: Mapped[str] = mapped_column(String, default="")
    namespace: Mapped[str] = mapped_column(String, default="default")
    endpoint: Mapped[str] = mapped_column(String, default="")
    cpu_usage: Mapped[str] = mapped_column(String, default="0m / 500m")
    memory_usage: Mapped[str] = mapped_column(String, default="0MB / 512MB")


class CatalogService(Base):
    __tablename__ = "catalog_services"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    category_label: Mapped[str] = mapped_column(String, nullable=False)
    badge: Mapped[str] = mapped_column(String, nullable=False)
    badge_color: Mapped[str] = mapped_column(String, default="text-kube")
    description: Mapped[str] = mapped_column(String, default="")
    port: Mapped[str] = mapped_column(String, default="")
    port_label: Mapped[str] = mapped_column(String, default="Default Port")
    version: Mapped[str] = mapped_column(String, default="v1.0")
    status: Mapped[str] = mapped_column(String, default="InActive")
    subtitle: Mapped[str] = mapped_column(String, default="")


class DatabaseInstance(Base):
    __tablename__ = "database_instances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    service_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    db_name: Mapped[str] = mapped_column(String, nullable=False)
    db_user: Mapped[str] = mapped_column(String, nullable=False)
    db_password: Mapped[str] = mapped_column(String, nullable=False)
    charset: Mapped[str] = mapped_column(String, default="UTF8")
    status: Mapped[str] = mapped_column(String, default="Active")
