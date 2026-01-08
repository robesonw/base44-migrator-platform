#!/bin/bash
set -e

# Configuration
JOB_ID="${JOB_ID:-generated_backend_smoke}"
SOURCE_REPO_URL="${SOURCE_REPO_URL:-https://github.com/robesonw/culinary-compass.git}"
OUT_DIR="${OUT_DIR:-test_output/${JOB_ID}/workspace}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PYTHONPATH="${PROJECT_ROOT}"

# Cleanup function
cleanup() {
    local exit_code=$?
    echo ""
    echo "=== Cleanup ==="
    
    BACKEND_DIR="${PROJECT_ROOT}/${OUT_DIR}/generated/backend"
    if [ -d "${BACKEND_DIR}" ]; then
        echo "Stopping docker compose..."
        cd "${BACKEND_DIR}"
        docker compose down -v 2>/dev/null || true
    fi
    
    if [ $exit_code -ne 0 ]; then
        echo "Script failed with exit code $exit_code"
    fi
    exit $exit_code
}

trap cleanup EXIT INT TERM

echo "=== Generated Backend Smoke Test ==="
echo "JOB_ID: ${JOB_ID}"
echo "SOURCE_REPO_URL: ${SOURCE_REPO_URL}"
echo "OUT_DIR: ${OUT_DIR}"
echo ""

# Step 1: Create clean output directory
echo "=== Step 1: Creating clean output directory ==="
OUT_DIR_ABS="${PROJECT_ROOT}/${OUT_DIR}"
rm -rf "${OUT_DIR_ABS}"
mkdir -p "${OUT_DIR_ABS}/workspace"
mkdir -p "${OUT_DIR_ABS}/source"
ARTIFACTS_DIR="${OUT_DIR_ABS}/workspace"
SOURCE_DIR="${OUT_DIR_ABS}/source"
echo "Created: ${OUT_DIR_ABS}"
echo ""

# Step 2: Run generator pipeline
echo "=== Step 2: Running generator pipeline ==="
cd "${PROJECT_ROOT}"
export PYTHONPATH="${PROJECT_ROOT}"

python3 -c "
import json
from pathlib import Path
from unittest.mock import MagicMock
from git import Repo
from app.agents.impl_intake import RepoIntakeAgent
from app.agents.impl_design import DomainModelerAgent, ApiDesignerAgent
from app.agents.impl_build import BackendBuilderAgent

source_repo = '${SOURCE_REPO_URL}'
source_dir = Path('${SOURCE_DIR}')
artifacts_dir = Path('${ARTIFACTS_DIR}')
workspace_root = Path('${OUT_DIR_ABS}')

class MockWorkspace:
    def __init__(self, root, source_dir, artifacts_dir):
        self.root = root
        self.source_dir = source_dir
        self.artifacts_dir = artifacts_dir

mock_ws = MockWorkspace(workspace_root, source_dir, artifacts_dir)

# Clone source repository
print('  Cloning source repository...')
if source_dir.exists() and any(source_dir.iterdir()):
    print('    Source directory already exists, skipping clone')
else:
    Repo.clone_from(source_repo, source_dir, depth=1)
    print('    Cloned successfully')

# Run RepoIntakeAgent
print('  Running RepoIntakeAgent...')
mock_job = MagicMock()
mock_job.source_repo_url = source_repo
intake_agent = RepoIntakeAgent()
intake_result = intake_agent.run(mock_job, mock_ws)
if not intake_result.ok:
    print(f'    ERROR: {intake_result.message}')
    exit(1)
print(f'    {intake_result.message}')

# Run DomainModelerAgent
print('  Running DomainModelerAgent...')
domain_job = MagicMock()
domain_job.db_stack = 'hybrid'
domain_job.artifacts = {'db_preferences': {'hybridStrategy': 'docToMongo'}}
domain_job.id = '${JOB_ID}'
domain_result = DomainModelerAgent().run(domain_job, mock_ws)
if not domain_result.ok:
    print(f'    ERROR: {domain_result.message}')
    exit(1)
print(f'    {domain_result.message}')

# Run ApiDesignerAgent
print('  Running ApiDesignerAgent...')
api_job = MagicMock()
api_job.source_repo_url = source_repo
api_result = ApiDesignerAgent().run(api_job, mock_ws)
if not api_result.ok:
    print(f'    ERROR: {api_result.message}')
    exit(1)
print(f'    {api_result.message}')

# Run BackendBuilderAgent
print('  Running BackendBuilderAgent...')
backend_job = MagicMock()
backend_job.id = '${JOB_ID}'
backend_result = BackendBuilderAgent().run(backend_job, mock_ws)
if not backend_result.ok:
    print(f'    ERROR: {backend_result.message}')
    exit(1)
