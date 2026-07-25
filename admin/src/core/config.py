import os
from fastapi.templating import Jinja2Templates

CURRENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(CURRENT_DIR, "templates")
STATIC_DIR = os.path.join(CURRENT_DIR, "static")


templates = Jinja2Templates(directory=TEMPLATES_DIR)
