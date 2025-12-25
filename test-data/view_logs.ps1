# Script to view and filter logs (Windows)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogsDir = Join-Path $ScriptDir "results\logs"

if (-not (Test-Path $LogsDir)) {
    Write-Host "[ERROR] Logs directory not found: $LogsDir" -ForegroundColor Red
    exit 1
}

Write-Host "Available log files:" -ForegroundColor Cyan
Get-ChildItem "$LogsDir\*.log" | ForEach-Object {
    $size = [math]::Round($_.Length / 1KB, 2)
    Write-Host "  $($_.Name) ($size KB)" -ForegroundColor Yellow
}
Write-Host ""

if ($args.Count -eq 0) {
    Write-Host "Usage: .\view_logs.ps1 [service] [filter]" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Services: mock-salesforce, backend-mcp, backend-langgraph, all" -ForegroundColor Cyan
    Write-Host "Filters: error, workflow_id=<id>, record_id=<id>" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Yellow
    Write-Host "  .\view_logs.ps1 backend-mcp                    # Show all backend-mcp logs"
    Write-Host "  .\view_logs.ps1 all error                     # Show all errors"
    Write-Host "  .\view_logs.ps1 backend-mcp workflow_id=xxx   # Filter by workflow_id"
    exit 0
}

$Service = $args[0]
$Filter = $args[1]

if ($Service -eq "all") {
    $Files = Get-ChildItem "$LogsDir\*.log"
} else {
    $Files = Get-ChildItem "$LogsDir\${Service}.log" -ErrorAction SilentlyContinue
}

if (-not $Files) {
    Write-Host "[ERROR] No log files found" -ForegroundColor Red
    exit 1
}

if (-not $Filter) {
    # Show all logs
    foreach ($file in $Files) {
        Write-Host "=== $($file.Name) ===" -ForegroundColor Cyan
        Get-Content $file.FullName -Tail 50
        Write-Host ""
    }
} elseif ($Filter -eq "error") {
    # Filter errors
    foreach ($file in $Files) {
        Write-Host "=== Errors in $($file.Name) ===" -ForegroundColor Cyan
        Get-Content $file.FullName | Select-String -Pattern "error|failed|exception" -CaseSensitive:$false | Select-Object -Last 20
        Write-Host ""
    }
} elseif ($Filter -like "workflow_id=*") {
    # Filter by workflow_id
    $WorkflowId = $Filter -replace "workflow_id=", ""
    foreach ($file in $Files) {
        Write-Host "=== Workflow $WorkflowId in $($file.Name) ===" -ForegroundColor Cyan
        Get-Content $file.FullName | Select-String -Pattern $WorkflowId
        Write-Host ""
    }
} elseif ($Filter -like "record_id=*") {
    # Filter by record_id
    $RecordId = $Filter -replace "record_id=", ""
    foreach ($file in $Files) {
        Write-Host "=== Record $RecordId in $($file.Name) ===" -ForegroundColor Cyan
        Get-Content $file.FullName | Select-String -Pattern $RecordId
        Write-Host ""
    }
} else {
    Write-Host "[ERROR] Unknown filter: $Filter" -ForegroundColor Red
    exit 1
}

