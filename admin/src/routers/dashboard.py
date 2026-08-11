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
            "current_page": "dashboard",
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


@router.get("/dashboard/deploy-user-app-modal")
def deploy_user_app_modal(request: Request):
    return templates.TemplateResponse(
        request,
        "components/deploy_user_app_modal.html",
        {},
    )


@router.post("/dashboard/deploy-user-app")
async def deploy_user_app(
    request: Request,
    service_name: str = Form(...),
    git_repo: str = Form(...),
    git_branch: str = Form("main"),
    dockerfile_path: str = Form("Dockerfile"),
    port: int = Form(8000),
    cpu_limit: str = Form("500m"),
    memory_limit: str = Form("512Mi"),
    db: Session = Depends(get_db),
):
    await PyroKubeK8sService.deploy_user_app_service(
        db=db,
        service_name=service_name,
        git_repo=git_repo,
        git_branch=git_branch,
        dockerfile_path=dockerfile_path,
        port=port,
        cpu_limit=cpu_limit,
        memory_limit=memory_limit,
    )

    user_services = db.query(UserService).all()
    return templates.TemplateResponse(
        request,
        "components/running_containers.html",
        {"user_services": user_services},
    )


@router.delete("/dashboard/services/{service_id}")
def delete_service(
    request: Request,
    service_id: str,
    db: Session = Depends(get_db),
):
    PyroKubeK8sService.teardown_k8s_managed_workload(service_id)
    service = db.query(UserService).filter(UserService.id == service_id).first()
    if service:
        db.delete(service)
        db.commit()

    user_services = db.query(UserService).all()
    return templates.TemplateResponse(
        request,
        "components/running_containers.html",
        {"user_services": user_services},
    )


@router.get("/dashboard/registry")
def registry_view(request: Request, db: Session = Depends(get_db)):
    from models.dashboard import ImageRegistryRecord
    records = db.query(ImageRegistryRecord).all()
    return templates.TemplateResponse(
        request,
        "components/registry_tab.html",
        {"registry_records": records},
    )


@router.post("/dashboard/server/prune")
def server_prune_action(request: Request, db: Session = Depends(get_db)):
    from services.cleanup import prune_server_storage
    res = prune_server_storage(db)
    server_status = sync_telemetry_status(db)
    return templates.TemplateResponse(
        request,
        "components/server_status.html",
        {"server_status": server_status, "cleanup_result": res},
    )


@router.get("/dashboard/domains/check-availability")
def check_subdomain_availability(
    request: Request,
    prefix: str,
    service_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    from services.ingress_service import PyroKubeIngressService
    clean_prefix = prefix.strip().lower().replace(" ", "-") if prefix else ""
    if not clean_prefix:
        return HTMLResponse("<span class='text-slate text-[10px] italic'>Type a subdomain prefix...</span>")

    target_host = f"{clean_prefix}.{setting.WILDCARD_DOMAIN}" if setting.WILDCARD_DOMAIN else clean_prefix
    is_available = PyroKubeIngressService.is_subdomain_available(db, clean_prefix, current_service_id=service_id)

    if is_available:
        return HTMLResponse(
            f"<span class='text-ok font-bold text-[11px] flex items-center gap-1'>🟢 <b>{target_host}</b> is Available!</span>"
        )
    else:
        return HTMLResponse(
            f"<span class='text-crit font-bold text-[11px] flex items-center gap-1'>🔴 <b>{target_host}</b> is Occupied / Taken!</span>"
        )


@router.post("/dashboard/services/domain/attach")
def attach_custom_domain(
    request: Request,
    service_id: str = Form(...),
    subdomain_prefix: Optional[str] = Form(None),
    custom_domain: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    service = db.query(UserService).filter(UserService.id == service_id).first()
    if service:
        from services.ingress_service import PyroKubeIngressService
        wildcard_host, custom_host = PyroKubeIngressService.provision_k8s_ingress(
            instance_name=service.id,
            port=service.port if hasattr(service, "port") and service.port else 8000,
            custom_domain=custom_domain,
            subdomain_prefix=subdomain_prefix,
            db=db,
        )
        service.wildcard_domain = wildcard_host
        service.custom_domain = custom_host
        db.commit()
        db.refresh(service)

    user_services = db.query(UserService).all()
    return templates.TemplateResponse(
        request,
        "components/running_containers.html",
        {"user_services": user_services},
    )


@router.get("/dashboard/domains-page")
def domains_page_view(request: Request, db: Session = Depends(get_db)):
    user_services = db.query(UserService).all()
    return templates.TemplateResponse(
        request,
        "pages/domains_page.html",
        {
            "user_services": user_services,
            "wildcard_domain": setting.WILDCARD_DOMAIN,
            "current_page": "domains",
        },
    )


@router.get("/dashboard/registry-page")
def registry_page_view(request: Request, db: Session = Depends(get_db)):
    from models.dashboard import ImageRegistryRecord
    records = db.query(ImageRegistryRecord).all()
    return templates.TemplateResponse(
        request,
        "pages/registry_page.html",
        {"registry_records": records, "current_page": "registry"},
    )


@router.get("/dashboard/cleanup-page")
def cleanup_page_view(request: Request, db: Session = Depends(get_db)):
    server_status = sync_telemetry_status(db)
    cleanup_logs = (
        db.query(ProcessLog)
        .filter(ProcessLog.action == "CLEANUP")
        .order_by(ProcessLog.id.desc())
        .limit(20)
        .all()
    )
    return templates.TemplateResponse(
        request,
        "pages/cleanup_page.html",
        {"server_status": server_status, "cleanup_logs": cleanup_logs, "current_page": "cleanup"},
    )


@router.get("/dashboard/crons-page")
def crons_page_view(request: Request, db: Session = Depends(get_db)):
    from models.cron import CronJobRecord
    cron_records = db.query(CronJobRecord).all()
    return templates.TemplateResponse(
        request,
        "pages/crons_page.html",
        {"cron_records": cron_records, "current_page": "crons"},
    )


@router.post("/dashboard/crons/create")
def crons_create_action(
    request: Request,
    name: str = Form(...),
    schedule: str = Form("0 2 * * *"),
    target_service: str = Form(...),
    command: str = Form(...),
    db: Session = Depends(get_db),
):
    from services.cron_service import PyroKubeCronService
    PyroKubeCronService.create_cronjob(
        db=db,
        name=name,
        schedule=schedule,
        target_service=target_service,
        command=command,
    )
    from models.cron import CronJobRecord
    cron_records = db.query(CronJobRecord).all()
    return templates.TemplateResponse(
        request,
        "pages/crons_page.html",
        {"cron_records": cron_records},
    )


@router.post("/dashboard/crons/delete")
def crons_delete_action(
    request: Request,
    cron_name: str = Form(...),
    db: Session = Depends(get_db),
):
    from services.cron_service import PyroKubeCronService
    PyroKubeCronService.delete_cronjob(db, cron_name)
    from models.cron import CronJobRecord
    cron_records = db.query(CronJobRecord).all()
    return templates.TemplateResponse(
        request,
        "pages/crons_page.html",
        {"cron_records": cron_records},
    )
