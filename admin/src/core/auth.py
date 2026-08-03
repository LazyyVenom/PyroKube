import hashlib
import hmac
import time

from fastapi import HTTPException, Request, status

from core.settings import setting

_SECRET = setting.SECRET_KEY.encode()


def _sign(payload: str) -> str:
    return hmac.new(_SECRET, payload.encode(), hashlib.sha256).hexdigest()


def check_password(candidate: str) -> bool:
    return hmac.compare_digest(candidate.encode(), setting.ADMIN_PSWD.encode())


def issue_token() -> str:
    expiry = str(int(time.time()) + setting.SESSION_TTL)
    return f"{expiry}.{_sign(expiry)}"


def token_expiry(token: str | None) -> int | None:
    if not token:
        return None

    expiry, separator, signature = token.partition(".")
    if not separator or not hmac.compare_digest(signature, _sign(expiry)):
        return None

    try:
        expires_at = int(expiry)
    except ValueError:
        return None

    return expires_at if expires_at > time.time() else None


def require_admin(request: Request) -> None:
    if token_expiry(request.cookies.get(setting.COOKIE_NAME)) is None:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/login"},
        )