print(f'    {backend_result.message}')
"

if [ $? -ne 0 ]; then
    echo "ERROR: Generator pipeline failed"
    exit 1
fi
echo ""

# Step 3: Verify generated backend exists
echo "=== Step 3: Verifying generated backend ==="
BACKEND_DIR="${OUT_DIR_ABS}/generated/backend"
if [ ! -d "${BACKEND_DIR}" ]; then
    echo "ERROR: Generated backend directory not found: ${BACKEND_DIR}"
    exit 1
fi
echo "Backend directory exists: ${BACKEND_DIR}"
echo ""

# Step 4: Change to backend directory
echo "=== Step 4: Changing to backend directory ==="
cd "${BACKEND_DIR}"
echo "Current directory: $(pwd)"
echo ""

# Step 5: Start docker compose
echo "=== Step 5: Starting docker compose ==="
docker compose up -d --build
if [ $? -ne 0 ]; then
    echo "ERROR: docker compose up failed"
    exit 1
fi
echo "Docker compose started"
echo ""

# Step 6: Wait for health endpoint
echo "=== Step 6: Waiting for health endpoint ==="
MAX_ATTEMPTS=60
ATTEMPT=0
HEALTH_URL="http://localhost:8081/api/health"
while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if curl -s -f "${HEALTH_URL}" > /dev/null 2>&1; then
        echo "Health check passed"
        break
    fi
    ATTEMPT=$((ATTEMPT + 1))
    if [ $ATTEMPT -ge $MAX_ATTEMPTS ]; then
        echo "ERROR: Health check failed after ${MAX_ATTEMPTS} attempts"
        docker compose logs api
        exit 1
    fi
    echo "Waiting for API... (attempt ${ATTEMPT}/${MAX_ATTEMPTS})"
    sleep 2
done
echo ""

# Step 7: Select entities from storage-plan.json
echo "=== Step 7: Selecting entities from storage-plan.json ==="
STORAGE_PLAN_PATH="${ARTIFACTS_DIR}/storage-plan.json"
if [ ! -f "${STORAGE_PLAN_PATH}" ]; then
    echo "ERROR: storage-plan.json not found: ${STORAGE_PLAN_PATH}"
    exit 1
fi

