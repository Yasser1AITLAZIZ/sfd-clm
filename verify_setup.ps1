# Script to verify that the setup is correct (Windows)
# Usage: .\verify_setup.ps1

$ErrorActionPreference = "Continue"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "OptiClaims - Setup Verification" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$AllOk = $true

# Check Python
Write-Host "Checking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ $pythonVersion" -ForegroundColor Green
    } else {
        throw "Python not found"
    }
} catch {
    Write-Host "  ❌ Python not found" -ForegroundColor Red
    $AllOk = $false
}

# Check services
$Services = @("backend-mcp", "backend-langgraph", "mock-salesforce")
foreach ($service in $Services) {
    Write-Host "Checking $service..." -ForegroundColor Yellow
    $ServiceDir = Join-Path $ScriptDir $service
    $VenvDir = Join-Path $ServiceDir "venv"
    
    if (-not (Test-Path $ServiceDir)) {
        Write-Host "  ❌ Service directory not found" -ForegroundColor Red
        $AllOk = $false
        continue
    }
    
    if (-not (Test-Path $VenvDir)) {
        Write-Host "  ❌ Virtual environment not found" -ForegroundColor Red
        Write-Host "     Run: .\setup_venv.ps1" -ForegroundColor Yellow
        $AllOk = $false
        continue
    }
    
    if (-not (Test-Path (Join-Path $ServiceDir "requirements.txt"))) {
        Write-Host "  ⚠️  No requirements.txt found" -ForegroundColor Yellow
    } else {
        Write-Host "  ✅ Virtual environment exists" -ForegroundColor Green
        Write-Host "  ✅ requirements.txt found" -ForegroundColor Green
    }
}

# Check test-data
Write-Host "Checking test-data..." -ForegroundColor Yellow
$TestDataDir = Join-Path $ScriptDir "test-data"
if (Test-Path $TestDataDir) {
    $DocumentsDir = Join-Path $TestDataDir "documents"
    $FieldsFile = Join-Path $TestDataDir "fields\fields.json"
    
    if (Test-Path $DocumentsDir) {
        $PdfCount = (Get-ChildItem -Path $DocumentsDir -Filter "*.pdf" -ErrorAction SilentlyContinue).Count
        if ($PdfCount -gt 0) {
            Write-Host "  ✅ Documents directory with $PdfCount PDF file(s)" -ForegroundColor Green
        } else {
            Write-Host "  ⚠️  Documents directory exists but no PDF files" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  ⚠️  Documents directory not found" -ForegroundColor Yellow
    }
    
    if (Test-Path $FieldsFile) {
        Write-Host "  ✅ Fields file found" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  Fields file not found" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ⚠️  test-data directory not found" -ForegroundColor Yellow
}

Write-Host ""
if ($AllOk) {
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "✅ All checks passed!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    exit 0
} else {
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "❌ Some checks failed" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Cyan
    exit 1
}

