from fastapi import APIRouter, Request, status
from fastapi.responses import RedirectResponse

from core.config import templates

router = APIRouter()


@router.get("/")
def home(request: Request):
    return templates.TemplateResponse(request, "pages/landing.html")
