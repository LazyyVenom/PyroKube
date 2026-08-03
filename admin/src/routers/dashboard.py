import time

from fastapi import APIRouter, Depends, Request

from core.auth import require_admin, token_expiry
from core.config import templates
from core.settings import setting
from utils.format import humanize_seconds

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/dashboard")
def dashboard(request: Request):
    return templates.TemplateResponse(request, "pages/dashboard.html")


@router.get("/dashboard/status")
def dashboard_status(request: Request):
    expires_at = token_expiry(request.cookies.get(setting.COOKIE_NAME))
    remaining = expires_at - int(time.time()) if expires_at else 0

    return templates.TemplateResponse(
        request,
        "partials/status.html",
        {"remaining": humanize_seconds(remaining)},
    )
