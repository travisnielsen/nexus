# Run all backend services concurrently

$BackendDir = Join-Path $PSScriptRoot "..\backend"

Write-Host "Starting all backend services..." -ForegroundColor Cyan

# Start MCP server (port 8001)
Write-Host "Starting MCP server on port 8001..." -ForegroundColor Yellow
$mcpJob = Start-Job -ScriptBlock {
    param($dir)
    Set-Location $dir
    uv run uvicorn main:rest_app --host 0.0.0.0 --port 8001 --reload
} -ArgumentList (Join-Path $BackendDir "mcp")

# Start A2A agent (port 5002)
Write-Host "Starting A2A agent on port 5002..." -ForegroundColor Yellow
$a2aJob = Start-Job -ScriptBlock {
    param($dir)
    Set-Location $dir
    uv run uvicorn main:app --host 0.0.0.0 --port 5002 --reload
} -ArgumentList (Join-Path $BackendDir "agent-a2a")

# Wait for dependencies to start
Start-Sleep -Seconds 2

# Start API server (port 8000)
Write-Host "Starting API server on port 8000..." -ForegroundColor Yellow
$apiJob = Start-Job -ScriptBlock {
    param($dir)
    Set-Location $dir
    uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
} -ArgumentList (Join-Path $BackendDir "api")

Write-Host ""
Write-Host "All services started:" -ForegroundColor Green
Write-Host "  - MCP Server:  http://localhost:8001"
Write-Host "  - A2A Agent:   http://localhost:5002"
Write-Host "  - API Server:  http://localhost:8000"
Write-Host ""
Write-Host "Press Ctrl+C to stop all services"

try {
    # Stream output from all jobs
    while ($true) {
        Receive-Job -Job $mcpJob, $a2aJob, $apiJob -ErrorAction SilentlyContinue
        Start-Sleep -Milliseconds 500
    }
}
finally {
    Write-Host ""
    Write-Host "Stopping all services..." -ForegroundColor Yellow
    Stop-Job -Job $mcpJob, $a2aJob, $apiJob -ErrorAction SilentlyContinue
    Remove-Job -Job $mcpJob, $a2aJob, $apiJob -Force -ErrorAction SilentlyContinue
}
