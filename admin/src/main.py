from fastapi import FastAPI, APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from routers import auth, base

from core.auth import require_admin
from core.config import STATIC_DIR

app = FastAPI()


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

admin_router = APIRouter(dependencies=[Depends(require_admin)])
app.include_router(auth.router)
app.include_router(base.router)
app.include_router(admin_router)


@app.exception_handler(HTTPException)
async def htmx_redirect_handler(request: Request, exc: HTTPException):
    if exc.status_code == status.HTTP_307_TEMPORARY_REDIRECT and request.headers.get(
        "HX-Request"
    ):
        return HTMLResponse(headers={"HX-Redirect": exc.headers.get("Location")})

    return HTMLResponse(content=exc.detail, status_code=exc.status_code)
