from enum import Enum


class ManagedServiceCategory(str, Enum):
    POSTGRES = "postgres"
    MONGODB = "mongodb"
    REDIS = "redis"
    RABBITMQ = "rabbitmq"
    ZINCSEARCH = "zincsearch"
    GARAGE = "garage"
    REGISTRY = "registry"
