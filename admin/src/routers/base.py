from fastapi import APIRouter, Request

from core.config import templates

router = APIRouter()


@router.get("/")
def home(request: Request):
    return templates.TemplateResponse(request, "pages/landing.html")
