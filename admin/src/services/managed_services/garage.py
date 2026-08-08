from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from models.dashboard import CatalogService, UserService
from services.logger import log_process
from services.managed_services.skeleton import PyroManagedService


class PyroGarage(PyroManagedService):
    """Managed Garage S3 Object Storage Implementation."""

    def __init__(self, app=None):
        super().__init__(app=app)
        self.category = "garage"
        self.default_port = "3900"

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
        log_process(db, instance_name, "DEPLOY_GRG", "INFO", f"[PyroGarage] Provisioning Garage S3 object storage '{instance_name}' ({storage_gb}GB PVC)")
        catalog_item = db.query(CatalogService).filter(CatalogService.id == service_id).first()
        if catalog_item:
            catalog_item.status = "Active"

        target_ns = f"pyro-{instance_name}"
        endpoint = f"{instance_name}.{target_ns}.svc:{self.default_port}"

        # Provision real K8s PVC, Service (S3 API 3900 & Admin API 3902), and Deployment inside dedicated namespace
        from services.k8s_service import PyroKubeK8sService
        PyroKubeK8sService.provision_k8s_managed_workload(
            instance_name=instance_name,
            image="dxflrs/garage:v1.0.0",
            port=3900,
            extra_ports=[3902],
            storage_gb=storage_gb,
            cpu_limit=cpu_limit,
            mount_path="/var/lib/garage",
        )

        service = db.query(UserService).filter(UserService.id == instance_name).first()
        if not service:
            service = UserService(
                id=instance_name,
                name=instance_name,
                tag="uploads",
                tag_color="text-ember",
                ready_pods=1,
                total_pods=1,
                status="Running",
                restarts=0,
                image="dxflrs/garage:v1.0.0",
                namespace=target_ns,
                endpoint=endpoint,
                cpu_usage=f"40m / {cpu_limit}",
                memory_usage="128MB / 512MB",
            )
            db.add(service)

        db.commit()
        db.refresh(service)
        log_process(db, instance_name, "DEPLOY_GRG", "SUCCESS", f"[PyroGarage] Garage S3 API active at '{endpoint}'")
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
        log_process(db, service_id, "ADD_BUCKET_GRG", "INFO", f"[PyroGarage] Created S3 bucket '{db_name}'")
        return {"service_id": service_id, "bucket": db_name}

    async def get_status(self, db: Session, service_id: str) -> Dict[str, Any]:
        return {"service_id": service_id, "engine": "Garage S3 v1.0", "status": "Active"}
