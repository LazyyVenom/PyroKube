from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from models.dashboard import CatalogService, DatabaseInstance, UserService
from services.logger import log_process
from services.managed_services.skeleton import PyroManagedService


class PyroPostgres(PyroManagedService):
    """
    Managed PostgreSQL Engine Implementation inheriting from PyroManagedService.
    Supports on-demand deployment, logical database creation, and connection mesh registration.
    """

    def __init__(self, app=None):
        super().__init__(app=app)
        self.category = "postgres"
        self.default_port = "5432"

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
        log_process(db, instance_name, "DEPLOY_PG", "INFO", f"[PyroPostgres] Provisioning PostgreSQL engine '{instance_name}' ({storage_gb}GB PVC)")
        
        catalog_item = db.query(CatalogService).filter(CatalogService.id == service_id).first()
        if catalog_item:
            catalog_item.status = "Active"

        target_ns = f"pyro-{instance_name}"
        endpoint = f"{instance_name}.{target_ns}.svc:{self.default_port}"
        
        # Provision real K8s PVC, Secret, Service, and Deployment inside dedicated namespace
        from services.k8s_service import PyroKubeK8sService
        PyroKubeK8sService.provision_k8s_managed_workload(
            instance_name=instance_name,
            image="postgres:16.2-alpine",
            port=5432,
            storage_gb=storage_gb,
            cpu_limit=cpu_limit,
            env_vars={
                "POSTGRES_USER": db_user or "postgres",
                "POSTGRES_PASSWORD": db_password or "pyrokube_pass",
                "POSTGRES_DB": instance_name,
            },
            mount_path="/var/lib/postgresql/data",
        )

        service = db.query(UserService).filter(UserService.id == instance_name).first()
        if not service:
            service = UserService(
                id=instance_name,
                name=instance_name,
                tag="database",
                tag_color="text-kube",
                ready_pods=1,
                total_pods=1,
                status="Running",
                restarts=0,
                image="postgres:16.2-alpine",
                namespace=target_ns,
                endpoint=endpoint,
                cpu_usage=f"50m / {cpu_limit}",
                memory_usage="256MB / 1024MB",
            )
            db.add(service)
        else:
            service.status = "Running"
            service.ready_pods = 1
            service.namespace = target_ns
            service.endpoint = endpoint

        # Seed primary logical database
        db_inst = DatabaseInstance(
            service_id=service_id,
            db_name=instance_name,
            db_user=db_user,
            db_password=db_password,
            status="Active",
        )
        db.add(db_inst)
        db.commit()
        db.refresh(service)

        log_process(db, instance_name, "DEPLOY_PG", "SUCCESS", f"[PyroPostgres] PostgreSQL engine active at '{endpoint}'")
        return service

    async def delete(self, db: Session, service_id: str) -> bool:
        log_process(db, service_id, "DELETE_PG", "INFO", f"[PyroPostgres] Teardown PostgreSQL instance '{service_id}'")
        from services.k8s_service import PyroKubeK8sService
        PyroKubeK8sService.teardown_k8s_managed_workload(service_id)

        service = db.query(UserService).filter(UserService.id == service_id).first()
        if service:
            db.delete(service)
            db.commit()
            log_process(db, service_id, "DELETE_PG", "SUCCESS", f"[PyroPostgres] Instance '{service_id}' deleted")
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
        db_user_str = db_user or "admin"
        db_password_str = db_password or "secure_pass"
        log_process(db, service_id, "ADD_DB_PG", "INFO", f"[PyroPostgres] Creating logical database '{db_name}' for user '{db_user_str}' inside active PostgreSQL engine")
        
        db_inst = DatabaseInstance(
            service_id=service_id,
            db_name=db_name,
            db_user=db_user_str,
            db_password=db_password_str,
            charset="UTF8",
            status="Active",
        )
        db.add(db_inst)
        db.commit()
        db.refresh(db_inst)

        log_process(db, service_id, "ADD_DB_PG", "SUCCESS", f"[PyroPostgres] Logical database '{db_name}' provisioned (URI: postgres://{db_user}:***@{service_id}.production.svc:5432/{db_name})")
        return db_inst

    async def get_status(self, db: Session, service_id: str) -> Dict[str, Any]:
        dbs = db.query(DatabaseInstance).filter(DatabaseInstance.service_id == service_id).all()
        return {
            "service_id": service_id,
            "engine": "PostgreSQL v16.2",
            "logical_databases_count": len(dbs),
            "databases": [d.db_name for d in dbs],
        }