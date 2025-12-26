# Script to start all services for testing (Windows)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Starting OptiClaims Services for Testing" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Create logs directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$LogsDir = Join-Path $ScriptDir "results\logs"
New-Item -ItemType Directory -Force -Path $LogsDir | Out-Null

# Create data directory for SQLite
$DataDir = Join-Path $ProjectRoot "backend-mcp\data"
New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
Write-Host "[OK] Data directory ready for SQLite" -ForegroundColor Green
Write-Host ""

# Check if venvs exist before starting services
Write-Host "Checking virtual environments..." -ForegroundColor Yellow
$Services = @(
    @{Name="Mock Salesforce"; Dir="mock-salesforce"},
    @{Name="Backend MCP"; Dir="backend-mcp"},
    @{Name="Backend LangGraph"; Dir="backend-langgraph"}
)

$AllVenvsExist = $true
foreach ($service in $Services) {
    $VenvPath = Join-Path (Join-Path $ProjectRoot $service.Dir) "venv\Scripts\python.exe"
    if (Test-Path $VenvPath) {
        Write-Host "  ✅ $($service.Name) venv found" -ForegroundColor Green
    } else {
        Write-Host "  ❌ $($service.Name) venv not found" -ForegroundColor Red
        Write-Host "     Expected: $VenvPath" -ForegroundColor Red
        $AllVenvsExist = $false
    }
}

