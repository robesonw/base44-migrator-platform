#!/usr/bin/env python3
"""
FrontendRefactorAgent - Refactor Base44 frontend to use generated FastAPI backend.

This script:
1. Creates a checkpoint branch in target repo
2. Clones source repo and copies frontend to target
3. Replaces Base44 dependencies with REST API client
4. Maps UI calls to REST endpoints
5. Sets up dev workflow
6. Creates PR
"""

import os
import re
import shutil
import logging
import tempfile
from pathlib import Path
from git import Repo
import httpx
import asyncio

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Configuration
SOURCE_REPO_URL = "https://github.com/robesonw/culinary-compass.git"
TARGET_REPO_URL = "https://github.com/robesonw/cc.git"
TARGET_BASE_BRANCH = "main"
BRANCH_NAME = "feat/frontend-wiring"
API_BASE_URL = "http://localhost:8081"
FRONTEND_PORT = 5173


def get_github_token():
    """Get GitHub token from environment."""
    return os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")


def parse_repo_url(repo_url: str) -> tuple[str, str]:
    """Parse GitHub repo URL to extract owner and repo name."""
    pattern = r"(?:https?://github\.com/|git@github\.com:)([^/]+)/([^/]+?)(?:\.git)?$"
    match = re.match(pattern, repo_url)
    if match:
        return match.group(1), match.group(2)
    raise ValueError(f"Could not parse repo URL: {repo_url}")


async def create_pr(
    github_token: str,
    repo_url: str,
    base_branch: str,
    head_branch: str,
    title: str,
    body: str,
) -> str | None:
    """Create a PR via GitHub API. Returns PR URL or None."""
    try:
        owner, repo_name = parse_repo_url(repo_url)
        url = f"https://api.github.com/repos/{owner}/{repo_name}/pulls"
        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        data = {
            "title": title,
            "head": head_branch,
            "base": base_branch,
            "body": body,
        }
        
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(url, headers=headers, json=data)
            r.raise_for_status()
            pr_data = r.json()
            return pr_data.get("html_url") or pr_data.get("url", "")
    except Exception as e:
        log.error(f"Failed to create PR: {e}")
        return None


def git_checkpoint_1(target_dir: Path) -> Repo:
    """GitCommitter checkpoint #1: Clone target repo and create branch."""
    log.info(f"Step 1: Creating checkpoint in target repo...")
    
    # Clone target repo if needed
    if target_dir.exists() and any(target_dir.iterdir()):
        log.info(f"Target repo already exists at {target_dir}, reusing it")
        repo = Repo(target_dir)
    else:
        log.info(f"Cloning target repo {TARGET_REPO_URL} to {target_dir}")
        repo = Repo.clone_from(TARGET_REPO_URL, target_dir)
    
    # Checkout base branch
    try:
        repo.git.checkout(TARGET_BASE_BRANCH)
        repo.git.pull("origin", TARGET_BASE_BRANCH)
    except Exception as e:
        log.warning(f"Could not checkout/pull {TARGET_BASE_BRANCH}: {e}")
    
    # Create or checkout branch
    if BRANCH_NAME in [h.name for h in repo.heads]:
        log.info(f"Branch {BRANCH_NAME} already exists, checking it out")
        repo.git.checkout(BRANCH_NAME)
    else:
        log.info(f"Creating branch {BRANCH_NAME}")
        repo.git.checkout("-b", BRANCH_NAME)
    
    # Ensure backend/ and migrator-artifacts/ are committed
    repo.git.add("backend/", "migrator-artifacts/")
    if repo.is_dirty():
        repo.index.commit("chore: ensure backend and migrator-artifacts are committed")
        log.info("Committed existing backend and migrator-artifacts")
    
    # Push branch
    try:
        repo.git.push("origin", BRANCH_NAME, set_upstream=True)
        log.info(f"Pushed branch {BRANCH_NAME} to origin")
    except Exception as e:
        log.warning(f"Could not push branch (may need manual push): {e}")
    
    return repo


