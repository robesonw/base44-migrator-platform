import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import text
from alembic.config import Config
from alembic import command
from app.core.config import settings
from app.core.logging import configure_logging
from app.api.routes import router as api_router
from app.db.session import engine

configure_logging()
log = logging.getLogger(__name__)


def wait_for_database(max_retries: int = 30, retry_delay: float = 1.0) -> None:
    """Wait for PostgreSQL database to be available."""
    for attempt in range(max_retries):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            log.info("Database connection successful", extra={"job_id": "-", "stage": "-"})
            return
        except Exception as e:
            if attempt < max_retries - 1:
                log.warning("Database not ready, retrying in %s seconds (attempt %d/%d): %s", 
                           retry_delay, attempt + 1, max_retries, e,
                           extra={"job_id": "-", "stage": "-"})
                time.sleep(retry_delay)
            else:
                log.error("Database connection failed after %d attempts", max_retries,
                         extra={"job_id": "-", "stage": "-"})
                raise


def run_migrations() -> None:
    """Run Alembic migrations to head."""
    try:
        log.info("Running database migrations...", extra={"job_id": "-", "stage": "-"})
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        log.info("Database migrations completed successfully", extra={"job_id": "-", "stage": "-"})
    except Exception as e:
        log.error("Database migration failed: %s", e, exc_info=True, extra={"job_id": "-", "stage": "-"})
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    log.info("Starting API server...", extra={"job_id": "-", "stage": "-"})
    try:
        wait_for_database()
        run_migrations()
        log.info("API server startup complete", extra={"job_id": "-", "stage": "-"})
    except Exception as e:
        log.error("API startup failed: %s", e, exc_info=True, extra={"job_id": "-", "stage": "-"})
        raise
    yield
    # Shutdown
    log.info("Shutting down API server...", extra={"job_id": "-", "stage": "-"})


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan
)
app.include_router(api_router, prefix="/v1")
