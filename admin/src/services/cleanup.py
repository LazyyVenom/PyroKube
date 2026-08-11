import os
import shutil
import subprocess
from typing import Dict, Any
from sqlalchemy.orm import Session

from services.logger import log_process


def prune_server_storage(db: Session) -> Dict[str, Any]:
    """
    Cleans up server storage:
    1. Removes temporary git workspace build caches (/tmp/pyrokube/builds/*).
    2. Prunes unused/dangling containerd & docker container images.
    3. Reclaims host disk space.
    """
    log_process(db, "server", "CLEANUP", "INFO", "Initiating PyroKube server & containerd image storage cleanup")

    reclaimed_bytes = 0

    # 1. Clean workspace build directory
    workspace_base = "/tmp/pyrokube/builds"
    if os.path.exists(workspace_base):
        try:
            for item in os.listdir(workspace_base):
                item_path = os.path.join(workspace_base, item)
                if os.path.isfile(item_path) or os.path.islink(item_path):
                    reclaimed_bytes += os.path.getsize(item_path)
                    os.unlink(item_path)
                elif os.path.isdir(item_path):
                    for root, _, files in os.walk(item_path):
                        reclaimed_bytes += sum(os.path.getsize(os.path.join(root, f)) for f in files)
                    shutil.rmtree(item_path, ignore_errors=True)
            log_process(db, "server", "CLEANUP", "SUCCESS", f"Cleared temporary build workspace cache in '{workspace_base}'")
        except Exception as e:
            log_process(db, "server", "CLEANUP", "WARNING", f"Workspace cache cleanup note: {str(e)}")

    # 2. Prune dangling containerd / docker images
    image_prune_cmds = [
        "crictl rmi --prune",
        "k3s crictl rmi --prune",
        "docker image prune -f",
        "podman image prune -f"
    ]

    pruned_summary = []
    for cmd in image_prune_cmds:
        try:
            res = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res.returncode == 0 and res.stdout.strip():
                pruned_summary.append(cmd)
        except Exception:
            pass

    reclaimed_mb = round(reclaimed_bytes / (1024 * 1024), 2)
    log_process(db, "server", "CLEANUP", "SUCCESS", f"Server cleanup complete. Reclaimed ~{reclaimed_mb} MB disk space")

    return {
        "status": "Success",
        "reclaimed_mb": reclaimed_mb,
        "pruned_commands": pruned_summary,
    }
