import time

from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from core.auth import require_admin, token_expiry
from core.config import templates
from core.db import get_db
from core.settings import setting
from models.audit import ProcessLog
from models.dashboard import CatalogService, ServerStatus, UserService
from services.k8s import get_cluster_telemetry
from services.k8s_service import PyroKubeK8sService
from utils.format import humanize_seconds

router = APIRouter(dependencies=[Depends(require_admin)])

STATUS_ORDER = {"Failed": 0, "Active": 1, "InActive": 2}


def sync_telemetry_status(db: Session) -> ServerStatus:
    telemetry = get_cluster_telemetry()
    status = db.query(ServerStatus).first()
    if not status:
        status = ServerStatus(id=1)
        db.add(status)

    status.nodes_healthy = telemetry.get("nodes_healthy", 3)
    status.nodes_total = telemetry.get("nodes_total", 3)
    status.api_server_status = telemetry.get("api_server_status", "Ready")
    status.cpu_usage_pct = telemetry.get("cpu_usage_pct", 18)
    status.cpu_cores = telemetry.get("cpu_cores", 12)
    status.memory_used_gb = telemetry.get("memory_used_gb", 4.2)
    status.memory_max_gb = telemetry.get("memory_max_gb", 32.0)
    status.storage_used_gb = telemetry.get("storage_used_gb", 120)
    status.storage_max_gb = telemetry.get("storage_max_gb", 500)
    status.storage_assigned_gb = telemetry.get("storage_assigned_gb", 250)
    status.cpu_allocated_m = telemetry.get("cpu_allocated_m", 800)
    status.memory_allocated_gb = telemetry.get("memory_allocated_gb", 0.6)

    db.commit()
    db.refresh(status)

    # Pre-calculate UI percentages for clean template rendering
    status.cpu_allocated_pct = round((status.cpu_allocated_m / status.cpu_cores) * 100, 1) if status.cpu_cores else 0
    status.mem_pct = round((status.memory_used_gb / status.memory_max_gb) * 100, 1) if status.memory_max_gb else 0
    status.mem_allocated_pct = round((status.memory_allocated_gb / status.memory_max_gb) * 100, 1) if status.memory_max_gb else 0
    status.storage_used_pct = round((status.storage_used_gb / status.storage_max_gb) * 100, 1) if status.storage_max_gb else 0
    status.storage_assigned_pct = round((status.storage_assigned_gb / status.storage_max_gb) * 100, 1) if status.storage_max_gb else 0

    status.cpu_pct_css = f"{status.cpu_usage_pct or 0}%"
    status.mem_pct_css = f"{status.mem_pct or 0}%"
    status.storage_used_pct_css = f"{status.storage_used_pct or 0}%"
    status.cpu_allocated_pct_css = f"{status.cpu_allocated_pct or 0}%"
    status.mem_allocated_pct_css = f"{status.mem_allocated_pct or 0}%"
    status.storage_assigned_pct_css = f"{status.storage_assigned_pct or 0}%"

    return status


@router.get("/dashboard")
def dashboard(request: Request, db: Session = Depends(get_db)):
    server_status = sync_telemetry_status(db)
    user_services = db.query(UserService).all()
    catalog_services = db.query(CatalogService).all()
    sorted_catalog = sorted(catalog_services, key=lambda s: STATUS_ORDER.get(s.status, 3))

    return templates.TemplateResponse(
        request,
        "pages/dashboard.html",
        {
            "server_status": server_status,
            "user_services": user_services,
            "services": sorted_catalog,
        },
    )


@router.get("/dashboard/server-status")
def server_status_partial(request: Request, db: Session = Depends(get_db)):
    server_status = sync_telemetry_status(db)
    return templates.TemplateResponse(
        request,
        "components/server_status.html",
        {"server_status": server_status},
    )


@router.get("/dashboard/user-services")
def user_services_partial(request: Request, db: Session = Depends(get_db)):
    user_services = db.query(UserService).all()
    return templates.TemplateResponse(
        request,
        "components/running_containers.html",
        {"user_services": user_services},
    )


@router.post("/dashboard/user-services/{service_id}/action")
def user_service_action(
    request: Request,
    service_id: str,
    action: str = Form(...),
    db: Session = Depends(get_db),
):
    action_lower = action.lower()
    if action_lower == "stop":
        PyroKubeK8sService.stop_service(db, service_id)
    elif action_lower == "start":
        PyroKubeK8sService.start_service(db, service_id)
    elif action_lower == "restart":
        PyroKubeK8sService.restart_service(db, service_id)

    user_services = db.query(UserService).all()
    return templates.TemplateResponse(
        request,
        "components/running_containers.html",
        {"user_services": user_services},
    )


@router.post("/dashboard/catalog/deploy")
async def deploy_catalog_service(
    request: Request,
    service_id: str = Form(...),
    instance_name: str = Form(...),
    storage_gb: int = Form(20),
    cpu_limit: str = Form("1000m"),
    db_user: Optional[str] = Form(None),
    db_password: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    await PyroKubeK8sService.deploy_managed_service(
        db=db,
        service_id=service_id,
        instance_name=instance_name,
        storage_gb=storage_gb,
        cpu_limit=cpu_limit,
        db_user=db_user,
        db_password=db_password,
    )

    user_services = db.query(UserService).all()
    return templates.TemplateResponse(
        request,
        "components/running_containers.html",
        {"user_services": user_services},
    )


@router.get("/dashboard/services/{service_id}/process-logs")
def get_service_process_logs(service_id: str, db: Session = Depends(get_db)):
    logs = (
        db.query(ProcessLog)
        .filter(ProcessLog.service_id == service_id)
        .order_by(ProcessLog.timestamp.asc())
        .all()
    )
    if not logs:
        return HTMLResponse(
            f"<div class='text-slate italic'>No process logs recorded for '{service_id}' yet.</div>"
        )

    html_items = []
    for entry in logs:
        level_color = "text-ok" if entry.level == "SUCCESS" else ("text-ember" if entry.level == "WARNING" else ("text-crit" if entry.level == "ERROR" else "text-paper-soft"))
        timestamp_str = entry.timestamp.strftime("%H:%M:%S")
        html_items.append(
            f"<div class='flex items-start gap-2.5 hover:bg-surface-alt/40 p-1 font-mono text-xs'>"
            f"<span class='text-slate text-[10px] whitespace-nowrap'>{timestamp_str}</span>"
            f"<span class='font-bold uppercase text-[10px] px-1 bg-surface-alt {level_color}'>{entry.level}</span>"
            f"<span class='text-paper font-medium'>{entry.message}</span>"
            f"</div>"
        )
    return HTMLResponse("".join(html_items))


@router.get("/dashboard/status")
def dashboard_status(request: Request):
    expires_at = token_expiry(request.cookies.get(setting.COOKIE_NAME))
    remaining = expires_at - int(time.time()) if expires_at else 0

    return templates.TemplateResponse(
        request,
        "partials/status.html",
        {"remaining": humanize_seconds(remaining)},
    )
