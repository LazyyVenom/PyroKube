from fastapi import FastAPI, APIRouter, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from admin.src.core.auth import require_admin

app = FastAPI()


app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

admin_router = APIRouter(dependencies=[Depends(require_admin)])