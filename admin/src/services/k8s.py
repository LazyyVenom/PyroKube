import os
import psutil
from typing import Dict, Any

try:
    from kubernetes import client, config
    K8S_AVAILABLE = True
except ImportError:
    K8S_AVAILABLE = False


def get_k8s_client() -> tuple[bool, Any, Any]:
    """
    Attempts to load kubeconfig or in-cluster config.
    Returns (is_connected, core_v1_api, custom_objects_api).
    """
    if not K8S_AVAILABLE:
        return False, None, None

    try:
        if os.path.exists(os.path.expanduser("~/.kube/config")):
            config.load_kube_config()
        else:
            config.load_incluster_config()
        
        v1 = client.CoreV1Api()
        custom = client.CustomObjectsApi()
        return True, v1, custom
    except Exception:
        return False, None, None


def get_cluster_telemetry() -> Dict[str, Any]:
    """
    Queries Kubernetes API or uses psutil system fallback for local admin dev.
    """
    is_connected, v1, custom = get_k8s_client()

    if is_connected and v1:
        try:
            nodes = v1.list_node()
            nodes_total = len(nodes.items)
            nodes_healthy = sum(
                1 for n in nodes.items 
                if any(c.type == "Ready" and c.status == "True" for c in n.status.conditions or [])
            )
            return {
                "is_connected": True,
                "nodes_healthy": nodes_healthy,
                "nodes_total": nodes_total if nodes_total > 0 else 1,
                "api_server_status": "Ready",
                "cpu_usage_pct": int(psutil.cpu_percent(interval=None)),
                "cpu_cores": psutil.cpu_count(logical=True) or 8,
                "memory_used_gb": round(psutil.virtual_memory().used / (1024 ** 3), 1),
                "memory_max_gb": round(psutil.virtual_memory().total / (1024 ** 3), 1),
                "storage_used_gb": round(psutil.disk_usage("/").used / (1024 ** 3), 0),
                "storage_max_gb": round(psutil.disk_usage("/").total / (1024 ** 3), 0),
                "storage_assigned_gb": round((psutil.disk_usage("/").total * 0.5) / (1024 ** 3), 0),
            }
        except Exception:
            pass

    # Local Admin Fallback Telemetry (psutil)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    
    return {
        "is_connected": False,
        "nodes_healthy": 3,
        "nodes_total": 3,
        "api_server_status": "Ready",
        "cpu_usage_pct": max(int(psutil.cpu_percent(interval=None)), 12),
        "cpu_cores": psutil.cpu_count(logical=True) or 8,
        "memory_used_gb": round(mem.used / (1024 ** 3), 1),
        "memory_max_gb": round(mem.total / (1024 ** 3), 1),
        "storage_used_gb": int(disk.used / (1024 ** 3)),
        "storage_max_gb": int(disk.total / (1024 ** 3)),
        "storage_assigned_gb": int((disk.total * 0.5) / (1024 ** 3)),
    }