def copy_frontend(source_dir: Path, target_dir: Path):
    """Copy frontend from source repo to target repo."""
    log.info(f"Step 2: Copying frontend from {source_dir} to {target_dir}/frontend")
    
    frontend_dest = target_dir / "frontend"
    
    # Determine what to copy (look for package.json, vite.config, src/)
    if (source_dir / "package.json").exists():
        # Frontend is at root
        frontend_src = source_dir
    elif (source_dir / "frontend" / "package.json").exists():
        # Frontend is in a frontend/ subdirectory
        frontend_src = source_dir / "frontend"
    else:
        raise ValueError("Could not find frontend (package.json) in source repo")
    
    # Remove existing frontend if present
    if frontend_dest.exists():
        log.info(f"Removing existing frontend directory: {frontend_dest}")
        shutil.rmtree(frontend_dest)
    
    # Copy frontend
    log.info(f"Copying frontend from {frontend_src} to {frontend_dest}")
    shutil.copytree(frontend_src, frontend_dest, ignore=shutil.ignore_patterns(
        ".git", "node_modules", ".next", "dist", "build", ".cache"
    ))
    
    log.info("Frontend copied successfully")


def replace_base44_dependencies(frontend_dir: Path):
    """Replace Base44 dependencies with REST API client."""
    log.info("Step 3: Replacing Base44 dependencies...")
    
    # Create new API client
    api_dir = frontend_dir / "src" / "api"
    api_dir.mkdir(parents=True, exist_ok=True)
    
    client_code = '''// API Client for REST backend
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8081';

export interface ApiError {
  message: string;
  status?: number;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error: ApiError = {
      message: `HTTP error! status: ${response.status}`,
      status: response.status,
    };
    try {
      const errorData = await response.json();
      error.message = errorData.detail || errorData.message || error.message;
    } catch {
      // Ignore JSON parse errors
    }
    throw error;
  }
  
  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }
  
  return response.json();
}

export class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  async get<T>(path: string, params?: Record<string, string | number | undefined>): Promise<T> {
    const url = new URL(path, this.baseUrl);
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          url.searchParams.append(key, String(value));
        }
      });
    }
    const response = await fetch(url.toString(), {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    return handleResponse<T>(response);
  }

  async post<T>(path: string, data?: unknown): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: data ? JSON.stringify(data) : undefined,
    });
    return handleResponse<T>(response);
  }

  async patch<T>(path: string, data?: unknown): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: data ? JSON.stringify(data) : undefined,
    });
    return handleResponse<T>(response);
  }

  async put<T>(path: string, data?: unknown): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: data ? JSON.stringify(data) : undefined,
    });
    return handleResponse<T>(response);
  }

  async delete<T>(path: string): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    return handleResponse<T>(response);
  }
}

export const apiClient = new ApiClient();
'''
    
    client_file = api_dir / "client.ts"
    client_file.write_text(client_code, encoding="utf-8")
    log.info(f"Created API client at {client_file}")
    
    # Create .env.example
    env_example = frontend_dir / ".env.example"
    env_example.write_text(
        f"VITE_API_BASE_URL={API_BASE_URL}\n",
        encoding="utf-8"
    )
    log.info(f"Created .env.example at {env_example}")


def to_kebab_case(name: str) -> str:
    """Convert PascalCase or camelCase to kebab-case."""
    # Insert hyphen before uppercase letters (except the first)
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1-\2', name)
    # Insert hyphen before uppercase letters that follow lowercase
    s2 = re.sub('([a-z0-9])([A-Z])', r'\1-\2', s1)
    return s2.lower()


def entity_to_slug(entity_name: str) -> str:
    """Convert entity name to API slug (kebab-case)."""
    return to_kebab_case(entity_name)


