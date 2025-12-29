# Script PowerShell pour executer le pipeline reel end-to-end
# Usage: .\run_pipeline_reel.ps1 [-RecordId "001XX000001"] [-UserMessage "Extract data from documents"]

param(
    [string]$RecordId = "001XX000001",
    [string]$UserMessage = "Extract data from documents"
)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Pipeline Reel - Execution End-to-End" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Get script directory and project root
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

# Service URLs
$MockSalesforceUrl = "http://localhost:8001"
$BackendMcpUrl = "http://localhost:8000"
$BackendLangGraphUrl = "http://localhost:8002"

# Service directories
$Services = @(
    @{Name="Mock Salesforce"; Dir="mock-salesforce"; Port=8001; Url=$MockSalesforceUrl},
    @{Name="Backend MCP"; Dir="backend-mcp"; Port=8000; Url=$BackendMcpUrl},
    @{Name="Backend LangGraph"; Dir="backend-langgraph"; Port=8002; Url=$BackendLangGraphUrl}
)

# Process IDs to track started services
$ServiceProcesses = @{}

# Function to check if Python 3.10.9 is installed
function Test-PythonVersion {
    try {
        $pythonVersion = python --version 2>&1
        if ($pythonVersion -match "Python 3\.10\.9") {
            Write-Host "[OK] Python 3.10.9 found: $pythonVersion" -ForegroundColor Green
            return $true
        } else {
            Write-Host "[WARNING] Python version: $pythonVersion (expected 3.10.9)" -ForegroundColor Yellow
            Write-Host "   Continuing anyway..." -ForegroundColor Yellow
            return $true
        }
    } catch {
        Write-Host "[ERROR] Python not found. Please install Python 3.10.9" -ForegroundColor Red
        return $false
    }
}

# Function to check if a port is available
function Test-PortAvailable {
    param([int]$Port)
    try {
        $Connection = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
        return ($null -eq $Connection)
    } catch {
        try {
            $NetstatOutput = netstat -an | Select-String ":$Port\s"
            return ($null -eq $NetstatOutput)
        } catch {
            return $true
        }
    }
}

# Function to wait for service to be ready
function Wait-ForService {
    param(
        [string]$Url,
        [string]$ServiceName,
        [int]$MaxRetries = 30,
        [double]$RetryDelay = 1.0
    )
    
    for ($i = 0; $i -lt $MaxRetries; $i++) {
        try {
            $response = Invoke-WebRequest -Uri "$Url/health" -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                Write-Host "[OK] $ServiceName is ready" -ForegroundColor Green
                return $true
            }
        } catch {
            # Service not ready yet
        }
        
        if ($i -lt $MaxRetries - 1) {
            Start-Sleep -Seconds $RetryDelay
        }
    }
    
    Write-Host "[ERROR] $ServiceName is not ready after $($MaxRetries * $RetryDelay)s" -ForegroundColor Red
    return $false
}

# Function to start a service
function Start-Service {
    param(
        [string]$ServiceName,
        [string]$ServiceDir,
        [int]$Port
    )
    
    $VenvPython = Join-Path $ServiceDir "venv\Scripts\python.exe"
    
    if (-not (Test-Path $VenvPython)) {
        Write-Host "[ERROR] Virtual environment not found for $ServiceName" -ForegroundColor Red
        Write-Host "   Expected: $VenvPython" -ForegroundColor Red
        Write-Host "   Please run: .\setup_venv.ps1" -ForegroundColor Yellow
        return $null
    }
    
    # Check if port is available
    if (-not (Test-PortAvailable -Port $Port)) {
        Write-Host "[WARNING] Port $Port is already in use. Assuming service is already running." -ForegroundColor Yellow
        return $null
    }
    
    Write-Host "Starting $ServiceName on port $Port..." -ForegroundColor Yellow
    $Arguments = "-m", "uvicorn", "app.main:app", "--port", $Port.ToString(), "--reload"
    
    $Process = Start-Process -FilePath $VenvPython -ArgumentList $Arguments -WorkingDirectory $ServiceDir -WindowStyle Hidden -PassThru
    
    if ($Process) {
        Write-Host "[OK] $ServiceName started (PID: $($Process.Id))" -ForegroundColor Green
        return $Process
    } else {
        Write-Host "[ERROR] Failed to start $ServiceName" -ForegroundColor Red
        return $null
    }
}

# Function to stop a service
function Stop-Service {
    param(
        [System.Diagnostics.Process]$Process,
        [string]$ServiceName
    )
    
    if ($Process -and -not $Process.HasExited) {
        Write-Host "Stopping $ServiceName..." -ForegroundColor Yellow
        $Process.Kill()
        $Process.WaitForExit(5000)
        Write-Host "[OK] $ServiceName stopped" -ForegroundColor Green
    }
}

# Step 1: Check prerequisites
Write-Host "Step 1: Checking prerequisites..." -ForegroundColor Cyan
Write-Host ""

if (-not (Test-PythonVersion)) {
    exit 1
}

# Check venvs
$AllVenvsExist = $true
foreach ($service in $Services) {
    $VenvPath = Join-Path (Join-Path $ProjectRoot $service.Dir) "venv\Scripts\python.exe"
    if (-not (Test-Path $VenvPath)) {
        Write-Host "[ERROR] $($service.Name) venv not found: $VenvPath" -ForegroundColor Red
        $AllVenvsExist = $false
    }
}

