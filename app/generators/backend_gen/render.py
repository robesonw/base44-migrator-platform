"""Simple string templates for backend code generation (Jinja2-free)."""


def render_main_py() -> str:
    """Generate app/main.py content."""
    return """from fastapi import FastAPI
from app.api.health import router as health_router

app = FastAPI(title="Generated Backend API", version="0.1.0")

app.include_router(health_router, prefix="/api")
"""


def render_api_init() -> str:
    """Generate app/api/__init__.py content."""
    return """\"\"\"API routes package.\"\"\"
"""


def render_api_health() -> str:
    """Generate app/api/health.py content."""
    return """from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def health():
    return {"status": "ok"}
"""


def render_core_config() -> str:
    """Generate app/core/config.py content."""
    return """from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    
    app_name: str = "backend-api"
    api_host: str = "0.0.0.0"
    api_port: int = 8080

settings = Settings()
"""


def render_requirements_txt() -> str:
    """Generate requirements.txt content."""
    return """fastapi==0.115.6
uvicorn[standard]==0.30.6
pydantic==2.9.2
pydantic-settings==2.5.2
"""


def render_dockerfile() -> str:
    """Generate Dockerfile content."""
    return """FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
"""


def render_docker_compose() -> str:
    """Generate docker-compose.yml content."""
    return """services:
  api:
    build: .
    ports:
      - "8080:8080"
    environment:
      - APP_NAME=backend-api
"""


def render_readme() -> str:
    """Generate README.md content."""
    return """# Generated Backend API

This is a generated FastAPI backend skeleton.

## Running the API

Using Docker Compose:
```bash
docker compose up --build
```

Using uvicorn directly:
```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

## API Endpoints

- `GET /api/health` - Health check endpoint
"""

