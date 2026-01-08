# Script to verify ui-contract.json structure
param(
    [Parameter(Mandatory=$false)]
    [string]$JobId
)

if (-not $JobId) {
    # Get latest job
    $jobs = Get-ChildItem workspaces -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    $JobId = $jobs.Name
}

$contractPath = "workspaces\$JobId\workspace\ui-contract.json"

if (-not (Test-Path $contractPath)) {
    Write-Host "ERROR: Contract file not found at $contractPath" -ForegroundColor Red
    exit 1
}

Write-Host "=== ui-contract.json Verification ===" -ForegroundColor Cyan
Write-Host "Job ID: $JobId" -ForegroundColor Yellow
Write-Host "File: $contractPath" -ForegroundColor Yellow
Write-Host ""

$contract = Get-Content $contractPath | ConvertFrom-Json
$contractText = Get-Content $contractPath -Raw

$allPassed = $true

# Check source_repo_url
Write-Host "1. source_repo_url: $($contract.source_repo_url)" -ForegroundColor Green

# Check framework structure
if ($contract.framework -is [PSCustomObject] -or $contract.framework.GetType().Name -eq 'Hashtable') {
    Write-Host "2. Framework is object: OK" -ForegroundColor Green
    Write-Host "   - name: $($contract.framework.name)" -ForegroundColor Yellow
    Write-Host "   - versionHint: '$($contract.framework.versionHint)'" -ForegroundColor Yellow
} else {
    Write-Host "2. Framework is object: FAILED (found: $($contract.framework.GetType().Name))" -ForegroundColor Red
    $allPassed = $false
}

# Check required fields exist
Write-Host "3. Entities count: $($contract.entities.Count)" -ForegroundColor Green
Write-Host "4. Endpoints count: $($contract.endpointsUsed.Count)" -ForegroundColor Green
Write-Host "5. Env vars count: $($contract.envVars.Count)" -ForegroundColor Green
Write-Host "6. API Client Files count: $($contract.apiClientFiles.Count)" -ForegroundColor Green

if ($contract.entityDetection) {
    Write-Host "7. EntityDetection exists: OK" -ForegroundColor Green
} else {
    Write-Host "7. EntityDetection exists: FAILED" -ForegroundColor Red
    $allPassed = $false
}

Write-Host "8. Notes count: $($contract.notes.Count)" -ForegroundColor Green

# Check for TODO
$hasTODO = $contractText -match 'TODO:'
if (-not $hasTODO) {
    Write-Host "9. Contains 'TODO:': No (OK)" -ForegroundColor Green
} else {
    Write-Host "9. Contains 'TODO:': YES (ERROR!)" -ForegroundColor Red
    $allPassed = $false
}

# Check for octocat
$hasOctocat = $contractText -match 'octocat/Hello-World'
if (-not $hasOctocat) {
    Write-Host "10. Contains 'octocat/Hello-World': No (OK)" -ForegroundColor Green
} else {
    Write-Host "10. Contains 'octocat/Hello-World': YES (ERROR!)" -ForegroundColor Red
    $allPassed = $false
}

Write-Host ""
if ($contract.notes.Count -gt 0) {
    Write-Host "Notes:" -ForegroundColor Cyan
    $contract.notes | ForEach-Object { Write-Host "  - $_" -ForegroundColor Yellow }
}

Write-Host ""
if ($allPassed) {
    Write-Host "All verification checks PASSED!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "Some verification checks FAILED!" -ForegroundColor Red
    exit 1
}

