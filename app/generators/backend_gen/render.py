"""Simple string templates for backend code generation (Jinja2-free)."""
from typing import List, Dict


def render_main_py(entity_routers: List[Dict[str, str]] = None) -> str:
    """Generate app/main.py content.
    
    Args:
        entity_routers: List of dicts with 'entity_slug' and 'path_slug' keys
    """
    if entity_routers is None:
        entity_routers = []
    
    lines = [
        "from fastapi import FastAPI",
        "from app.api.health import router as health_router",
        "",
        "app = FastAPI(title=\"Generated Backend API\", version=\"0.1.0\")",
        "",
        "app.include_router(health_router, prefix=\"/api\")",
        "",
    ]
    
    for router_info in entity_routers:
        entity_slug = router_info["entity_slug"]
        path_slug = router_info["path_slug"]
        lines.append(f"from app.api.entities.{entity_slug} import router as {entity_slug}_router")
        lines.append(f'app.include_router({entity_slug}_router, prefix="/api/{path_slug}", tags=["{router_info.get("entity_name", entity_slug)}"])')
        lines.append("")
    
    return "\n".join(lines)


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


def render_repos_base() -> str:
    """Generate app/repos/base.py content."""
    return """from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from uuid import UUID

class CRUDRepository(ABC):
    @abstractmethod
    async def list(self, limit: int = 100, offset: int = 0, q: Optional[str] = None) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    async def get(self, id: str) -> Optional[Dict[str, Any]]:
        pass
    
    @abstractmethod
    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    async def replace(self, id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    async def patch(self, id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    async def delete(self, id: str) -> bool:
        pass
"""


def render_repos_postgres_repo() -> str:
    """Generate app/repos/postgres_repo.py content."""
    return """from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import uuid
import json
from app.db.postgres import get_db

class PostgresRepo:
    def __init__(self, table_name: str, columns: List[Dict[str, Any]]):
        self.table_name = table_name
        self.columns = columns
    
    async def _ensure_table(self, session: AsyncSession):
        column_defs = ["id TEXT PRIMARY KEY", "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP", "updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"]
        for col in self.columns:
            col_name = col["name"]
            if col_name == "id":
                continue
            col_type = self._map_type(col)
            if col.get("required", False) and not col.get("nullable", False):
                column_defs.append(f'"{col_name}" {col_type} NOT NULL')
            else:
                column_defs.append(f'"{col_name}" {col_type}')
        
        create_table_sql = f\"\"\"CREATE TABLE IF NOT EXISTS {self.table_name} (
            {', '.join(column_defs)}
        )\"\"\"
        await session.execute(text(create_table_sql))
        await session.commit()
    
    def _map_type(self, col: Dict[str, Any]) -> str:
        col_type = col.get("type", "string")
        if col_type in ("object", "array"):
            return "JSONB"
        elif col_type == "string":
            return "TEXT"
        elif col_type == "number":
            return "NUMERIC"
        elif col_type == "boolean":
            return "BOOLEAN"
        elif col_type == "datetime":
            return "TIMESTAMP"
        else:
            return "TEXT"
    
    async def list(self, limit: int = 100, offset: int = 0, q: Optional[str] = None) -> Dict[str, Any]:
        async for session in get_db():
            await self._ensure_table(session)
            params = {"limit": limit, "offset": offset}
            query = f'SELECT * FROM {self.table_name}'
            conditions = []
            if q:
                text_cols = [col["name"] for col in self.columns if col.get("type") == "string"]
                conditions = [f'"{col}" ILIKE :q' for col in text_cols]
                if conditions:
                    query += f' WHERE {" OR ".join(conditions)}'
                params["q"] = f"%{q}%"
            query += ' LIMIT :limit OFFSET :offset'
            result = await session.execute(text(query), params)
            rows = result.fetchall()
            items = [dict(row._mapping) for row in rows]
            
            count_query = f'SELECT COUNT(*) as count FROM {self.table_name}'
            if q and conditions:
                count_query += f' WHERE {" OR ".join(conditions)}'
                count_result = await session.execute(text(count_query), {"q": f"%{q}%"})
            else:
                count_result = await session.execute(text(count_query))
            total = count_result.scalar()
            return {"items": items, "total": total}
    
    async def get(self, id: str) -> Optional[Dict[str, Any]]:
        async for session in get_db():
            await self._ensure_table(session)
            query = text(f'SELECT * FROM {self.table_name} WHERE id = :id')
            result = await session.execute(query, {"id": id})
            row = result.fetchone()
            return dict(row._mapping) if row else None
    
    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        async for session in get_db():
            await self._ensure_table(session)
            data["id"] = data.get("id") or str(uuid.uuid4())
            data["created_at"] = datetime.utcnow()
            data["updated_at"] = datetime.utcnow()
            
            cols = list(data.keys())
            placeholders = ", ".join([f":{col}" for col in cols])
            col_names = ", ".join([f'"{col}"' for col in cols])
            query = text(f'INSERT INTO {self.table_name} ({col_names}) VALUES ({placeholders}) RETURNING *')
            result = await session.execute(query, data)
            await session.commit()
            row = result.fetchone()
            return dict(row._mapping)
    
    async def replace(self, id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        async for session in get_db():
            await self._ensure_table(session)
            data["id"] = id
            data["updated_at"] = datetime.utcnow()
            
            set_clause = ", ".join([f'"{k}" = :{k}' for k in data.keys() if k != "id"])
            query = text(f'UPDATE {self.table_name} SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = :id RETURNING *')
            result = await session.execute(query, data)
            await session.commit()
            row = result.fetchone()
            if not row:
                raise ValueError(f"Entity with id {id} not found")
            return dict(row._mapping)
    
    async def patch(self, id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        async for session in get_db():
            await self._ensure_table(session)
            data["updated_at"] = datetime.utcnow()
            
            set_clause = ", ".join([f'"{k}" = :{k}' for k in data.keys() if k != "id"])
            query = text(f'UPDATE {self.table_name} SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = :id RETURNING *')
            result = await session.execute(query, {**data, "id": id})
            await session.commit()
            row = result.fetchone()
            if not row:
                raise ValueError(f"Entity with id {id} not found")
            return dict(row._mapping)
    
    async def delete(self, id: str) -> bool:
        async for session in get_db():
            await self._ensure_table(session)
            query = text(f'DELETE FROM {self.table_name} WHERE id = :id')
            result = await session.execute(query, {"id": id})
            await session.commit()
            return result.rowcount > 0
"""


