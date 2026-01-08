# PowerShell script to create a PR from dev to main
# Usage: .\scripts\create_pr.ps1 -Token YOUR_GITHUB_TOKEN

param(
    [Parameter(Mandatory=$true)]
    [string]$Token
)

$owner = "robesonw"
$repo = "base44-migrator-platform"
$baseBranch = "main"
$headBranch = "dev"
$url = "https://api.github.com/repos/$owner/$repo/pulls"

$headers = @{
    "Authorization" = "Bearer $Token"
    "Accept" = "application/vnd.github+json"
    "X-GitHub-Api-Version" = "2022-11-28"
}

$body = @{
    title = "Merge dev into main"
    head = $headBranch
    base = $baseBranch
    body = @"
This PR merges the development branch into main.

## Changes
- Development branch setup
- Branch workflow established

## Workflow
- Development work happens on `dev` branch
- Changes are merged to `main` via Pull Requests
"@
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri $url -Method Post -Headers $headers -Body $body -ContentType "application/json"
    Write-Host "✅ Pull Request created successfully!" -ForegroundColor Green
    Write-Host "📝 Title: $($response.title)" -ForegroundColor Cyan
    Write-Host "🔗 URL: $($response.html_url)" -ForegroundColor Cyan
    Write-Host "📊 Status: $($response.state)" -ForegroundColor Cyan
    $response.html_url
} catch {
    if ($_.Exception.Response.StatusCode -eq 422) {
        Write-Host "⚠️  Pull request may already exist or there are no differences between branches." -ForegroundColor Yellow
        Write-Host "Check: https://github.com/$owner/$repo/pulls" -ForegroundColor Cyan
    } else {
        Write-Host "❌ Error creating PR: $($_.Exception.Message)" -ForegroundColor Red
        throw
    }
}

