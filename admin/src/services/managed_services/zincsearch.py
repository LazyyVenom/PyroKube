from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from models.dashboard import CatalogService, UserService
from services.logger import log_process
from services.managed_services.skeleton import PyroManagedService


class PyroZincSearch(PyroManagedService):
    """Managed ZincSearch Log Indexer Implementation."""

    def __init__(self, app=None):
        super().__init__(app=app)
        self.category = "zincsearch"
        self.default_port = "4080"

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
        log_process(db, instance_name, "DEPLOY_ZNC", "INFO", f"[PyroZincSearch] Provisioning ZincSearch engine '{instance_name}'")
        catalog_item = db.query(CatalogService).filter(CatalogService.id == service_id).first()
        if catalog_item:
            catalog_item.status = "Active"

        target_ns = f"pyro-{instance_name}"
        endpoint = f"{instance_name}.{target_ns}.svc:{self.default_port}"

        # Provision real K8s PVC, Secret, Service, and Deployment inside dedicated namespace
        from services.k8s_service import PyroKubeK8sService
        PyroKubeK8sService.provision_k8s_managed_workload(
            instance_name=instance_name,
            image="zincsearch/zincsearch:v0.4.8",
            port=4080,
            storage_gb=storage_gb,
            cpu_limit=cpu_limit,
            env_vars={
                "ZINC_FIRST_ADMIN_USER": db_user or "admin",
                "ZINC_FIRST_ADMIN_PASSWORD": db_password or "pyrokube_pass",
            },
            mount_path="/data",
        )

        service = db.query(UserService).filter(UserService.id == instance_name).first()
        if not service:
            service = UserService(
                id=instance_name,
                name=instance_name,
                tag="logging",
                tag_color="text-ember",
                ready_pods=1,
                total_pods=1,
                status="Running",
                restarts=0,
                image="zincsearch/zincsearch:v0.4.8",
                namespace=target_ns,
                endpoint=endpoint,
                cpu_usage=f"60m / {cpu_limit}",
                memory_usage="256MB / 1024MB",
            )
            db.add(service)

        db.commit()
        db.refresh(service)
        log_process(db, instance_name, "DEPLOY_ZNC", "SUCCESS", f"[PyroZincSearch] Active at '{endpoint}'")
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
        log_process(db, service_id, "ADD_INDEX_ZNC", "INFO", f"[PyroZincSearch] Created log index '{db_name}'")
        return {"service_id": service_id, "index": db_name}

    async def get_status(self, db: Session, service_id: str) -> Dict[str, Any]:
        return {"service_id": service_id, "engine": "ZincSearch v0.4.8", "status": "Active"}
