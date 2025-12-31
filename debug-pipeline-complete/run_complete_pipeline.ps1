# Script PowerShell pour exécuter le pipeline complet de debug
# Ce script exécute tous les steps du pipeline de bout en bout

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Complete Pipeline Debug Execution" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment exists
$VenvPath = Join-Path $ProjectRoot "backend-mcp\venv"
if (-not (Test-Path $VenvPath)) {
    Write-Host "[ERROR] Virtual environment not found at: $VenvPath" -ForegroundColor Red
    Write-Host "Please create the virtual environment first:" -ForegroundColor Yellow
    Write-Host "  cd backend-mcp" -ForegroundColor Yellow
    Write-Host "  python -m venv venv" -ForegroundColor Yellow
    Write-Host "  .\venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    Write-Host "  pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& "$VenvPath\Scripts\Activate.ps1"
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to activate virtual environment" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Virtual environment activated" -ForegroundColor Green
Write-Host ""

# Check if services are running (optional check)
Write-Host "Checking if services are running (optional)..." -ForegroundColor Yellow
$ServicesRunning = $true

try {
    $null = Invoke-WebRequest -Uri "http://localhost:8001/health" -TimeoutSec 2 -UseBasicParsing
    Write-Host "[OK] Mock Salesforce service is running" -ForegroundColor Green
} catch {
    Write-Host "[WARNING] Mock Salesforce service is not running" -ForegroundColor Yellow
    $ServicesRunning = $false
}

try {
    $null = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 2 -UseBasicParsing
    Write-Host "[OK] Backend MCP service is running" -ForegroundColor Green
} catch {
    Write-Host "[WARNING] Backend MCP service is not running" -ForegroundColor Yellow
    $ServicesRunning = $false
}

try {
    $null = Invoke-WebRequest -Uri "http://localhost:8002/health" -TimeoutSec 2 -UseBasicParsing
    Write-Host "[OK] Backend LangGraph service is running" -ForegroundColor Green
} catch {
    Write-Host "[WARNING] Backend LangGraph service is not running" -ForegroundColor Yellow
    Write-Host "  Note: Step 7 (MCP Sending) requires LangGraph service to be running" -ForegroundColor Yellow
    $ServicesRunning = $false
}

if (-not $ServicesRunning) {
    Write-Host ""
    Write-Host "[INFO] Some services are not running. Some steps may be skipped." -ForegroundColor Yellow
    Write-Host "To start services, run: docker-compose up -d" -ForegroundColor Yellow
    Write-Host ""
}

# Run the complete pipeline script
Write-Host "Running complete pipeline debug script..." -ForegroundColor Yellow
Write-Host ""
python "$ScriptDir\run_complete_pipeline.py"
$ExitCode = $LASTEXITCODE

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
if ($ExitCode -eq 0) {
    Write-Host "Pipeline execution completed successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Check the following files for results:" -ForegroundColor Yellow
    Write-Host "  - debug-pipeline-complete/step*_output.json" -ForegroundColor White
    Write-Host "  - debug-pipeline-complete/pipeline_summary_*.json" -ForegroundColor White
    Write-Host "  - debug-pipeline-complete/complete_results_*.json" -ForegroundColor White
    Write-Host "  - debug-pipeline-complete/complete_pipeline_*.log" -ForegroundColor White
} else {
    Write-Host "Pipeline execution completed with errors" -ForegroundColor Red
    Write-Host "Check the log file for details: debug-pipeline-complete/complete_pipeline_*.log" -ForegroundColor Yellow
}

exit $ExitCode

