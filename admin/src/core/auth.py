from fastapi import Request, status, HTTPException
from core.settings import setting

COOKIE_NAME = setting.COOKIE_NAME
ADMIN_PASSWORD = setting.ADMIN_PSWD


def require_admin(request: Request):
    session: str = request.cookies.get(COOKIE_NAME)
    if not session or session != ADMIN_PASSWORD:
        
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/login"},
        )
    return session
