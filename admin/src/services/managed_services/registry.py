from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from models.dashboard import CatalogService, UserService
from models.managed_services.enums import ManagedServiceCategory
from services.logger import log_process
from services.managed_services.skeleton import PyroManagedService


class PyroRegistry(PyroManagedService):
    """
    Polymorphic PyroManagedService Driver for In-Cluster Private Container Image Registry (registry:2).
    Provisions official Docker Distribution Registry on port 5000 inside dedicated namespace 'pyro-registry'.
    """

    def __init__(self, app=None):
        super().__init__(app)
        self.category = ManagedServiceCategory.REGISTRY.value
        self.default_port = 5000

    async def create(
        self,
        db: Session,
        service_id: str,
        instance_name: str,
        storage_gb: int = 10,
        cpu_limit: str = "1000m",
        db_user: Optional[str] = None,
        db_password: Optional[str] = None,
    ) -> UserService:
        log_process(db, instance_name, "DEPLOY_REGISTRY", "INFO", f"[PyroRegistry] Provisioning Private Container Image Registry '{instance_name}' ({storage_gb}GB PVC)")

        catalog_item = db.query(CatalogService).filter(CatalogService.id == service_id).first()
        if catalog_item:
            catalog_item.status = "Active"

        target_ns = f"pyro-{instance_name}"
        endpoint = f"{instance_name}.{target_ns}.svc:{self.default_port}"

        # Provision real K8s PVC, Service, and Deployment inside dedicated namespace
        from services.k8s_service import PyroKubeK8sService
        PyroKubeK8sService.provision_k8s_managed_workload(
            instance_name=instance_name,
            image="registry:2",
            port=5000,
            storage_gb=storage_gb,
            cpu_limit=cpu_limit,
            mount_path="/var/lib/registry",
        )

        service = db.query(UserService).filter(UserService.id == instance_name).first()
        if not service:
            service = UserService(
                id=instance_name,
                name=instance_name,
                tag="registry",
                tag_color="text-kube",
                ready_pods=1,
                total_pods=1,
                status="Running",
                restarts=0,
                image="registry:2",
                namespace=target_ns,
                endpoint=endpoint,
                cpu_usage=f"30m / {cpu_limit}",
                memory_usage="64MB / 512MB",
            )
            db.add(service)
        else:
            service.status = "Running"
            service.namespace = target_ns
            service.endpoint = endpoint

        db.commit()
        db.refresh(service)
        log_process(db, instance_name, "DEPLOY_REGISTRY", "SUCCESS", f"[PyroRegistry] Active at '{endpoint}'")
        return service

    async def delete(self, db: Session, service_id: str) -> bool:
        log_process(db, service_id, "DELETE_REGISTRY", "INFO", f"[PyroRegistry] Executing teardown for registry '{service_id}'")
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
        return None

    async def get_status(self, db: Session, service_id: str) -> Dict[str, Any]:
        service = db.query(UserService).filter(UserService.id == service_id).first()
        return {
            "service_id": service_id,
            "status": service.status if service else "Unknown",
            "endpoint": service.endpoint if service else "",
        }