def find_and_replace_base44_usage(frontend_dir: Path):
    """Find and replace Base44 client usage with new API client."""
    log.info("Step 4: Finding and replacing Base44 usage...")
    
    # Find all files that might use base44
    base44_files = []
    for ext in ["*.js", "*.jsx", "*.ts", "*.tsx"]:
        base44_files.extend(frontend_dir.rglob(ext))
    
    replacements_made = 0
    for file_path in base44_files:
        if "node_modules" in str(file_path) or "api/client" in str(file_path):
            continue
        
        try:
            content = file_path.read_text(encoding="utf-8")
            original_content = content
            
            # Replace imports: base44 from '@/api/base44Client' or similar
            content = re.sub(
                r"import\s+\{[^}]*base44[^}]*\}\s+from\s+['\"][^'\"]*base44Client['\"]",
                "import { apiClient } from '@/api/client'",
                content
            )
            content = re.sub(
                r"import\s+base44\s+from\s+['\"][^'\"]*base44Client['\"]",
                "import { apiClient } from '@/api/client'",
                content
            )
            content = re.sub(
                r"import\s+\{.*base44.*\}\s+from\s+['\"][^'\"]*base44Client['\"]",
                "import { apiClient } from '@/api/client'",
                content
            )
            
            # Map base44.entities.{EntityName}.list() to apiClient.get('/api/{slug}')
            # Pattern: base44.entities.EntityName.list(params?)
            def replace_list(match):
                entity_name = match.group(1)
                params = match.group(2) if match.group(2) else ""
                slug = entity_to_slug(entity_name)
                # Handle sort params like '-created_date' -> convert to query params
                if params and params.strip():
                    # If it's a simple sort string like '-created_date', convert to query param
                    sort_param = params.strip().strip("'\"")
                    if sort_param.startswith('-'):
                        # Descending sort
                        return f"apiClient.get('/api/{slug}', {{ sort: '{sort_param[1:]}', order: 'desc' }})"
                    else:
                        return f"apiClient.get('/api/{slug}', {{ sort: '{sort_param}', order: 'asc' }})"
                return f"apiClient.get('/api/{slug}')"
            
            content = re.sub(
                r"base44\.entities\.([A-Za-z][A-Za-z0-9]*)\.list\(([^)]*)\)",
                replace_list,
                content
            )
            
            # Map base44.entities.{EntityName}.create(data) to apiClient.post('/api/{slug}', data)
            content = re.sub(
                r"base44\.entities\.([A-Za-z][A-Za-z0-9]*)\.create\(([^)]+)\)",
                lambda m: f"apiClient.post('/api/{entity_to_slug(m.group(1))}', {m.group(2)})",
                content
            )
            
            # Map base44.entities.{EntityName}.get(id) to apiClient.get('/api/{slug}/{id}')
            content = re.sub(
                r"base44\.entities\.([A-Za-z][A-Za-z0-9]*)\.get\(([^)]+)\)",
                lambda m: f"apiClient.get(`/api/{entity_to_slug(m.group(1))}/${{{m.group(2).strip()}}}`)",
                content
            )
            
            # Map base44.entities.{EntityName}.update(id, data) to apiClient.patch('/api/{slug}/{id}', data)
            content = re.sub(
                r"base44\.entities\.([A-Za-z][A-Za-z0-9]*)\.update\(([^,]+),\s*([^)]+)\)",
                lambda m: f"apiClient.patch(`/api/{entity_to_slug(m.group(1))}/${{{m.group(2).strip()}}}`, {m.group(3)})",
                content
            )
            
            # Map base44.entities.{EntityName}.delete(id) to apiClient.delete('/api/{slug}/{id}')
            content = re.sub(
                r"base44\.entities\.([A-Za-z][A-Za-z0-9]*)\.delete\(([^)]+)\)",
                lambda m: f"apiClient.delete(`/api/{entity_to_slug(m.group(1))}/${{{m.group(2).strip()}}}`)",
                content
            )
            
            # Map base44.entities.{EntityName}.filter(params) to apiClient.get('/api/{slug}', params)
            content = re.sub(
                r"base44\.entities\.([A-Za-z][A-Za-z0-9]*)\.filter\(([^)]+)\)",
                lambda m: f"apiClient.get('/api/{entity_to_slug(m.group(1))}', {m.group(2)})",
                content
            )
            
            # Handle auth calls - base44.auth.me() -> apiClient.get('/api/auth/me') or similar
            # Note: This depends on backend auth endpoint structure
            content = re.sub(
                r"base44\.auth\.me\(\)",
                "apiClient.get('/api/auth/me')",
                content
            )
            
            # Replace any remaining base44 references (fallback)
            content = re.sub(
                r"base44\.",
                "apiClient.",
                content
            )
            
            if content != original_content:
                file_path.write_text(content, encoding="utf-8")
                replacements_made += 1
                log.info(f"Updated {file_path.relative_to(frontend_dir)}")
        except Exception as e:
            log.warning(f"Could not process {file_path}: {e}")
    
    log.info(f"Made replacements in {replacements_made} files")
    
    # Remove base44Client.js if it exists
    base44_client_file = frontend_dir / "src" / "api" / "base44Client.js"
    if base44_client_file.exists():
        base44_client_file.unlink()
        log.info(f"Removed {base44_client_file}")


