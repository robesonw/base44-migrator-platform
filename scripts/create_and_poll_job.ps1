# PowerShell script to create a job and poll its status
# Usage: .\scripts\create_and_poll_job.ps1

$API_URL = if ($env:API_URL) { $env:API_URL } else { "http://localhost:8080" }
$MAX_WAIT_SECONDS = 300
$POLL_INTERVAL = 2

Write-Host "=== Creating a new job ==="
try {
    $body = @{
        source_repo_url = "https://github.com/robesonw/culinary-compass.git"
        target_repo_url = "https://github.com/robesonw/cc"
        backend_stack   = "python"
        db_stack        = "postgres"
        commit_mode     = "pr"
    } | ConvertTo-Json
    
    $jobResponse = Invoke-RestMethod -Uri "$API_URL/v1/jobs" -Method Post -Body $body -ContentType "application/json"
    $jobId = $jobResponse.id
    
    if (-not $jobId) {
        Write-Host "ERROR: Failed to create job. Response: $($jobResponse | ConvertTo-Json)"
        exit 1
    }
    
    Write-Host "Job created with ID: $jobId"
    Write-Host ""
} catch {
    Write-Host "ERROR: Failed to create job: $($_.Exception.Message)"
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host "Response: $responseBody"
    }
    exit 1
}

Write-Host "=== Polling job status ==="
$elapsed = 0
$status = ""
while ($elapsed -lt $MAX_WAIT_SECONDS -and $status -ne "DONE" -and $status -ne "FAILED") {
    try {
        $job = Invoke-RestMethod -Uri "$API_URL/v1/jobs/$jobId"
        $status = $job.status
        $stage = $job.stage
        
        Write-Host "Job status: $status, stage: $stage (elapsed: ${elapsed}s)"
        
        if ($status -eq "DONE" -or $status -eq "FAILED") {
            Write-Host "Job reached final state: $status"
            break
        }
    } catch {
        Write-Host "ERROR: Failed to poll job status: $($_.Exception.Message)"
        exit 1
    }
    
    Start-Sleep -Seconds $POLL_INTERVAL
    $elapsed += $POLL_INTERVAL
}

if ($elapsed -ge $MAX_WAIT_SECONDS) {
    Write-Host "ERROR: Job did not complete within ${MAX_WAIT_SECONDS} seconds"
    exit 1
}

Write-Host ""
Write-Host "=== Final Job Status ==="
try {
    $job = Invoke-RestMethod -Uri "$API_URL/v1/jobs/$jobId"
    $job | ConvertTo-Json -Depth 10
} catch {
    Write-Host "ERROR: Failed to get final job status: $($_.Exception.Message)"
    exit 1
}

Write-Host ""
Write-Host "=== Fetching Artifacts ==="
try {
    $artifacts = Invoke-RestMethod -Uri "$API_URL/v1/jobs/$jobId/artifacts"
    $artifacts | ConvertTo-Json -Depth 10
    
    if ($artifacts.artifacts.Count -gt 0) {
        Write-Host ""
        Write-Host "Artifact files:"
        foreach ($artifact in $artifacts.artifacts) {
            Write-Host "  - $($artifact.path) ($($artifact.size) bytes, modified: $($artifact.last_modified))"
        }
    }
} catch {
    Write-Host "ERROR: Failed to get artifacts: $($_.Exception.Message)"
    exit 1
}

Write-Host ""
Write-Host "=== Summary ==="
if ($status -eq "FAILED") {
    Write-Host "WARNING: Job failed. Check logs for details."
    Write-Host "View logs with: docker compose logs worker --tail=50"
    exit 1
} else {
    Write-Host "SUCCESS: Job completed successfully"
    Write-Host "Job ID: $jobId"
    Write-Host "Artifacts available at: workspaces/$jobId/workspace/"
    exit 0
}

