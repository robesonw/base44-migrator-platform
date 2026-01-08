$ErrorActionPreference = "Stop"

$API_URL = if ($env:API_URL) { $env:API_URL } else { "http://localhost:8080" }
$MAX_WAIT_SECONDS = 20
$POLL_INTERVAL = 2

Write-Host "=== Starting Docker Compose ==="
docker compose up -d
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to start Docker Compose"
    exit 1
}

Write-Host "=== Waiting for services to be ready ==="
Start-Sleep -Seconds 5

Write-Host "=== Checking /v1/health endpoint ==="
$attempt = 0
$healthCheckPassed = $false
while ($attempt -lt 5 -and -not $healthCheckPassed) {
    $attempt++
    try {
        $response = Invoke-WebRequest -Uri "$API_URL/v1/health" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        $healthCheckPassed = $true
        Write-Host "Health check passed"
    } catch {
        if ($attempt -ge 5) {
            Write-Host "ERROR: Health check failed after 5 attempts"
            docker compose logs api
            exit 1
        }
        Write-Host "Waiting for API to be ready... (attempt $attempt/5)"
        Start-Sleep -Seconds 1
    }
}

Write-Host "=== Creating a new job ==="
try {
    $body = @{
        source_repo_url = "https://github.com/octocat/Hello-World"
        target_repo_url = "https://github.com/octocat/Hello-World"
        backend_stack = "python"
        db_stack = "postgres"
        commit_mode = "pr"
    } | ConvertTo-Json
    
    $jobResponse = Invoke-RestMethod -Uri "$API_URL/v1/jobs" -Method Post -Body $body -ContentType "application/json"
    $jobId = $jobResponse.id
    
    if (-not $jobId) {
        Write-Host "ERROR: Failed to create job. Response: $($jobResponse | ConvertTo-Json)"
        exit 1
    }
    
    Write-Host "Job created with ID: $jobId"
} catch {
    Write-Host "ERROR: Failed to create job: $($_.Exception.Message)"
    exit 1
}

Write-Host "=== Polling job status ==="
$elapsed = 0
$status = ""
while ($elapsed -lt $MAX_WAIT_SECONDS -and $status -ne "DONE" -and $status -ne "FAILED") {
    try {
        $statusResponse = Invoke-RestMethod -Uri "$API_URL/v1/jobs/$jobId"
        $status = $statusResponse.status
        $stage = $statusResponse.stage
        
        Write-Host "Job status: $status, stage: $stage (elapsed: ${elapsed}s)"
        
        if ($status -eq "DONE" -or $status -eq "FAILED") {
            Write-Host "Job reached final state: $status"
            break
        }
    } catch {
        Write-Host "ERROR: Failed to fetch job status: $($_.Exception.Message)"
        exit 1
    }
    
    Start-Sleep -Seconds $POLL_INTERVAL
    $elapsed += $POLL_INTERVAL
}

if ($elapsed -ge $MAX_WAIT_SECONDS) {
    Write-Host "ERROR: Job did not complete within $MAX_WAIT_SECONDS seconds"
    exit 1
}

Write-Host "=== Fetching artifact list ==="
try {
    $artifactsResponse = Invoke-RestMethod -Uri "$API_URL/v1/jobs/$jobId/artifacts"
    $artifactsResponse | ConvertTo-Json -Depth 10
} catch {
    Write-Host "ERROR: Failed to fetch artifacts: $($_.Exception.Message)"
    exit 1
}

Write-Host "=== Smoke test completed ==="
if ($status -eq "FAILED") {
    Write-Host "WARNING: Job failed. Check logs for details."
    docker compose logs worker --tail=50
    exit 1
} else {
    Write-Host "SUCCESS: Job completed successfully"
    exit 0
}

