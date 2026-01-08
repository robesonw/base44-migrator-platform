# PowerShell script for generated backend smoke test
$ErrorActionPreference = "Stop"

# Configuration
$JOB_ID = if ($env:JOB_ID) { $env:JOB_ID } else { "generated_backend_smoke" }
$SOURCE_REPO_URL = if ($env:SOURCE_REPO_URL) { $env:SOURCE_REPO_URL } else { "https://github.com/robesonw/culinary-compass.git" }
$OUT_DIR = if ($env:OUT_DIR) { $env:OUT_DIR } else { "test_output/$JOB_ID/workspace" }

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_ROOT = Split-Path -Parent $SCRIPT_DIR
$OUT_DIR_ABS = Join-Path $PROJECT_ROOT $OUT_DIR
$ARTIFACTS_DIR = Join-Path $OUT_DIR_ABS "artifacts"
$SOURCE_DIR = Join-Path $OUT_DIR_ABS "source"
$BACKEND_DIR = Join-Path $OUT_DIR_ABS "generated\backend"
$VERIFICATION_LOG = Join-Path $ARTIFACTS_DIR "verification.md"

$ENDPOINTS_CALLED = @()
$STATUS_CODES = @()

# Cleanup function
function Cleanup {
    param([int]$ExitCode)
    
    Write-Host ""
    Write-Host "=== Cleanup ==="
    
    if (Test-Path $BACKEND_DIR) {
        Write-Host "Stopping docker compose..."
        Push-Location $BACKEND_DIR
        docker compose down -v 2>$null
        Pop-Location
    }
    
    if ($ExitCode -ne 0) {
        Write-Host "Script failed with exit code $ExitCode"
    }
    exit $ExitCode
}

