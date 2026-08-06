import os

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from core.config import STATIC_DIR, templates

router = APIRouter()


@router.get("/")
def home(request: Request):
    return templates.TemplateResponse(request, "pages/landing.html")


@router.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse(os.path.join(STATIC_DIR, "assets", "favicon.ico"))
