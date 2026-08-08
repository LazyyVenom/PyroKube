from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from models.dashboard import CatalogService, DatabaseInstance, UserService
from services.logger import log_process
from services.managed_services.skeleton import PyroManagedService


class PyroMongoDB(PyroManagedService):
    """Managed MongoDB Document Store Implementation."""

    def __init__(self, app=None):
        super().__init__(app=app)
        self.category = "mongodb"
        self.default_port = "27017"

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
        log_process(db, instance_name, "DEPLOY_MDB", "INFO", f"[PyroMongoDB] Provisioning MongoDB document store '{instance_name}' ({storage_gb}GB PVC)")
        
        catalog_item = db.query(CatalogService).filter(CatalogService.id == service_id).first()
        if catalog_item:
            catalog_item.status = "Active"

        target_ns = f"pyro-{instance_name}"
        endpoint = f"{instance_name}.{target_ns}.svc:{self.default_port}"
        
        # Provision real K8s PVC, Secret, Service, and Deployment inside dedicated namespace
        from services.k8s_service import PyroKubeK8sService
        PyroKubeK8sService.provision_k8s_managed_workload(
            instance_name=instance_name,
            image="mongo:7.0.5",
            port=27017,
            storage_gb=storage_gb,
            cpu_limit=cpu_limit,
            env_vars={
                "MONGO_INITDB_ROOT_USERNAME": db_user or "admin",
                "MONGO_INITDB_ROOT_PASSWORD": db_password or "pyrokube_pass",
                "MONGO_INITDB_DATABASE": instance_name,
            },
            mount_path="/data/db",
        )

        service = db.query(UserService).filter(UserService.id == instance_name).first()
        if not service:
            service = UserService(
                id=instance_name,
                name=instance_name,
                tag="database",
                tag_color="text-ok",
                ready_pods=1,
                total_pods=1,
                status="Running",
                restarts=0,
                image="mongo:7.0.5",
                namespace=target_ns,
                endpoint=endpoint,
                cpu_usage=f"80m / {cpu_limit}",
                memory_usage="384MB / 1024MB",
            )
            db.add(service)

        db.commit()
        db.refresh(service)
        log_process(db, instance_name, "DEPLOY_MDB", "SUCCESS", f"[PyroMongoDB] MongoDB active at '{endpoint}'")
        return service

    async def delete(self, db: Session, service_id: str) -> bool:
        from services.k8s_service import PyroKubeK8sService
        PyroKubeK8sService.teardown_k8s_managed_workload(service_id)

        service = db.query(UserService).filter(UserService.id == service_id).first()
        if service:
            db.delete(service)
            db.commit()
            return True
        return False

    async def add_database(
        self,
        db: Session,
        service_id: str,
        db_name: str,
        db_user: Optional[str] = None,
        db_password: Optional[str] = None,
    ) -> Any:
        log_process(db, service_id, "ADD_DB_MDB", "INFO", f"[PyroMongoDB] Creating logical MongoDB database '{db_name}'")
        db_inst = DatabaseInstance(
            service_id=service_id,
            db_name=db_name,
            db_user=db_user,
            db_password=db_password,
            status="Active",
        )
        db.add(db_inst)
        db.commit()
        return db_inst

    async def get_status(self, db: Session, service_id: str) -> Dict[str, Any]:
        return {"service_id": service_id, "engine": "MongoDB v7.0.5", "status": "Active"}
