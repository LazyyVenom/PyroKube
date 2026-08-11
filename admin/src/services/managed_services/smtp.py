from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from models.dashboard import CatalogService, UserService
from models.managed_services.enums import ManagedServiceCategory
from services.logger import log_process
from services.managed_services.skeleton import PyroManagedService


class PyroSMTP(PyroManagedService):
    """
    Polymorphic PyroManagedService Driver for In-Cluster SMTP Server / Mail Relay.
    Provisions Mailpit SMTP server on ports 1025 (SMTP) and 8025 (Web UI).
    """

    def __init__(self, app=None):
        super().__init__(app)
        self.category = "smtp"
        self.default_port = 1025

    async def create(
        self,
        db: Session,
        service_id: str,
        instance_name: str,
        storage_gb: int = 1,
        cpu_limit: str = "500m",
        db_user: Optional[str] = None,
        db_password: Optional[str] = None,
    ) -> UserService:
        log_process(db, instance_name, "DEPLOY_SMTP", "INFO", f"[PyroSMTP] Provisioning SMTP Mailer Relay '{instance_name}'")

        catalog_item = db.query(CatalogService).filter(CatalogService.id == service_id).first()
        if catalog_item:
            catalog_item.status = "Active"

        target_ns = f"pyro-{instance_name}"
        endpoint = f"{instance_name}.{target_ns}.svc:{self.default_port}"

        from services.k8s_service import PyroKubeK8sService
        PyroKubeK8sService.provision_k8s_managed_workload(
            instance_name=instance_name,
            image="axllent/mailpit:latest",
            port=1025,
            extra_ports=[8025],
            storage_gb=storage_gb,
            cpu_limit=cpu_limit,
            mount_path="/data",
        )

        service = db.query(UserService).filter(UserService.id == instance_name).first()
        if not service:
            service = UserService(
                id=instance_name,
                name=instance_name,
                tag="smtp",
                tag_color="text-kube",
                ready_pods=1,
                total_pods=1,
                status="Running",
                restarts=0,
                image="axllent/mailpit:latest",
                namespace=target_ns,
                endpoint=endpoint,
                cpu_usage=f"20m / {cpu_limit}",
                memory_usage="32MB / 256MB",
            )
            db.add(service)
        else:
            service.status = "Running"

        db.commit()
        db.refresh(service)
        log_process(db, instance_name, "DEPLOY_SMTP", "SUCCESS", f"[PyroSMTP] Active at '{endpoint}' (Web UI: :8025)")
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

    async def add_database(self, db: Session, service_id: str, db_name: str, db_user: Optional[str] = None, db_password: Optional[str] = None) -> Any:
        return None

    async def get_status(self, db: Session, service_id: str) -> Dict[str, Any]:
        service = db.query(UserService).filter(UserService.id == service_id).first()
        return {"service_id": service_id, "status": service.status if service else "Unknown"}
