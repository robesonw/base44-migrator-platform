from fastapi import FastAPI
from app.core.config import settings
from app.core.logging import configure_logging
from app.api.routes import router as api_router

configure_logging()

app = FastAPI(title=settings.app_name, version="0.1.0")
app.include_router(api_router, prefix="/v1")
