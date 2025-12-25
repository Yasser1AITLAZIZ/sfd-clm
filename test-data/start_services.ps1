# Script to start all services for testing (Windows)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Starting OptiClaims Services for Testing" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Redis is running
Write-Host "Checking Redis..." -ForegroundColor Yellow
try {
    $null = redis-cli ping 2>$null
    Write-Host "[OK] Redis is running" -ForegroundColor Green
} catch {
    Write-Host "[WARNING] Redis is not running. Please start it manually." -ForegroundColor Yellow
    Write-Host "           Run: redis-server" -ForegroundColor Yellow
    Read-Host "Press Enter to continue anyway"
}

Write-Host ""

# Create logs directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogsDir = Join-Path $ScriptDir "results\logs"
New-Item -ItemType Directory -Force -Path $LogsDir | Out-Null

# Start Mock Salesforce service
Write-Host "Starting Mock Salesforce service on port 8001..." -ForegroundColor Yellow
$MockSfLog = Join-Path $LogsDir "mock-salesforce.log"
Start-Process -FilePath "uvicorn" -ArgumentList "app.main:app", "--port", "8001", "--reload" -WorkingDirectory (Join-Path $ScriptDir "..\mock-salesforce") -WindowStyle Hidden -RedirectStandardOutput $MockSfLog -RedirectStandardError $MockSfLog
Start-Sleep -Seconds 3

# Check if Mock Salesforce started
try {
    $null = Invoke-WebRequest -Uri "http://localhost:8001/health" -TimeoutSec 2 -UseBasicParsing
    Write-Host "[OK] Mock Salesforce service started" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Failed to start Mock Salesforce service" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Start Backend MCP service
Write-Host "Starting Backend MCP service on port 8000..." -ForegroundColor Yellow
$McpLog = Join-Path $LogsDir "backend-mcp.log"
Start-Process -FilePath "uvicorn" -ArgumentList "app.main:app", "--port", "8000", "--reload" -WorkingDirectory (Join-Path $ScriptDir "..\backend-mcp") -WindowStyle Hidden -RedirectStandardOutput $McpLog -RedirectStandardError $McpLog
Start-Sleep -Seconds 3

# Check if Backend MCP started
try {
    $null = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 2 -UseBasicParsing
    Write-Host "[OK] Backend MCP service started" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Failed to start Backend MCP service" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Start Backend LangGraph service
Write-Host "Starting Backend LangGraph service on port 8002..." -ForegroundColor Yellow
$LangGraphLog = Join-Path $LogsDir "backend-langgraph.log"
Start-Process -FilePath "uvicorn" -ArgumentList "app.main:app", "--port", "8002", "--reload" -WorkingDirectory (Join-Path $ScriptDir "..\backend-langgraph") -WindowStyle Hidden -RedirectStandardOutput $LangGraphLog -RedirectStandardError $LangGraphLog
Start-Sleep -Seconds 3

# Check if Backend LangGraph started
try {
    $null = Invoke-WebRequest -Uri "http://localhost:8002/health" -TimeoutSec 2 -UseBasicParsing
    Write-Host "[OK] Backend LangGraph service started" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Failed to start Backend LangGraph service" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "All services are running!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Mock Salesforce: http://localhost:8001" -ForegroundColor Cyan
Write-Host "Backend MCP: http://localhost:8000" -ForegroundColor Cyan
Write-Host "Backend LangGraph: http://localhost:8002" -ForegroundColor Cyan
Write-Host ""
Write-Host "Logs are being written to: $LogsDir" -ForegroundColor Cyan
Write-Host ""
Write-Host "Services are running in background." -ForegroundColor Yellow
Write-Host "Close those processes to stop the services." -ForegroundColor Yellow
Write-Host ""
Write-Host "Ready for testing! Run: python test-data\test_pipeline.py" -ForegroundColor Green
Write-Host ""
Read-Host "Press Enter to exit"

