# Quick start script for Docker Compose (Windows)
# This script starts all services and waits for them to be ready

$ProjectRoot = $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Starting SFD-CLM Services with Docker" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check Docker
Write-Host "Checking Docker..." -ForegroundColor Yellow
try {
    $null = docker info 2>&1
    Write-Host "[OK] Docker is running" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Docker is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}

# Build and start services
Write-Host ""
Write-Host "Building and starting services..." -ForegroundColor Yellow
docker-compose up -d --build

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to start services" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Waiting for services to be ready..." -ForegroundColor Yellow

# Wait for services
$maxWait = 60
$waited = 0
$allReady = $false

while ($waited -lt $maxWait -and -not $allReady) {
    Start-Sleep -Seconds 2
    $waited += 2
    
    $allReady = $true
    try {
        $null = Invoke-WebRequest -Uri "http://localhost:8001/health" -TimeoutSec 2 -UseBasicParsing
    } catch {
        $allReady = $false
    }
    
    try {
        $null = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 2 -UseBasicParsing
    } catch {
        $allReady = $false
    }
    
    try {
        $null = Invoke-WebRequest -Uri "http://localhost:8002/health" -TimeoutSec 2 -UseBasicParsing
    } catch {
        $allReady = $false
    }
    
    if (-not $allReady) {
        Write-Host "  Waiting... ($waited/$maxWait seconds)" -ForegroundColor Gray
    }
}

if ($allReady) {
    Write-Host ""
    Write-Host "[OK] All services are ready!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Services:" -ForegroundColor Cyan
    Write-Host "  - Mock Salesforce:  http://localhost:8001" -ForegroundColor White
    Write-Host "  - Backend MCP:      http://localhost:8000" -ForegroundColor White
    Write-Host "  - Backend LangGraph: http://localhost:8002" -ForegroundColor White
    Write-Host ""
    Write-Host "Useful commands:" -ForegroundColor Cyan
    Write-Host "  - View logs:        docker-compose logs -f" -ForegroundColor White
    Write-Host "  - Stop services:    docker-compose down" -ForegroundColor White
    Write-Host "  - Restart service:  docker-compose restart <service-name>" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "[ERROR] Services did not become ready within $maxWait seconds" -ForegroundColor Red
    Write-Host "Check logs with: docker-compose logs" -ForegroundColor Yellow
    exit 1
}

