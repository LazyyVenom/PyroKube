from abc import ABC, abstractmethod


class PyroManagedService(ABC):
    @abstractmethod
    async def create(self):
        pass

    @abstractmethod
    async def delete(self):
        pass