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
    
    postgres_url: str
    mongo_url: str
    mongo_db: str

settings = Settings()
"""


def render_requirements_txt() -> str:
    """Generate requirements.txt content."""
    return """fastapi==0.115.6
uvicorn[standard]==0.30.6
pydantic==2.9.2
pydantic-settings==2.5.2
sqlalchemy[asyncio]==2.0.36
asyncpg==0.30.0
motor==3.6.0
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
      - POSTGRES_URL=postgresql+asyncpg://app:app@postgres:5432/app
      - MONGO_URL=mongodb://mongo:27017
      - MONGO_DB=app
    depends_on:
      postgres:
        condition: service_healthy
      mongo:
        condition: service_healthy

  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: app
      POSTGRES_DB: app
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app -d app"]
      interval: 5s
      timeout: 5s
      retries: 5

  mongo:
    image: mongo:7
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db
    healthcheck:
      test: echo 'db.runCommand("ping").ok' | mongosh localhost:27017/test --quiet
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
  mongo_data:
"""


def render_db_postgres() -> str:
    """Generate app/db/postgres.py content."""
    return """from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings

engine = create_async_engine(settings.postgres_url, echo=False, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
"""


def render_db_mongo() -> str:
    """Generate app/db/mongo.py content."""
    return """from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

client = AsyncIOMotorClient(settings.mongo_url)

def get_database():
    return client[settings.mongo_db]

def get_collection(db, name: str):
    return db[name]
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

