from typing import Optional, Tuple
from sqlalchemy.orm import Session

from core.settings import setting
from services.k8s import get_k8s_client
from services.logger import log_process


class PyroKubeIngressService:
    """
    Traefik Ingress Routing Engine for PyroKube.
    Provisions Kubernetes Ingress objects for auto-allotted wildcard subdomains (*.anubhav.fyi)
    and custom external domain attachments.
    """

    @staticmethod
    def provision_k8s_ingress(
        instance_name: str,
        port: int,
        custom_domain: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> Tuple[Optional[str], Optional[str]]:
        wildcard_host = f"{instance_name}.{setting.WILDCARD_DOMAIN}" if setting.WILDCARD_DOMAIN and setting.WILDCARD_DOMAIN.strip() else None
        namespace = f"pyro-{instance_name}"

        if db:
            msg = f"Provisioning Traefik Ingress routing (Wildcard: {wildcard_host}, Custom: {custom_domain})"
            log_process(db, instance_name, "INGRESS", "INFO", msg)

        is_connected, v1, _ = get_k8s_client()
        if is_connected and v1:
            try:
                from kubernetes import client

                networking_v1 = client.NetworkingV1Api()
                labels = {"app": instance_name, "pyrokube/ingress": "true"}
                rules = []

                if wildcard_host:
                    rules.append(
                        client.V1IngressRule(
                            host=wildcard_host,
                            http=client.V1HTTPIngressRuleValue(
                                paths=[
                                    client.V1HTTPIngressPath(
                                        path="/",
                                        path_type="Prefix",
                                        backend=client.V1IngressBackend(
                                            service=client.V1IngressServiceBackend(
                                                name=instance_name,
                                                port=client.V1ServiceBackendPort(number=port),
                                            )
                                        ),
                                    )
                                ]
                            ),
                        )
                    )

                if custom_domain and custom_domain.strip():
                    clean_custom = custom_domain.strip().lower()
                    rules.append(
                        client.V1IngressRule(
                            host=clean_custom,
                            http=client.V1HTTPIngressRuleValue(
                                paths=[
                                    client.V1HTTPIngressPath(
                                        path="/",
                                        path_type="Prefix",
                                        backend=client.V1IngressBackend(
                                            service=client.V1IngressServiceBackend(
                                                name=instance_name,
                                                port=client.V1ServiceBackendPort(number=port),
                                            )
                                        ),
                                    )
                                ]
                            ),
                        )
                    )

                if not rules:
                    return wildcard_host, custom_domain

                ingress_manifest = client.V1Ingress(
                    metadata=client.V1ObjectMeta(
                        name=f"{instance_name}-ingress",
                        namespace=namespace,
                        labels=labels,
                        annotations={
                            "traefik.ingress.kubernetes.io/router.entrypoints": "web,websecure",
                        },
                    ),
                    spec=client.V1IngressSpec(
                        ingress_class_name="traefik",
                        rules=rules,
                    ),
                )

                try:
                    networking_v1.create_namespaced_ingress(namespace=namespace, body=ingress_manifest)
                    if db:
                        log_process(db, instance_name, "INGRESS", "SUCCESS", f"Traefik Ingress active: http://{wildcard_host}")
                except client.exceptions.ApiException as e:
                    if e.status == 409:
                        networking_v1.patch_namespaced_ingress(
                            name=f"{instance_name}-ingress", namespace=namespace, body=ingress_manifest
                        )
                        if db:
                            log_process(db, instance_name, "INGRESS", "SUCCESS", f"Traefik Ingress updated: http://{wildcard_host}")
                    else:
                        if db:
                            log_process(db, instance_name, "INGRESS", "WARNING", f"Ingress notice: {str(e)}")
            except Exception as e:
                if db:
                    log_process(db, instance_name, "INGRESS", "WARNING", f"Ingress K8s error: {str(e)}")

        return wildcard_host, custom_domain

    @staticmethod
    def delete_k8s_ingress(instance_name: str) -> bool:
        is_connected, v1, _ = get_k8s_client()
        if is_connected:
            try:
                from kubernetes import client

                networking_v1 = client.NetworkingV1Api()
                networking_v1.delete_namespaced_ingress(
                    name=f"{instance_name}-ingress", namespace=f"pyro-{instance_name}"
                )
                return True
            except Exception:
                pass
        return False
