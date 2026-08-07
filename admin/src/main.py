from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from core.config import STATIC_DIR
from core.db import init_db
from routers import auth, base, dashboard


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

app.include_router(base.router)
app.include_router(auth.router)
app.include_router(dashboard.router)


@app.exception_handler(HTTPException)
async def redirect_handler(request: Request, exc: HTTPException):
    location = (exc.headers or {}).get("Location")

    if location and request.headers.get("HX-Request"):
        return HTMLResponse(headers={"HX-Redirect": location})

    if location:
        return RedirectResponse(url=location, status_code=exc.status_code)

    return HTMLResponse(content=exc.detail, status_code=exc.status_code)
