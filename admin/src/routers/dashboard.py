import time

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy.orm import Session

from core.auth import require_admin, token_expiry
from core.config import templates
from core.db import get_db
from core.settings import setting
from models.dashboard import CatalogService, ServerStatus, UserService
from utils.format import humanize_seconds

router = APIRouter(dependencies=[Depends(require_admin)])

STATUS_ORDER = {"Failed": 0, "Active": 1, "InActive": 2}


@router.get("/dashboard")
def dashboard(request: Request, db: Session = Depends(get_db)):
    server_status = db.query(ServerStatus).first()
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
    server_status = db.query(ServerStatus).first()
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
    service = db.query(UserService).filter(UserService.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    action_lower = action.lower()
    if action_lower == "stop":
        service.status = "Stopped"
        service.ready_pods = 0
    elif action_lower == "start":
        service.status = "Running"
        service.ready_pods = service.total_pods
    elif action_lower == "restart":
        service.status = "Running"
        service.ready_pods = service.total_pods
        service.restarts += 1

    db.commit()

    user_services = db.query(UserService).all()
    return templates.TemplateResponse(
        request,
        "components/running_containers.html",
        {"user_services": user_services},
    )


@router.get("/dashboard/status")
def dashboard_status(request: Request):
    expires_at = token_expiry(request.cookies.get(setting.COOKIE_NAME))
    remaining = expires_at - int(time.time()) if expires_at else 0

    return templates.TemplateResponse(
        request,
        "partials/status.html",
        {"remaining": humanize_seconds(remaining)},
    )