def render_repos_mongo_repo() -> str:
    """Generate app/repos/mongo_repo.py content."""
    return """from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import uuid4
from app.db.mongo import get_database, get_collection

class MongoRepo:
    def __init__(self, collection_name: str):
        self.collection_name = collection_name
    
    def _get_collection(self):
        db = get_database()
        return get_collection(db, self.collection_name)
    
    async def list(self, limit: int = 100, offset: int = 0, q: Optional[str] = None) -> Dict[str, Any]:
        collection = self._get_collection()
        query = {}
        if q:
            query = {"$or": [{"_id": {"$regex": q, "$options": "i"}}]}
        
        cursor = collection.find(query).skip(offset).limit(limit)
        items = await cursor.to_list(length=limit)
        total = await collection.count_documents(query)
        
        for item in items:
            item["id"] = item.pop("_id", str(uuid4()))
        
        return {"items": items, "total": total}
    
    async def get(self, id: str) -> Optional[Dict[str, Any]]:
        collection = self._get_collection()
        doc = await collection.find_one({"_id": id})
        if doc:
            doc["id"] = doc.pop("_id")
        return doc
    
    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        collection = self._get_collection()
        doc_id = data.get("id") or str(uuid4())
        data["_id"] = doc_id
        data.pop("id", None)
        data["created_at"] = datetime.utcnow()
        data["updated_at"] = datetime.utcnow()
        
        await collection.insert_one(data)
        data["id"] = data.pop("_id")
        return data
    
    async def replace(self, id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        collection = self._get_collection()
        data["_id"] = id
        data.pop("id", None)
        data["updated_at"] = datetime.utcnow()
        
        result = await collection.replace_one({"_id": id}, data, upsert=False)
        if result.matched_count == 0:
            raise ValueError(f"Entity with id {id} not found")
        
        data["id"] = data.pop("_id")
        return data
    
    async def patch(self, id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        collection = self._get_collection()
        data["updated_at"] = datetime.utcnow()
        
        result = await collection.update_one({"_id": id}, {"$set": data})
        if result.matched_count == 0:
            raise ValueError(f"Entity with id {id} not found")
        
        doc = await collection.find_one({"_id": id})
        if doc:
            doc["id"] = doc.pop("_id")
        return doc
    
    async def delete(self, id: str) -> bool:
        collection = self._get_collection()
        result = await collection.delete_one({"_id": id})
        return result.deleted_count > 0
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

## Example API Usage

### Postgres Entity Example

```bash
# List entities
curl http://localhost:8080/api/user-link?limit=10&offset=0

# Create entity
curl -X POST http://localhost:8080/api/user-link \\
  -H "Content-Type: application/json" \\
  -d '{"user_id": "123", "target_id": "456"}'

# Get entity
curl http://localhost:8080/api/user-link/{id}

# Update entity
curl -X PUT http://localhost:8080/api/user-link/{id} \\
  -H "Content-Type: application/json" \\
  -d '{"user_id": "123", "target_id": "789"}'

# Delete entity
curl -X DELETE http://localhost:8080/api/user-link/{id}
```

### Mongo Entity Example

```bash
# List entities
curl http://localhost:8080/api/recipe?limit=10&offset=0&q=chicken

# Create entity
curl -X POST http://localhost:8080/api/recipe \\
  -H "Content-Type: application/json" \\
  -d '{"title": "Chicken Curry", "ingredients": [{"name": "chicken", "qty": 500}]}'

# Get entity
curl http://localhost:8080/api/recipe/{id}

# Update entity
curl -X PATCH http://localhost:8080/api/recipe/{id} \\
  -H "Content-Type: application/json" \\
  -d '{"title": "Updated Recipe"}'

# Delete entity
curl -X DELETE http://localhost:8080/api/recipe/{id}
```
"""

