from typing import Dict, Type

from models.managed_services.enums import ManagedServiceCategory
from services.managed_services.garage import PyroGarage
from services.managed_services.mongodb import PyroMongoDB
from services.managed_services.postgres import PyroPostgres
from services.managed_services.rabbitmq import PyroRabbitMQ
from services.managed_services.redis import PyroRedis
from services.managed_services.registry import PyroRegistry
from services.managed_services.skeleton import PyroManagedService
from services.managed_services.zincsearch import PyroZincSearch


class PyroManagedServiceFactory:
    """
    Polymorphic Factory Pattern for PyroKube Managed Services.
    Dynamically resolves and instantiates the correct PyroManagedService subclass.
    """

    _REGISTRY: Dict[str, Type[PyroManagedService]] = {
        ManagedServiceCategory.POSTGRES.value: PyroPostgres,
        ManagedServiceCategory.MONGODB.value: PyroMongoDB,
        ManagedServiceCategory.REDIS.value: PyroRedis,
        ManagedServiceCategory.RABBITMQ.value: PyroRabbitMQ,
        ManagedServiceCategory.ZINCSEARCH.value: PyroZincSearch,
        ManagedServiceCategory.GARAGE.value: PyroGarage,
        ManagedServiceCategory.REGISTRY.value: PyroRegistry,
    }

    @classmethod
    def get_service(cls, category_or_id: str, app=None) -> PyroManagedService:
        category_lower = category_or_id.lower().strip()
        service_cls = cls._REGISTRY.get(category_lower, PyroPostgres)
        return service_cls(app=app)
