from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session


class PyroManagedService(ABC):
    """
    Abstract Base Class for all Managed Services in PyroKube.
    Enforces polymorphic methods across catalog items (PostgreSQL, Redis, MongoDB, etc.).
    """

    def __init__(self, app=None):
        self.app = app

    @abstractmethod
    async def create(
        self,
        db: Session,
        service_id: str,
        instance_name: str,
        storage_gb: int,
        cpu_limit: str,
        db_user: Optional[str] = None,
        db_password: Optional[str] = None,
    ) -> Any:
        """Provision the managed service engine container and register connection mesh."""
        pass

    @abstractmethod
    async def delete(self, db: Session, service_id: str) -> bool:
        """Teardown the managed service engine container and storage."""
        pass

    @abstractmethod
    async def add_database(
        self,
        db: Session,
        service_id: str,
        db_name: str,
        db_user: Optional[str] = None,
        db_password: Optional[str] = None,
    ) -> Any:
        """Provision a new logical database/schema on-demand inside the active engine."""
        pass

    @abstractmethod
    async def get_status(self, db: Session, service_id: str) -> Dict[str, Any]:
        """Fetch engine health, connection strings, and active logical databases."""
        pass