# Use Python to parse storage-plan and select entities
ENTITY_INFO=$(python3 -c "
import json
import sys
from pathlib import Path
from app.generators.backend_gen.utils import entity_to_path

storage_plan_path = Path('${STORAGE_PLAN_PATH}')
with open(storage_plan_path, 'r') as f:
    storage_plan = json.load(f)

postgres_entity = None
mongo_entity = None

for entity in storage_plan.get('entities', []):
    if postgres_entity is None and entity.get('store') == 'postgres':
        postgres_entity = entity['name']
    if mongo_entity is None and entity.get('store') == 'mongo':
        mongo_entity = entity['name']
    if postgres_entity and mongo_entity:
        break

if not postgres_entity:
    print('ERROR: No postgres entity found', file=sys.stderr)
    sys.exit(1)
if not mongo_entity:
    print('ERROR: No mongo entity found', file=sys.stderr)
    sys.exit(1)

postgres_slug = entity_to_path(postgres_entity)
mongo_slug = entity_to_path(mongo_entity)

print(f'{postgres_entity}|{postgres_slug}|{mongo_entity}|{mongo_slug}')
")

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to select entities"
    exit 1
fi

POSTGRES_ENTITY=$(echo "${ENTITY_INFO}" | cut -d'|' -f1)
POSTGRES_SLUG=$(echo "${ENTITY_INFO}" | cut -d'|' -f2)
MONGO_ENTITY=$(echo "${ENTITY_INFO}" | cut -d'|' -f3)
MONGO_SLUG=$(echo "${ENTITY_INFO}" | cut -d'|' -f4)

echo "Selected Postgres entity: ${POSTGRES_ENTITY} (slug: ${POSTGRES_SLUG})"
echo "Selected Mongo entity: ${MONGO_ENTITY} (slug: ${MONGO_SLUG})"
echo ""

# Step 8: CRUD tests
echo "=== Step 8: Running CRUD tests ==="
API_BASE="http://localhost:8081/api"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
VERIFICATION_LOG="${ARTIFACTS_DIR}/verification.md"
ENDPOINTS_CALLED=()
STATUS_CODES=()

# Function to log endpoint call
log_endpoint() {
    local method=$1
    local endpoint=$2
    local status=$3
    ENDPOINTS_CALLED+=("${method} ${endpoint}")
    STATUS_CODES+=("${status}")
    echo "  ${method} ${endpoint} -> ${status}"
}

# Build payloads using Python helper
echo "Building payloads..."
POSTGRES_PAYLOAD=$(python3 -c "
import sys
from pathlib import Path
from app.generators.backend_gen.smoke_payload import build_minimal_payload
import json

ui_contract_path = Path('${ARTIFACTS_DIR}/ui-contract.json')
entity_name = '${POSTGRES_ENTITY}'
payload = build_minimal_payload(ui_contract_path, entity_name)
print(json.dumps(payload))
")

MONGO_PAYLOAD=$(python3 -c "
import sys
from pathlib import Path
from app.generators.backend_gen.smoke_payload import build_minimal_payload
import json

ui_contract_path = Path('${ARTIFACTS_DIR}/ui-contract.json')
entity_name = '${MONGO_ENTITY}'
payload = build_minimal_payload(ui_contract_path, entity_name)
print(json.dumps(payload))
")

# Test Postgres entity
echo ""
echo "Testing Postgres entity: ${POSTGRES_ENTITY}"
POSTGRES_ENDPOINT="${API_BASE}/${POSTGRES_SLUG}"

# POST
echo "  Creating ${POSTGRES_ENTITY}..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${POSTGRES_ENDPOINT}" \
    -H "Content-Type: application/json" \
    -d "${POSTGRES_PAYLOAD}")
HTTP_BODY=$(echo "${RESPONSE}" | head -n -1)
HTTP_CODE=$(echo "${RESPONSE}" | tail -n 1)
log_endpoint "POST" "${POSTGRES_ENDPOINT}" "${HTTP_CODE}"
if [ "${HTTP_CODE}" -ne 201 ]; then
    echo "ERROR: POST failed with status ${HTTP_CODE}"
    echo "Response: ${HTTP_BODY}"
    exit 1
fi
POSTGRES_ID=$(echo "${HTTP_BODY}" | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))")

# GET list
echo "  Listing ${POSTGRES_ENTITY}..."
RESPONSE=$(curl -s -w "\n%{http_code}" "${POSTGRES_ENDPOINT}")
HTTP_BODY=$(echo "${RESPONSE}" | head -n -1)
HTTP_CODE=$(echo "${RESPONSE}" | tail -n 1)
log_endpoint "GET" "${POSTGRES_ENDPOINT}" "${HTTP_CODE}"
if [ "${HTTP_CODE}" -ne 200 ]; then
    echo "ERROR: GET list failed with status ${HTTP_CODE}"
    exit 1
fi

# GET by ID
echo "  Getting ${POSTGRES_ENTITY} by ID..."
RESPONSE=$(curl -s -w "\n%{http_code}" "${POSTGRES_ENDPOINT}/${POSTGRES_ID}")
HTTP_BODY=$(echo "${RESPONSE}" | head -n -1)
HTTP_CODE=$(echo "${RESPONSE}" | tail -n 1)
log_endpoint "GET" "${POSTGRES_ENDPOINT}/${POSTGRES_ID}" "${HTTP_CODE}"
if [ "${HTTP_CODE}" -ne 200 ]; then
    echo "ERROR: GET by ID failed with status ${HTTP_CODE}"
    exit 1
fi

# PATCH
echo "  Updating ${POSTGRES_ENTITY}..."
PATCH_PAYLOAD="{}"
RESPONSE=$(curl -s -w "\n%{http_code}" -X PATCH "${POSTGRES_ENDPOINT}/${POSTGRES_ID}" \
    -H "Content-Type: application/json" \
    -d "${PATCH_PAYLOAD}")
HTTP_BODY=$(echo "${RESPONSE}" | head -n -1)
HTTP_CODE=$(echo "${RESPONSE}" | tail -n 1)
log_endpoint "PATCH" "${POSTGRES_ENDPOINT}/${POSTGRES_ID}" "${HTTP_CODE}"
if [ "${HTTP_CODE}" -ne 200 ]; then
    echo "ERROR: PATCH failed with status ${HTTP_CODE}"
    exit 1
fi

# DELETE
echo "  Deleting ${POSTGRES_ENTITY}..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE "${POSTGRES_ENDPOINT}/${POSTGRES_ID}")
HTTP_CODE=$(echo "${RESPONSE}" | tail -n 1)
log_endpoint "DELETE" "${POSTGRES_ENDPOINT}/${POSTGRES_ID}" "${HTTP_CODE}"
if [ "${HTTP_CODE}" -ne 204 ]; then
    echo "ERROR: DELETE failed with status ${HTTP_CODE}"
    exit 1
fi

# Test Mongo entity
echo ""
echo "Testing Mongo entity: ${MONGO_ENTITY}"
MONGO_ENDPOINT="${API_BASE}/${MONGO_SLUG}"

# POST
echo "  Creating ${MONGO_ENTITY}..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${MONGO_ENDPOINT}" \
    -H "Content-Type: application/json" \
    -d "${MONGO_PAYLOAD}")