def map_ui_to_rest_endpoints(frontend_dir: Path):
    """Map UI data calls to REST endpoints."""
    log.info("Step 4: Mapping UI calls to REST endpoints...")
    
    # This is a placeholder - actual implementation would require:
    # 1. Parsing the UI code to find API calls
    # 2. Understanding entity slugs (kebab-case)
    # 3. Mapping Base44 collection calls to REST endpoints
    # 4. Adjusting payload shapes
    
    # For now, we'll create a helper document explaining the mapping
    mapping_doc = frontend_dir / "API_MIGRATION_NOTES.md"
    mapping_doc.write_text("""# API Migration Notes

This frontend has been migrated from Base44 to REST API endpoints.

## Endpoint Mapping

- Base44 collections → `/api/{entity-slug}`
- GET collection → `GET /api/{entity-slug}?limit=&offset=&q=`
- GET item → `GET /api/{entity-slug}/{id}`
- CREATE → `POST /api/{entity-slug}`
- UPDATE → `PATCH /api/{entity-slug}/{id}`
- DELETE → `DELETE /api/{entity-slug}/{id}`

## Entity Slugs

Entity slugs should be in kebab-case (e.g., `recipe-items`, `user-profiles`).

## Payload Shapes

- For CREATE: Use the Create model (omit optional fields or send null when needed)
- For UPDATE: Use the Update model (partial updates)

## Usage

```typescript
import { apiClient } from './api/client';

// List items
const items = await apiClient.get('/api/recipes', { limit: 10, offset: 0 });

// Get single item
const item = await apiClient.get(`/api/recipes/${id}`);

// Create
const newItem = await apiClient.post('/api/recipes', { name: '...', ... });

// Update
const updated = await apiClient.patch(`/api/recipes/${id}`, { name: '...' });

// Delete
await apiClient.delete(`/api/recipes/${id}`);
```
""", encoding="utf-8")
    log.info(f"Created migration notes at {mapping_doc}")


def setup_dev_workflow(target_dir: Path):
    """Set up development workflow and documentation."""
    log.info("Step 5: Setting up dev workflow...")
    
    # Update or create README
    readme_path = target_dir / "README.md"
    readme_content = """# Culinary Compass - Full Stack Application

This is a monorepo containing the backend and frontend for Culinary Compass.

## Structure

- `/backend` - FastAPI backend application
- `/frontend` - React/Vite frontend application
- `/migrator-artifacts` - Migration artifacts and documentation

## Development Setup

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ and npm
- Python 3.11+ (if running backend locally)

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Start the backend services:
   ```bash
   docker compose up --build
   ```

   This will start:
   - API server at `http://localhost:8081`
   - PostgreSQL on port `5433`
   - MongoDB on port `27018`

3. Verify the backend is running:
   ```bash
   curl http://localhost:8081/health
   ```

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Create a `.env` file (copy from `.env.example`):
   ```bash
   cp .env.example .env
   ```

4. Start the development server:
   ```bash
   npm run dev
   ```

   The frontend will be available at `http://localhost:5173`

### Running Everything

1. In one terminal, start the backend:
   ```bash
   cd backend && docker compose up
   ```

2. In another terminal, start the frontend:
   ```bash
   cd frontend && npm run dev
   ```

## Environment Variables

### Frontend

- `VITE_API_BASE_URL` - Base URL for the API (default: `http://localhost:8081`)

See `frontend/.env.example` for more details.

## API Documentation

Once the backend is running, API documentation is available at:
- Swagger UI: `http://localhost:8081/docs`
- ReDoc: `http://localhost:8081/redoc`

## Testing

### Backend Smoke Test

```bash
cd backend
docker compose up -d
sleep 5  # Wait for services to start
curl http://localhost:8081/health
```

### Frontend Smoke Test

1. Start backend (see above)
2. Start frontend: `cd frontend && npm run dev`
3. Open `http://localhost:5173` in your browser
4. Verify the frontend loads and can connect to the backend
"""
    
    if readme_path.exists():
        # Append to existing README if it exists
        existing = readme_path.read_text(encoding="utf-8")
        if "# Development Setup" not in existing:
            readme_path.write_text(existing + "\n\n" + readme_content, encoding="utf-8")
    else:
        readme_path.write_text(readme_content, encoding="utf-8")
    
    log.info(f"Updated README at {readme_path}")


