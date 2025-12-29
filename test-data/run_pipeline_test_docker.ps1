# Script to run the complete pipeline test with Docker Compose (Windows)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Pipeline End-to-End Test (Docker)" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is running
Write-Host "Checking Docker..." -ForegroundColor Yellow
try {
    $null = docker info 2>&1
    Write-Host "[OK] Docker is running" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Docker is not running. Please start Docker Desktop and try again." -ForegroundColor Red
    exit 1
}

# Check if docker-compose is available
Write-Host "Checking docker-compose..." -ForegroundColor Yellow
try {
    $null = docker-compose version 2>&1
    Write-Host "[OK] docker-compose is available" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] docker-compose is not available. Please install docker-compose." -ForegroundColor Red
    exit 1
}

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
    Write-Host "[INFO] Starting Docker services..." -ForegroundColor Yellow
    Write-Host ""
    
    # Build and start services
    docker-compose up -d --build
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to start Docker services" -ForegroundColor Red
        exit 1
    }
    
    Write-Host ""
    Write-Host "Waiting for services to be ready..." -ForegroundColor Yellow
    
    # Wait for services with timeout
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
            Write-Host "  Waiting for services... ($waited/$maxWait seconds)" -ForegroundColor Gray
        }
    }
    
    if (-not $allReady) {
        Write-Host "[ERROR] Services did not become ready within $maxWait seconds" -ForegroundColor Red
        Write-Host "Checking service logs..." -ForegroundColor Yellow
        docker-compose logs --tail=50
        exit 1
    }
    
    Write-Host "[OK] All services are ready" -ForegroundColor Green
    Write-Host ""
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
$response = Read-Host "Do you want to stop the Docker services? (y/N)"
if ($response -eq "y" -or $response -eq "Y") {
    Write-Host "Stopping Docker services..." -ForegroundColor Yellow
    docker-compose down
    Write-Host "[OK] Services stopped" -ForegroundColor Green
}

exit $TestExitCode

