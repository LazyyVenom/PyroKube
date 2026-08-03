import asyncio

from fastapi import APIRouter, Form, Request, status
from fastapi.responses import RedirectResponse

from core.auth import check_password, issue_token, token_expiry
from core.config import templates
from core.settings import setting

router = APIRouter()


@router.get("/login")
def login_page(request: Request):
    if token_expiry(request.cookies.get(setting.COOKIE_NAME)) is not None:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
        request,
        "pages/login.html",
        {"error": request.query_params.get("error")},
    )


@router.post("/login")
async def login_submit(password: str = Form(...)):
    if not check_password(password):
        await asyncio.sleep(3.0)
        return RedirectResponse(
            url="/login?error=invalid", status_code=status.HTTP_303_SEE_OTHER
        )

    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key=setting.COOKIE_NAME,
        value=issue_token(),
        max_age=setting.SESSION_TTL,
        httponly=True,
        samesite="lax",
        secure=setting.COOKIE_SECURE,
    )
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(setting.COOKIE_NAME)
    return response
