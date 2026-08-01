from fastapi import APIRouter, Request, Form, status
from fastapi.responses import RedirectResponse
import asyncio

from core.config import templates
from core.settings import setting

ADMIN_PSWD = setting.ADMIN_PSWD
COOKIE_NAME = setting.COOKIE_NAME

router = APIRouter()


@router.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(request, "pages/login.html")


@router.post("/login")
async def login_submit(password: str = Form(...)):
    if password == ADMIN_PSWD:
        response = RedirectResponse(
            url="/dashboard", status_code=status.HTTP_303_SEE_OTHER
        )
        response.set_cookie(key=COOKIE_NAME, value=ADMIN_PSWD, httponly=True)
        return response

    await asyncio.sleep(3.0)
    return RedirectResponse(
        url="/auth/login?error=invalid", status_code=status.HTTP_303_SEE_OTHER
    )


@router.get("/logout")
def logout():
    response = RedirectResponse(
        url="/auth/login", status_code=status.HTTP_303_SEE_OTHER
    )
    response.delete_cookie(COOKIE_NAME)
    return response