if (-not $AllVenvsExist) {
    Write-Host ""
    Write-Host "[ERROR] Some virtual environments are missing!" -ForegroundColor Red
    Write-Host "        Please run: .\setup_venv.ps1" -ForegroundColor Yellow
    exit 1
}

Write-Host "[OK] All prerequisites met" -ForegroundColor Green
Write-Host ""

# Step 2: Start services
Write-Host "Step 2: Starting services..." -ForegroundColor Cyan
Write-Host ""

foreach ($service in $Services) {
    $ServiceDir = Join-Path $ProjectRoot $service.Dir
    $Process = Start-Service -ServiceName $service.Name -ServiceDir $ServiceDir -Port $service.Port
    
    if ($Process) {
        $ServiceProcesses[$service.Name] = $Process
        Start-Sleep -Seconds 2
    }
}

Write-Host ""

# Step 3: Wait for services to be ready
Write-Host "Step 3: Waiting for services to be ready..." -ForegroundColor Cyan
Write-Host ""

$AllServicesReady = $true
foreach ($service in $Services) {
    if (-not (Wait-ForService -Url $service.Url -ServiceName $service.Name)) {
        $AllServicesReady = $false
    }
}

if (-not $AllServicesReady) {
    Write-Host ""
    Write-Host "[ERROR] Some services are not ready. Please check the logs." -ForegroundColor Red
    Write-Host "        Stopping started services..." -ForegroundColor Yellow
    
    foreach ($serviceName in $ServiceProcesses.Keys) {
        Stop-Service -Process $ServiceProcesses[$serviceName] -ServiceName $serviceName
    }
    
    exit 1
}

Write-Host ""

# Step 4: Execute pipeline
Write-Host "Step 4: Executing pipeline..." -ForegroundColor Cyan
Write-Host "   Record ID: $RecordId" -ForegroundColor White
Write-Host "   User Message: $UserMessage" -ForegroundColor White
Write-Host ""

try {
    $url = "$BackendMcpUrl/api/mcp/receive-request"
    $payload = @{
        record_id = $RecordId
        session_id = $null
        user_message = $UserMessage
    } | ConvertTo-Json
    
    Write-Host "[SENDING] Sending request to Backend MCP..." -ForegroundColor Yellow
    
    $startTime = Get-Date
    $response = Invoke-RestMethod -Uri $url -Method Post -Body $payload -ContentType "application/json" -TimeoutSec 300
    $elapsedTime = (Get-Date) - $startTime
    
    Write-Host "[OK] Pipeline completed in $($elapsedTime.TotalSeconds.ToString('F2'))s" -ForegroundColor Green
    Write-Host ""
    
    # Display results
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "RESULTS" -ForegroundColor Cyan
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host ""
    
    if ($response.status -eq "success") {
        $workflowData = $response.data
        
        Write-Host "Status: $($workflowData.status)" -ForegroundColor Green
        Write-Host "Workflow ID: $($workflowData.workflow_id)" -ForegroundColor White
        Write-Host ""
        
        # Extract extracted data
        $workflowStepsData = $workflowData.data
        $responseHandling = $workflowStepsData.response_handling
        $extractedData = $responseHandling.extracted_data
        $confidenceScores = $responseHandling.confidence_scores
        
        if (-not $extractedData) {
            $mcpSending = $workflowStepsData.mcp_sending
            $mcpResponse = $mcpSending.mcp_response
            $extractedData = $mcpResponse.extracted_data
            $confidenceScores = $mcpResponse.confidence_scores
        }
        
        if ($extractedData) {
            $fieldCount = $extractedData.Count
            $fieldWord = if ($fieldCount -eq 1) { "field" } else { "fields" }
            Write-Host "Extracted Data: $fieldCount $fieldWord" -ForegroundColor Cyan
            $separator = "-" * 60
            Write-Host $separator -ForegroundColor Gray
            
            foreach ($fieldName in $extractedData.Keys) {
                $value = $extractedData[$fieldName]
                $confidence = if ($confidenceScores -and $confidenceScores.ContainsKey($fieldName)) {
                    $confidenceScores[$fieldName]
                } else {
                    0.0
                }
                Write-Host "  $fieldName : $value (confidence: $($confidence.ToString('P')))" -ForegroundColor White
            }
            
            if ($confidenceScores) {
                $avgConfidence = ($confidenceScores.Values | Measure-Object -Average).Average
                Write-Host ""
                Write-Host "Average Confidence: $($avgConfidence.ToString('P'))" -ForegroundColor Cyan
            }
        } else {
            Write-Host "[WARNING] No extracted data found in response" -ForegroundColor Yellow
        }
    } else {
        Write-Host "Status: $($response.status)" -ForegroundColor Red
        if ($response.error) {
            Write-Host "Error: $($response.error.message)" -ForegroundColor Red
        }
    }
    
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Cyan
    
} catch {
    Write-Host "[ERROR] Pipeline execution failed: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host "Response: $responseBody" -ForegroundColor Red
    }
}

Write-Host ""

# Step 5: Cleanup
Write-Host "Step 5: Cleaning up..." -ForegroundColor Cyan
Write-Host ""

foreach ($serviceName in $ServiceProcesses.Keys) {
    Stop-Service -Process $ServiceProcesses[$serviceName] -ServiceName $serviceName
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Pipeline execution completed" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