def main():
    """Main execution function."""
    # Create temporary directory for cloning repos
    work_dir = Path(tempfile.mkdtemp(prefix="frontend_refactor_"))
    log.info(f"Working directory: {work_dir}")
    
    try:
        # Step 1: GitCommitter checkpoint #1
        target_dir = work_dir / "target"
        repo = git_checkpoint_1(target_dir)
        
        # Step 2: Clone source and copy frontend
        source_dir = work_dir / "source"
        if not source_dir.exists():
            log.info(f"Cloning source repo {SOURCE_REPO_URL} to {source_dir}")
            Repo.clone_from(SOURCE_REPO_URL, source_dir, depth=1)
        copy_frontend(source_dir, target_dir)
        
        frontend_dir = target_dir / "frontend"
        
        # Step 3: Replace Base44 dependencies
        replace_base44_dependencies(frontend_dir)
        
        # Step 4: Map UI calls to REST endpoints
        find_and_replace_base44_usage(frontend_dir)
        map_ui_to_rest_endpoints(frontend_dir)
        
        # Step 5: Dev workflow
        setup_dev_workflow(target_dir)
        
        # Step 6: Commit changes
        repo.git.add("frontend/", "README.md")
        if repo.is_dirty(untracked_files=True):
            repo.index.commit("feat: add frontend and wire to backend REST API")
            commit_hash = repo.head.commit.hexsha
            log.info(f"Committed changes with hash: {commit_hash}")
            
            # Push branch
            try:
                repo.git.push("origin", BRANCH_NAME)
                log.info(f"Pushed branch {BRANCH_NAME} to origin")
            except Exception as e:
                log.warning(f"Could not push branch: {e}")
        
        # Step 7: Create PR
        github_token = get_github_token()
        if github_token:
            pr_body = """# Frontend Wiring - Base44 to REST API Migration

This PR wires the frontend to the newly generated FastAPI backend.

## Changes

- Added `/frontend` directory with React/Vite application
- Replaced Base44 API client with REST API client
- Updated API calls to use `/api/{entity-slug}` endpoints
- Added development workflow documentation

## How to Run

### Backend
```bash
cd backend
docker compose up --build
```

### Frontend
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

## API Endpoints

The frontend now uses REST endpoints:
- `GET /api/{slug}` - List items (supports ?limit=&offset=&q=)
- `POST /api/{slug}` - Create item
- `GET /api/{slug}/{id}` - Get item
- `PATCH /api/{slug}/{id}` - Update item
- `DELETE /api/{slug}/{id}` - Delete item

## Environment Variables

- `VITE_API_BASE_URL` - Backend API base URL (default: http://localhost:8081)

## Next Steps

- Test CRUD operations for Postgres-backed entities
- Test CRUD operations for Mongo-backed entities
- Verify all UI functionality works with new backend
"""
            
            pr_url = asyncio.run(create_pr(
                github_token=github_token,
                repo_url=TARGET_REPO_URL,
                base_branch=TARGET_BASE_BRANCH,
                head_branch=BRANCH_NAME,
                title="feat: wire frontend to generated backend REST API",
                body=pr_body,
            ))
            
            if pr_url:
                log.info(f"✅ Created PR: {pr_url}")
            else:
                log.warning("Failed to create PR automatically")
        else:
            log.warning("No GitHub token found - skipping PR creation")
            log.info(f"Branch {BRANCH_NAME} is ready for manual PR creation")
        
        log.info(f"✅ Frontend refactoring complete! Work directory: {work_dir}")
        log.info(f"⚠️  Note: You may want to review and test the changes before merging")
        
    except Exception as e:
        log.exception(f"❌ Frontend refactoring failed: {e}")
        raise


if __name__ == "__main__":
    main()

