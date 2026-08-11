from typing import List, Optional
from sqlalchemy.orm import Session

from models.cron import CronJobRecord
from services.k8s import get_k8s_client
from services.logger import log_process


class PyroKubeCronService:
    """
    Kubernetes CronJobs Provisioning & Management Engine.
    Creates, deletes, and manages scheduled background tasks and database backups.
    """

    @staticmethod
    def create_cronjob(
        db: Session,
        name: str,
        schedule: str,
        target_service: str,
        command: str,
        image: str = "alpine:latest",
    ) -> CronJobRecord:
        log_process(db, name, "CREATE_CRON", "INFO", f"Provisioning Kubernetes CronJob '{name}' (Schedule: {schedule})")

        is_connected, v1, _ = get_k8s_client()
        namespace = f"pyro-{target_service}"

        if is_connected and v1:
            try:
                from kubernetes import client

                batch_v1 = client.BatchV1Api()
                labels = {"app": name, "pyrokube/cron": "true"}

                # Ensure namespace exists
                try:
                    v1.create_namespace(body=client.V1Namespace(metadata=client.V1ObjectMeta(name=namespace)))
                except Exception:
                    pass

                cron_manifest = client.V1CronJob(
                    metadata=client.V1ObjectMeta(name=name, namespace=namespace, labels=labels),
                    spec=client.V1CronJobSpec(
                        schedule=schedule,
                        job_template=client.V1JobTemplateSpec(
                            spec=client.V1JobSpec(
                                template=client.V1PodTemplateSpec(
                                    metadata=client.V1ObjectMeta(labels=labels),
                                    spec=client.V1PodSpec(
                                        restart_policy="OnFailure",
                                        containers=[
                                            client.V1Container(
                                                name=name,
                                                image=image,
                                                command=["sh", "-c", command],
                                            )
                                        ],
                                    ),
                                )
                            )
                        ),
                    ),
                )

                try:
                    batch_v1.create_namespaced_cron_job(namespace=namespace, body=cron_manifest)
                    log_process(db, name, "CREATE_CRON", "SUCCESS", f"Kubernetes CronJob '{name}' created on VPS cluster")
                except client.exceptions.ApiException as e:
                    if e.status == 409:
                        batch_v1.patch_namespaced_cron_job(name=name, namespace=namespace, body=cron_manifest)
                    else:
                        log_process(db, name, "CREATE_CRON", "WARNING", f"CronJob K8s notice: {str(e)}")
            except Exception as e:
                log_process(db, name, "CREATE_CRON", "WARNING", f"CronJob K8s error: {str(e)}")

        record = db.query(CronJobRecord).filter(CronJobRecord.name == name).first()
        if not record:
            record = CronJobRecord(
                name=name,
                schedule=schedule,
                target_service=target_service,
                command=command,
                status="Active",
            )
            db.add(record)
        else:
            record.schedule = schedule
            record.command = command
            record.status = "Active"

        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def delete_cronjob(db: Session, name: str) -> bool:
        log_process(db, name, "DELETE_CRON", "INFO", f"Deleting CronJob '{name}'")
        record = db.query(CronJobRecord).filter(CronJobRecord.name == name).first()
        if record:
            target_service = record.target_service
            is_connected, v1, _ = get_k8s_client()
            if is_connected:
                try:
                    from kubernetes import client

                    batch_v1 = client.BatchV1Api()
                    batch_v1.delete_namespaced_cron_job(name=name, namespace=f"pyro-{target_service}")
                except Exception:
                    pass
            db.delete(record)
            db.commit()
            return True
        return False
