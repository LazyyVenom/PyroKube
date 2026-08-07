from services.managed_services.skeleton import PyroManagedService

class PyroPostgres(PyroManagedService):
    def __init__(self, app):
        self.app = app

    async def create(self):
        pass

    async def delete(self):
        pass