# Script to setup virtual environments and install requirements for all services (Windows)
# Usage: .\setup_venv.ps1

$ErrorActionPreference = "Stop"

# Get script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "OptiClaims - Virtual Environment Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Python version
Write-Host "Checking Python version..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Python not found"
    }
    
    $versionMatch = $pythonVersion -match "Python (\d+)\.(\d+)(?:\.(\d+))?"
    if (-not $versionMatch) {
        throw "Could not parse Python version"
    }
    
    $majorVersion = [int]$matches[1]
    $minorVersion = [int]$matches[2]
    $patchVersion = if ($matches[3]) { [int]$matches[3] } else { 0 }
    
    # Check if version is 3.10.9+ or 3.11+
    $isValid = $false
    if ($majorVersion -gt 3) {
        $isValid = $true
    } elseif ($majorVersion -eq 3) {
        if ($minorVersion -gt 10) {
            $isValid = $true
        } elseif ($minorVersion -eq 10 -and $patchVersion -ge 9) {
            $isValid = $true
        }
    }
    
    if (-not $isValid) {
        Write-Host "❌ Python 3.10.9+ required. Found: $pythonVersion" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "✅ $pythonVersion found" -ForegroundColor Green
} catch {
    Write-Host "❌ Python not found. Please install Python 3.10.9 or higher." -ForegroundColor Red
    Write-Host "   Download from: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}
Write-Host ""

# Check if venv module is available
Write-Host "Checking venv module..." -ForegroundColor Yellow
try {
    python -m venv --help | Out-Null
    Write-Host "✅ venv module available" -ForegroundColor Green
} catch {
    Write-Host "❌ venv module not available." -ForegroundColor Red
    exit 1
}
Write-Host ""

# Services to setup
$Services = @("backend-mcp", "backend-langgraph", "mock-salesforce")

# Function to setup venv for a service
function Setup-ServiceVenv {
    param(
        [string]$Service
    )
    
    $ServiceDir = Join-Path $ScriptDir $Service
    $VenvDir = Join-Path $ServiceDir "venv"
    
    Write-Host "Setting up $Service..." -ForegroundColor Cyan
    
    if (-not (Test-Path $ServiceDir)) {
        Write-Host "  ❌ Service directory not found: $ServiceDir" -ForegroundColor Red
        return $false
    }
    
    # Create venv if it doesn't exist
    if (-not (Test-Path $VenvDir)) {
        Write-Host "  Creating virtual environment..." -ForegroundColor Yellow
        python -m venv $VenvDir
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  ❌ Failed to create virtual environment" -ForegroundColor Red
            return $false
        }
        Write-Host "  ✅ Virtual environment created" -ForegroundColor Green
    } else {
        Write-Host "  Virtual environment already exists, skipping creation" -ForegroundColor Yellow
    }
    
    # Install requirements using venv Python directly
    Write-Host "  Installing requirements..." -ForegroundColor Yellow
    
    # Use venv Python directly (no need to activate)
    $VenvPython = Join-Path $VenvDir "Scripts\python.exe"
    
    if (-not (Test-Path $VenvPython)) {
        Write-Host "  ❌ Python not found in venv: $VenvPython" -ForegroundColor Red
        return $false
    }
    
    # Upgrade pip using venv Python
    & $VenvPython -m pip install --upgrade pip --quiet
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ❌ Failed to upgrade pip" -ForegroundColor Red
        return $false
    }
    
    # Install requirements using venv Python
    $RequirementsFile = Join-Path $ServiceDir "requirements.txt"
    if (Test-Path $RequirementsFile) {
        & $VenvPython -m pip install -r $RequirementsFile
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  ❌ Failed to install requirements" -ForegroundColor Red
            return $false
        }
        Write-Host "  ✅ Requirements installed" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  No requirements.txt found" -ForegroundColor Yellow
    }
    
    Write-Host "✅ $Service setup complete" -ForegroundColor Green
    Write-Host ""
    return $true
}

# Setup each service
foreach ($service in $Services) {
    Setup-ServiceVenv -Service $service
}

# Create data directory for SQLite (session storage)
Write-Host "Preparing SQLite session storage..." -ForegroundColor Yellow
$DataDir = Join-Path $ScriptDir "backend-mcp\data"
try {
    New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
    Write-Host "✅ Data directory ready for SQLite" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Could not create data directory: $DataDir" -ForegroundColor Yellow
    Write-Host "   It will be created automatically on first service start" -ForegroundColor Yellow
}
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✅ Setup complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "To activate a service's virtual environment:" -ForegroundColor Cyan
Write-Host "  cd backend-mcp; .\venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "  cd backend-langgraph; .\venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "  cd mock-salesforce; .\venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host ""
Write-Host "To run a service:" -ForegroundColor Cyan
Write-Host "  .\venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "  uvicorn app.main:app --reload --port <PORT>" -ForegroundColor White
Write-Host ""

