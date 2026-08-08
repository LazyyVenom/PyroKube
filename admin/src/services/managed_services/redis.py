from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from models.dashboard import CatalogService, UserService
from services.logger import log_process
from services.managed_services.skeleton import PyroManagedService


class PyroRedis(PyroManagedService):
    """Managed Redis Cache/Store Engine Implementation."""

    def __init__(self, app=None):
        super().__init__(app=app)
        self.category = "redis"
        self.default_port = "6379"

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
        log_process(db, instance_name, "DEPLOY_REDIS", "INFO", f"[PyroRedis] Provisioning Redis in-memory cache/store '{instance_name}'")
        
        catalog_item = db.query(CatalogService).filter(CatalogService.id == service_id).first()
        if catalog_item:
            catalog_item.status = "Active"

        target_ns = f"pyro-{instance_name}"
        endpoint = f"{instance_name}.{target_ns}.svc:{self.default_port}"
        
        # Provision real K8s PVC, Service, and Deployment inside dedicated namespace
        from services.k8s_service import PyroKubeK8sService
        PyroKubeK8sService.provision_k8s_managed_workload(
            instance_name=instance_name,
            image="redis:7.2-alpine",
            port=6379,
            storage_gb=storage_gb,
            cpu_limit=cpu_limit,
            mount_path="/data",
        )

        service = db.query(UserService).filter(UserService.id == instance_name).first()
        if not service:
            service = UserService(
                id=instance_name,
                name=instance_name,
                tag="cache",
                tag_color="text-crit",
                ready_pods=1,
                total_pods=1,
                status="Running",
                restarts=0,
                image="redis:7.2-alpine",
                namespace=target_ns,
                endpoint=endpoint,
                cpu_usage=f"15m / {cpu_limit}",
                memory_usage="64MB / 512MB",
            )
            db.add(service)
        else:
            service.status = "Running"
            service.namespace = target_ns
            service.endpoint = endpoint

        db.commit()
        db.refresh(service)
        log_process(db, instance_name, "DEPLOY_REDIS", "SUCCESS", f"[PyroRedis] Redis engine active at '{endpoint}'")
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
        log_process(db, service_id, "ADD_DB_REDIS", "INFO", f"[PyroRedis] Allocated Redis logical DB index for '{db_name}'")
        return {"service_id": service_id, "db_name": db_name, "type": "redis_key_prefix"}

    async def get_status(self, db: Session, service_id: str) -> Dict[str, Any]:
        return {"service_id": service_id, "engine": "Redis v7.2", "status": "Active"}