if (-not $AllVenvsExist) {
    Write-Host ""
    Write-Host "[ERROR] Some virtual environments are missing!" -ForegroundColor Red
    Write-Host "        Please run: .\setup_venv.ps1" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

Write-Host ""

# Function to check if a port is available
function Test-PortAvailable {
    param([int]$Port)
    try {
        $Connection = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
        return ($null -eq $Connection)
    } catch {
        # Fallback: try netstat if Get-NetTCPConnection is not available
        try {
            $NetstatOutput = netstat -an | Select-String ":$Port\s"
            return ($null -eq $NetstatOutput)
        } catch {
            # If both fail, assume port is available (will fail later with clearer error)
            return $true
        }
    }
}

# Function to stop processes using a specific port
function Stop-ProcessOnPort {
    param(
        [int]$Port,
        [string]$ServiceName
    )
    
    try {
        $Processes = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
        $Killed = $false
        
        foreach ($ProcessId in $Processes) {
            if ($ProcessId) {
                Write-Host "  Stopping process on port $Port (PID: $ProcessId)..." -ForegroundColor Yellow
                Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
                $Killed = $true
                Start-Sleep -Milliseconds 500
            }
        }
        
        if ($Killed) {
            # Wait a bit for port to be released
            Start-Sleep -Seconds 1
            return $true
        }
        return $false
    } catch {
        return $false
    }
}

# Function to start a service with venv
function Start-ServiceWithVenv {
    param(
        [string]$ServiceName,
        [string]$ServiceDir,
        [int]$Port,
        [string]$LogFile
    )
    
    $VenvPython = Join-Path $ServiceDir "venv\Scripts\python.exe"
    
    # Check if venv exists
    if (-not (Test-Path $VenvPython)) {
        Write-Host "[ERROR] Virtual environment not found for $ServiceName" -ForegroundColor Red
        Write-Host "        Expected: $VenvPython" -ForegroundColor Red
        Write-Host "        Please run: .\setup_venv.ps1" -ForegroundColor Yellow
        return $false
    }
    
    # Use venv Python to run uvicorn
    $WorkingDir = $ServiceDir
    $Arguments = "-m", "uvicorn", "app.main:app", "--port", $Port.ToString(), "--reload"
    
    # PowerShell doesn't allow both RedirectStandardOutput and RedirectStandardError to point to same file
    # Solution: Use separate files for stdout and stderr
    $StdErrFile = $LogFile -replace '\.log$', '.stderr.log'
    
    $Process = Start-Process -FilePath $VenvPython -ArgumentList $Arguments -WorkingDirectory $WorkingDir -WindowStyle Hidden -RedirectStandardOutput $LogFile -RedirectStandardError $StdErrFile -PassThru
    
    return $true
}

# Start Mock Salesforce service
Write-Host "Starting Mock Salesforce service on port 8001..." -ForegroundColor Yellow
$MockSfDir = Join-Path $ProjectRoot "mock-salesforce"
$MockSfLog = Join-Path $LogsDir "mock-salesforce.log"

# Check if port is available
if (-not (Test-PortAvailable -Port 8001)) {
    Write-Host "[WARNING] Port 8001 is already in use." -ForegroundColor Yellow
    $Response = Read-Host "  Do you want to stop the process using port 8001 and continue? (Y/n)"
    # Default to 'y' if user just presses Enter (empty response)
    if ([string]::IsNullOrEmpty($Response) -or $Response -eq "y" -or $Response -eq "Y") {
        if (Stop-ProcessOnPort -Port 8001 -ServiceName "Mock Salesforce") {
            Write-Host "[OK] Process stopped. Continuing..." -ForegroundColor Green
        } else {
            Write-Host "[ERROR] Failed to stop process on port 8001." -ForegroundColor Red
            Write-Host "        Please stop it manually and try again." -ForegroundColor Yellow
            exit 1
        }
    } else {
        Write-Host "[ERROR] Port 8001 is in use. Exiting." -ForegroundColor Red
        Write-Host "        You can check what's using the port with: Get-NetTCPConnection -LocalPort 8001" -ForegroundColor Yellow
        exit 1
    }
}

if (-not (Start-ServiceWithVenv -ServiceName "Mock Salesforce" -ServiceDir $MockSfDir -Port 8001 -LogFile $MockSfLog)) {
    exit 1
}
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
$McpDir = Join-Path $ProjectRoot "backend-mcp"
$McpLog = Join-Path $LogsDir "backend-mcp.log"

# Check if port is available
if (-not (Test-PortAvailable -Port 8000)) {
    Write-Host "[WARNING] Port 8000 is already in use." -ForegroundColor Yellow
    $Response = Read-Host "  Do you want to stop the process using port 8000 and continue? (Y/n)"
    # Default to 'y' if user just presses Enter (empty response)
    if ([string]::IsNullOrEmpty($Response) -or $Response -eq "y" -or $Response -eq "Y") {
        if (Stop-ProcessOnPort -Port 8000 -ServiceName "Backend MCP") {
            Write-Host "[OK] Process stopped. Continuing..." -ForegroundColor Green
        } else {
            Write-Host "[ERROR] Failed to stop process on port 8000." -ForegroundColor Red
            Write-Host "        Please stop it manually and try again." -ForegroundColor Yellow
            exit 1
        }
    } else {
        Write-Host "[ERROR] Port 8000 is in use. Exiting." -ForegroundColor Red
        Write-Host "        You can check what's using the port with: Get-NetTCPConnection -LocalPort 8000" -ForegroundColor Yellow
        exit 1
    }
}

if (-not (Start-ServiceWithVenv -ServiceName "Backend MCP" -ServiceDir $McpDir -Port 8000 -LogFile $McpLog)) {
    exit 1
}
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
$LangGraphDir = Join-Path $ProjectRoot "backend-langgraph"
$LangGraphLog = Join-Path $LogsDir "backend-langgraph.log"

# Create .env file for LangGraph with MOCK_MODE enabled if it doesn't exist
$LangGraphEnvFile = Join-Path $LangGraphDir ".env"
if (-not (Test-Path $LangGraphEnvFile)) {
    Write-Host "  Creating .env file with MOCK_MODE=true for testing..." -ForegroundColor Yellow
    @"
# Backend LangGraph Configuration (Auto-generated for testing)
LOG_LEVEL=INFO
DEBUG=false
HOST=0.0.0.0
PORT=8002
MOCK_MODE=true
"@ | Out-File -FilePath $LangGraphEnvFile -Encoding utf8
    Write-Host "  ✅ .env file created with MOCK_MODE=true" -ForegroundColor Green
} else {
    # Check if MOCK_MODE is set, if not add it
    $envContent = Get-Content $LangGraphEnvFile -Raw
    if ($envContent -notmatch "MOCK_MODE") {
        Write-Host "  Adding MOCK_MODE=true to existing .env file..." -ForegroundColor Yellow
        Add-Content -Path $LangGraphEnvFile -Value "`nMOCK_MODE=true" -Encoding utf8
        Write-Host "  ✅ MOCK_MODE=true added to .env file" -ForegroundColor Green
    }
}

# Check if port is available
if (-not (Test-PortAvailable -Port 8002)) {
    Write-Host "[WARNING] Port 8002 is already in use." -ForegroundColor Yellow
    $Response = Read-Host "  Do you want to stop the process using port 8002 and continue? (Y/n)"
    # Default to 'y' if user just presses Enter (empty response)
    if ([string]::IsNullOrEmpty($Response) -or $Response -eq "y" -or $Response -eq "Y") {
        if (Stop-ProcessOnPort -Port 8002 -ServiceName "Backend LangGraph") {
            Write-Host "[OK] Process stopped. Continuing..." -ForegroundColor Green
        } else {
            Write-Host "[ERROR] Failed to stop process on port 8002." -ForegroundColor Red
            Write-Host "        Please stop it manually and try again." -ForegroundColor Yellow
            exit 1
        }
    } else {
        Write-Host "[ERROR] Port 8002 is in use. Exiting." -ForegroundColor Red
        Write-Host "        You can check what's using the port with: Get-NetTCPConnection -LocalPort 8002" -ForegroundColor Yellow
        exit 1
    }
}

if (-not (Start-ServiceWithVenv -ServiceName "Backend LangGraph" -ServiceDir $LangGraphDir -Port 8002 -LogFile $LangGraphLog)) {
    exit 1
}
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