try {
    Write-Host "=== Generated Backend Smoke Test ==="
    Write-Host "JOB_ID: $JOB_ID"
    Write-Host "SOURCE_REPO_URL: $SOURCE_REPO_URL"
    Write-Host "OUT_DIR: $OUT_DIR"
    Write-Host ""
    
    # Step 1: Create clean output directory
    Write-Host "=== Step 1: Creating clean output directory ==="
    if (Test-Path $OUT_DIR_ABS) {
        Remove-Item -Recurse -Force $OUT_DIR_ABS
    }
    New-Item -ItemType Directory -Path $ARTIFACTS_DIR -Force | Out-Null
    New-Item -ItemType Directory -Path $SOURCE_DIR -Force | Out-Null
    Write-Host "Created: $OUT_DIR_ABS"
    Write-Host ""
    
    # Step 2: Run generator pipeline
    Write-Host "=== Step 2: Running generator pipeline ==="
    Push-Location $PROJECT_ROOT
    $env:PYTHONPATH = $PROJECT_ROOT
    
    # Convert Windows paths to forward slashes for Python
    $sourceDirPy = $SOURCE_DIR.Replace('\', '/')
    $artifactsDirPy = $ARTIFACTS_DIR.Replace('\', '/')
    $outDirPy = $OUT_DIR_ABS.Replace('\', '/')
    
    $pipelineScript = @"
import json
from pathlib import Path
from unittest.mock import MagicMock
from git import Repo
from app.agents.impl_intake import RepoIntakeAgent
from app.agents.impl_design import DomainModelerAgent, ApiDesignerAgent
from app.agents.impl_build import BackendBuilderAgent

source_repo = '$SOURCE_REPO_URL'
source_dir = Path('$sourceDirPy')
artifacts_dir = Path('$artifactsDirPy')
workspace_root = Path('$outDirPy')

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
domain_job.id = '$JOB_ID'
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
backend_job.id = '$JOB_ID'
backend_result = BackendBuilderAgent().run(backend_job, mock_ws)
if not backend_result.ok:
    print(f'    ERROR: {backend_result.message}')
    exit(1)
print(f'    {backend_result.message}')
"@
    
    python -c $pipelineScript
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Generator pipeline failed"
        Cleanup 1
    }
    Pop-Location
    Write-Host ""
    
    # Step 3: Verify generated backend exists
    Write-Host "=== Step 3: Verifying generated backend ==="
    if (-not (Test-Path $BACKEND_DIR)) {
        Write-Host "ERROR: Generated backend directory not found: $BACKEND_DIR"
        Cleanup 1
    }
    Write-Host "Backend directory exists: $BACKEND_DIR"
    Write-Host ""
    
    # Step 4: Change to backend directory
    Write-Host "=== Step 4: Changing to backend directory ==="
    Push-Location $BACKEND_DIR
    Write-Host "Current directory: $(Get-Location)"
    Write-Host ""
    
    # Step 5: Start docker compose
    Write-Host "=== Step 5: Starting docker compose ==="
    docker compose up -d --build
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: docker compose up failed"
        Cleanup 1
    }
    Write-Host "Docker compose started"
    Write-Host ""
    
    # Step 6: Wait for health endpoint
    Write-Host "=== Step 6: Waiting for health endpoint ==="
    $MAX_ATTEMPTS = 60
    $ATTEMPT = 0
    $HEALTH_URL = "http://localhost:8081/api/health"
    $healthCheckPassed = $false
    
    while ($ATTEMPT -lt $MAX_ATTEMPTS -and -not $healthCheckPassed) {
        try {
            $response = Invoke-WebRequest -Uri $HEALTH_URL -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                $healthCheckPassed = $true
                Write-Host "Health check passed"
            }
        } catch {
            $ATTEMPT++
            if ($ATTEMPT -ge $MAX_ATTEMPTS) {
                Write-Host "ERROR: Health check failed after $MAX_ATTEMPTS attempts"
                docker compose logs api
                Cleanup 1
            }
            Write-Host "Waiting for API... (attempt $ATTEMPT/$MAX_ATTEMPTS)"
            Start-Sleep -Seconds 2
        }
    }
    Write-Host ""
    
    # Step 7: Select entities from storage-plan.json
    Write-Host "=== Step 7: Selecting entities from storage-plan.json ==="
    $STORAGE_PLAN_PATH = Join-Path $ARTIFACTS_DIR "storage-plan.json"
    if (-not (Test-Path $STORAGE_PLAN_PATH)) {
        Write-Host "ERROR: storage-plan.json not found: $STORAGE_PLAN_PATH"
        Cleanup 1
    }
    
    $entityInfoScript = @"
import json
import sys
from pathlib import Path
from app.generators.backend_gen.utils import entity_to_path

storage_plan_path = Path(r'$STORAGE_PLAN_PATH'.Replace('\', '/'))
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
"@
    
    $ENTITY_INFO = python -c $entityInfoScript
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to select entities"
        Cleanup 1
    }
    
    $POSTGRES_ENTITY = ($ENTITY_INFO -split '\|')[0]
    $POSTGRES_SLUG = ($ENTITY_INFO -split '\|')[1]
    $MONGO_ENTITY = ($ENTITY_INFO -split '\|')[2]
    $MONGO_SLUG = ($ENTITY_INFO -split '\|')[3]
    
    Write-Host "Selected Postgres entity: $POSTGRES_ENTITY (slug: $POSTGRES_SLUG)"
    Write-Host "Selected Mongo entity: $MONGO_ENTITY (slug: $MONGO_SLUG)"
    Write-Host ""
    
    # Step 8: CRUD tests
    Write-Host "=== Step 8: Running CRUD tests ==="
    $API_BASE = "http://localhost:8081/api"
    $TIMESTAMP = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    
    # Build payloads using Python helper
    Write-Host "Building payloads..."
    $postgresPayloadScript = @"
import sys
from pathlib import Path
from app.generators.backend_gen.smoke_payload import build_minimal_payload
import json

ui_contract_path = Path(r'$ARTIFACTS_DIR'.Replace('\', '/')) / 'ui-contract.json'
entity_name = '$POSTGRES_ENTITY'
payload = build_minimal_payload(ui_contract_path, entity_name)
print(json.dumps(payload))
"@
    
    $MONGO_PAYLOAD_SCRIPT = @"
import sys
from pathlib import Path
from app.generators.backend_gen.smoke_payload import build_minimal_payload
import json

ui_contract_path = Path(r'$ARTIFACTS_DIR'.Replace('\', '/')) / 'ui-contract.json'
entity_name = '$MONGO_ENTITY'
payload = build_minimal_payload(ui_contract_path, entity_name)
print(json.dumps(payload))
"@
    
    $POSTGRES_PAYLOAD = python -c $postgresPayloadScript
    $MONGO_PAYLOAD = python -c $MONGO_PAYLOAD_SCRIPT
    
    # Function to log endpoint call
    function Log-Endpoint {
        param([string]$Method, [string]$Endpoint, [int]$Status)
        $script:ENDPOINTS_CALLED += "$Method $Endpoint"
        $script:STATUS_CODES += $Status
        Write-Host "  $Method $Endpoint -> $Status"
    }
    
    # Test Postgres entity
    Write-Host ""
    Write-Host "Testing Postgres entity: $POSTGRES_ENTITY"
    $POSTGRES_ENDPOINT = "$API_BASE/$POSTGRES_SLUG"
    
    # POST
    Write-Host "  Creating $POSTGRES_ENTITY..."
    try {
        $response = Invoke-RestMethod -Uri $POSTGRES_ENDPOINT -Method Post -Body $POSTGRES_PAYLOAD -ContentType "application/json" -ErrorAction Stop
        $POSTGRES_ID = $response.id
        Log-Endpoint "POST" $POSTGRES_ENDPOINT 201
    } catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        Log-Endpoint "POST" $POSTGRES_ENDPOINT $statusCode
        Write-Host "ERROR: POST failed with status $statusCode"
        Cleanup 1
    }
    
    # GET list
    Write-Host "  Listing $POSTGRES_ENTITY..."
    try {
        $response = Invoke-RestMethod -Uri $POSTGRES_ENDPOINT -Method Get -ErrorAction Stop
        Log-Endpoint "GET" $POSTGRES_ENDPOINT 200
    } catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        Log-Endpoint "GET" $POSTGRES_ENDPOINT $statusCode
        Write-Host "ERROR: GET list failed with status $statusCode"
        Cleanup 1
    }
    
    # GET by ID
    Write-Host "  Getting $POSTGRES_ENTITY by ID..."
    try {
        $response = Invoke-RestMethod -Uri "$POSTGRES_ENDPOINT/$POSTGRES_ID" -Method Get -ErrorAction Stop
        Log-Endpoint "GET" "$POSTGRES_ENDPOINT/$POSTGRES_ID" 200
    } catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        Log-Endpoint "GET" "$POSTGRES_ENDPOINT/$POSTGRES_ID" $statusCode
        Write-Host "ERROR: GET by ID failed with status $statusCode"
        Cleanup 1
    }
    
    # PATCH
    Write-Host "  Updating $POSTGRES_ENTITY..."
    $PATCH_PAYLOAD = "{}"
    try {
        $response = Invoke-RestMethod -Uri "$POSTGRES_ENDPOINT/$POSTGRES_ID" -Method Patch -Body $PATCH_PAYLOAD -ContentType "application/json" -ErrorAction Stop
        Log-Endpoint "PATCH" "$POSTGRES_ENDPOINT/$POSTGRES_ID" 200
    } catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        Log-Endpoint "PATCH" "$POSTGRES_ENDPOINT/$POSTGRES_ID" $statusCode
        Write-Host "ERROR: PATCH failed with status $statusCode"
        Cleanup 1
    }
    
    # DELETE
    Write-Host "  Deleting $POSTGRES_ENTITY..."
    try {
        $response = Invoke-WebRequest -Uri "$POSTGRES_ENDPOINT/$POSTGRES_ID" -Method Delete -UseBasicParsing -ErrorAction Stop
        $statusCode = $response.StatusCode
        Log-Endpoint "DELETE" "$POSTGRES_ENDPOINT/$POSTGRES_ID" $statusCode
        if ($statusCode -ne 204) {
            Write-Host "ERROR: DELETE failed with status $statusCode"
            Cleanup 1
        }
    } catch {
        if ($_.Exception.Response) {
            $statusCode = $_.Exception.Response.StatusCode.value__
            Log-Endpoint "DELETE" "$POSTGRES_ENDPOINT/$POSTGRES_ID" $statusCode
            Write-Host "ERROR: DELETE failed with status $statusCode"
        } else {
            Write-Host "ERROR: DELETE failed: $($_.Exception.Message)"
        }
        Cleanup 1
    }
    
    # Test Mongo entity
    Write-Host ""
    Write-Host "Testing Mongo entity: $MONGO_ENTITY"
    $MONGO_ENDPOINT = "$API_BASE/$MONGO_SLUG"
    
    # POST
    Write-Host "  Creating $MONGO_ENTITY..."
    try {
        $response = Invoke-RestMethod -Uri $MONGO_ENDPOINT -Method Post -Body $MONGO_PAYLOAD -ContentType "application/json" -ErrorAction Stop
        $MONGO_ID = $response.id
        Log-Endpoint "POST" $MONGO_ENDPOINT 201
    } catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        Log-Endpoint "POST" $MONGO_ENDPOINT $statusCode
        Write-Host "ERROR: POST failed with status $statusCode"
        Cleanup 1
    }
    
    # GET list
    Write-Host "  Listing $MONGO_ENTITY..."
    try {
        $response = Invoke-RestMethod -Uri $MONGO_ENDPOINT -Method Get -ErrorAction Stop
        Log-Endpoint "GET" $MONGO_ENDPOINT 200
    } catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        Log-Endpoint "GET" $MONGO_ENDPOINT $statusCode
        Write-Host "ERROR: GET list failed with status $statusCode"
        Cleanup 1
    }
    
    # GET by ID
    Write-Host "  Getting $MONGO_ENTITY by ID..."
    try {
        $response = Invoke-RestMethod -Uri "$MONGO_ENDPOINT/$MONGO_ID" -Method Get -ErrorAction Stop
        Log-Endpoint "GET" "$MONGO_ENDPOINT/$MONGO_ID" 200
    } catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        Log-Endpoint "GET" "$MONGO_ENDPOINT/$MONGO_ID" $statusCode
        Write-Host "ERROR: GET by ID failed with status $statusCode"
        Cleanup 1
    }
    
    # PATCH
    Write-Host "  Updating $MONGO_ENTITY..."
    $PATCH_PAYLOAD = "{}"
    try {
        $response = Invoke-RestMethod -Uri "$MONGO_ENDPOINT/$MONGO_ID" -Method Patch -Body $PATCH_PAYLOAD -ContentType "application/json" -ErrorAction Stop
        Log-Endpoint "PATCH" "$MONGO_ENDPOINT/$MONGO_ID" 200
    } catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        Log-Endpoint "PATCH" "$MONGO_ENDPOINT/$MONGO_ID" $statusCode
        Write-Host "ERROR: PATCH failed with status $statusCode"
        Cleanup 1
    }
    
    # DELETE
    Write-Host "  Deleting $MONGO_ENTITY..."
    try {
        $response = Invoke-WebRequest -Uri "$MONGO_ENDPOINT/$MONGO_ID" -Method Delete -UseBasicParsing -ErrorAction Stop
        $statusCode = $response.StatusCode
        Log-Endpoint "DELETE" "$MONGO_ENDPOINT/$MONGO_ID" $statusCode
        if ($statusCode -ne 204) {
            Write-Host "ERROR: DELETE failed with status $statusCode"
            Cleanup 1
        }
    } catch {
        if ($_.Exception.Response) {
            $statusCode = $_.Exception.Response.StatusCode.value__
            Log-Endpoint "DELETE" "$MONGO_ENDPOINT/$MONGO_ID" $statusCode
            Write-Host "ERROR: DELETE failed with status $statusCode"
        } else {
            Write-Host "ERROR: DELETE failed: $($_.Exception.Message)"
        }
        Cleanup 1
    }
    
    Write-Host ""
    Write-Host "All CRUD tests passed!"
    Write-Host ""
    
    # Step 9: Write verification.md
    Write-Host "=== Step 9: Writing verification.md ==="
    $content = @"
# Verification Report

**Timestamp:** $TIMESTAMP

**Selected Entities:**
- Postgres: $POSTGRES_ENTITY (slug: $POSTGRES_SLUG)
- Mongo: $MONGO_ENTITY (slug: $MONGO_SLUG)

**Endpoints Called:**
"@
    
    for ($i = 0; $i -lt $ENDPOINTS_CALLED.Length; $i++) {
        $content += "`n- $($ENDPOINTS_CALLED[$i]) -> $($STATUS_CODES[$i])"
    }
    
    $content += @"

**Status:** All tests passed successfully
"@
    
    $content | Out-File -FilePath $VERIFICATION_LOG -Encoding utf8
    Write-Host "Verification report written to: $VERIFICATION_LOG"
    Write-Host "Absolute path: $((Resolve-Path $VERIFICATION_LOG -ErrorAction SilentlyContinue).Path)"
    Write-Host ""
    
    Write-Host "=== Smoke Test Complete ==="
    Write-Host "All tests passed!"
    
    Pop-Location
    Cleanup 0
    
} catch {
    Write-Host "ERROR: $($_.Exception.Message)"
    Write-Host $_.ScriptStackTrace
    Cleanup 1
}