HTTP_BODY=$(echo "${RESPONSE}" | head -n -1)
HTTP_CODE=$(echo "${RESPONSE}" | tail -n 1)
log_endpoint "POST" "${MONGO_ENDPOINT}" "${HTTP_CODE}"
if [ "${HTTP_CODE}" -ne 201 ]; then
    echo "ERROR: POST failed with status ${HTTP_CODE}"
    echo "Response: ${HTTP_BODY}"
    exit 1
fi
MONGO_ID=$(echo "${HTTP_BODY}" | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))")

# GET list
echo "  Listing ${MONGO_ENTITY}..."
RESPONSE=$(curl -s -w "\n%{http_code}" "${MONGO_ENDPOINT}")
HTTP_BODY=$(echo "${RESPONSE}" | head -n -1)
HTTP_CODE=$(echo "${RESPONSE}" | tail -n 1)
log_endpoint "GET" "${MONGO_ENDPOINT}" "${HTTP_CODE}"
if [ "${HTTP_CODE}" -ne 200 ]; then
    echo "ERROR: GET list failed with status ${HTTP_CODE}"
    exit 1
fi

# GET by ID
echo "  Getting ${MONGO_ENTITY} by ID..."
RESPONSE=$(curl -s -w "\n%{http_code}" "${MONGO_ENDPOINT}/${MONGO_ID}")
HTTP_BODY=$(echo "${RESPONSE}" | head -n -1)
HTTP_CODE=$(echo "${RESPONSE}" | tail -n 1)
log_endpoint "GET" "${MONGO_ENDPOINT}/${MONGO_ID}" "${HTTP_CODE}"
if [ "${HTTP_CODE}" -ne 200 ]; then
    echo "ERROR: GET by ID failed with status ${HTTP_CODE}"
    exit 1
fi

# PATCH
echo "  Updating ${MONGO_ENTITY}..."
PATCH_PAYLOAD="{}"
RESPONSE=$(curl -s -w "\n%{http_code}" -X PATCH "${MONGO_ENDPOINT}/${MONGO_ID}" \
    -H "Content-Type: application/json" \
    -d "${PATCH_PAYLOAD}")
HTTP_BODY=$(echo "${RESPONSE}" | head -n -1)
HTTP_CODE=$(echo "${RESPONSE}" | tail -n 1)
log_endpoint "PATCH" "${MONGO_ENDPOINT}/${MONGO_ID}" "${HTTP_CODE}"
if [ "${HTTP_CODE}" -ne 200 ]; then
    echo "ERROR: PATCH failed with status ${HTTP_CODE}"
    exit 1
fi

# DELETE
echo "  Deleting ${MONGO_ENTITY}..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE "${MONGO_ENDPOINT}/${MONGO_ID}")
HTTP_CODE=$(echo "${RESPONSE}" | tail -n 1)
log_endpoint "DELETE" "${MONGO_ENDPOINT}/${MONGO_ID}" "${HTTP_CODE}"
if [ "${HTTP_CODE}" -ne 204 ]; then
    echo "ERROR: DELETE failed with status ${HTTP_CODE}"
    exit 1
fi

echo ""
echo "All CRUD tests passed!"
echo ""

# Step 9: Write verification.md
echo "=== Step 9: Writing verification.md ==="
cat > "${VERIFICATION_LOG}" <<EOF
# Verification Report

**Timestamp:** ${TIMESTAMP}

**Selected Entities:**
- Postgres: ${POSTGRES_ENTITY} (slug: ${POSTGRES_SLUG})
- Mongo: ${MONGO_ENTITY} (slug: ${MONGO_SLUG})

**Endpoints Called:**
EOF

for i in "${!ENDPOINTS_CALLED[@]}"; do
    echo "- ${ENDPOINTS_CALLED[$i]} -> ${STATUS_CODES[$i]}" >> "${VERIFICATION_LOG}"
done

cat >> "${VERIFICATION_LOG}" <<EOF

**Status:** All tests passed successfully
EOF

echo "Verification report written to: ${VERIFICATION_LOG}"
echo ""

echo "=== Smoke Test Complete ==="
echo "All tests passed!"

