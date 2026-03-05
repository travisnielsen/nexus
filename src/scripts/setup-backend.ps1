# Setup script for all backend Python projects

$BackendDir = Join-Path $PSScriptRoot "..\backend"

Write-Host "Setting up backend Python projects..." -ForegroundColor Cyan

$projects = @("api", "mcp", "agent-a2a")

foreach ($project in $projects) {
    Write-Host ""
    Write-Host "=== Setting up $project ===" -ForegroundColor Yellow
    
    $projectPath = Join-Path $BackendDir $project
    
    if (-not (Test-Path $projectPath)) {
        Write-Host "Failed to find $project at $projectPath" -ForegroundColor Red
        exit 1
    }
    
    Push-Location $projectPath
    try {
        uv sync
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Failed to sync $project" -ForegroundColor Red
            exit 1
        }
    }
    finally {
        Pop-Location
    }
}

Write-Host ""
Write-Host "✅ All backend projects set up successfully" -ForegroundColor Green
