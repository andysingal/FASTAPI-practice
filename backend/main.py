from core.config import settings
from fastapi import FastAPI

app = FastAPI(title=settings.PROJECT_TITLE, version=settings.PROJECT_VERSION)


@app.get("/")
def hello():
    return {"msg": "Hello FastAPI"}
