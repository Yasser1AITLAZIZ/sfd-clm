# Script to run the complete pipeline test (Windows)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Pipeline End-to-End Test" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if services are already running
Write-Host "Checking if services are running..." -ForegroundColor Yellow
$ServicesRunning = $true

try {
    $null = Invoke-WebRequest -Uri "http://localhost:8001/health" -TimeoutSec 2 -UseBasicParsing
} catch {
    $ServicesRunning = $false
}

try {
    $null = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 2 -UseBasicParsing
} catch {
    $ServicesRunning = $false
}

try {
    $null = Invoke-WebRequest -Uri "http://localhost:8002/health" -TimeoutSec 2 -UseBasicParsing
} catch {
    $ServicesRunning = $false
}

if (-not $ServicesRunning) {
    Write-Host "[WARNING] Some services are not running. Starting them..." -ForegroundColor Yellow
    Write-Host ""
    & "$ScriptDir\start_services.ps1"
    Write-Host ""
    Write-Host "Waiting for services to be ready..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
} else {
    Write-Host "[OK] All services are already running" -ForegroundColor Green
    Write-Host ""
}

# Run the test
Write-Host "Running pipeline test..." -ForegroundColor Yellow
Write-Host ""
python "$ScriptDir\test_pipeline.py"
$TestExitCode = $LASTEXITCODE

Write-Host ""

# Ask if user wants to stop services
if (-not $ServicesRunning) {
    $response = Read-Host "Do you want to stop the services? (y/N)"
    if ($response -eq "y" -or $response -eq "Y") {
        & "$ScriptDir\stop_services.ps1"
    }
}

exit $TestExitCode

