# Script to view and filter logs (Windows) - Enhanced version with traceback support

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
    Write-Host "Usage: .\view_logs.ps1 [service] [filter] [options]" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Services: mock-salesforce, backend-mcp, backend-langgraph, all" -ForegroundColor Cyan
    Write-Host "Filters: error, traceback, workflow_id=<id>, record_id=<id>" -ForegroundColor Cyan
    Write-Host "Options: verbose, stderr" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Yellow
    Write-Host "  .\view_logs.ps1 backend-mcp                    # Show last 100 lines"
    Write-Host "  .\view_logs.ps1 all error                     # Show all errors with context"
    Write-Host "  .\view_logs.ps1 backend-mcp traceback          # Show tracebacks only"
    Write-Host "  .\view_logs.ps1 backend-mcp error verbose      # Show errors with full details"
    Write-Host "  .\view_logs.ps1 backend-mcp error stderr       # Include stderr.log files"
    Write-Host "  .\view_logs.ps1 backend-mcp workflow_id=xxx    # Filter by workflow_id"
    exit 0
}

$Service = $args[0]
$Filter = $args[1]
$Options = $args[2..($args.Count - 1)]

# Check for options
$Verbose = $Options -contains "verbose"
$IncludeStderr = $Options -contains "stderr"

# Get log files
if ($Service -eq "all") {
    $Files = Get-ChildItem "$LogsDir\*.log" | Where-Object { -not $IncludeStderr -or $_.Name -notlike "*.stderr.log" }
    if ($IncludeStderr) {
        $StderrFiles = Get-ChildItem "$LogsDir\*.stderr.log"
    }
} else {
    $Files = Get-ChildItem "$LogsDir\${Service}.log" -ErrorAction SilentlyContinue
    if ($IncludeStderr) {
        $StderrFiles = Get-ChildItem "$LogsDir\${Service}.stderr.log" -ErrorAction SilentlyContinue
    }
}

if (-not $Files -and -not $StderrFiles) {
    Write-Host "[ERROR] No log files found" -ForegroundColor Red
    exit 1
}

function Show-ErrorWithContext {
    param(
        [string]$FilePath,
        [int]$ContextLines = 5
    )
    
    $lines = Get-Content $FilePath
    $errorLines = @()
    
    for ($i = 0; $i -lt $lines.Length; $i++) {
        $line = $lines[$i]
        if ($line -match "error|failed|exception|traceback" -and $line -notmatch "INFO|DEBUG") {
            $start = [Math]::Max(0, $i - $ContextLines)
            $end = [Math]::Min($lines.Length - 1, $i + $ContextLines)
            
            if ($start -gt 0) {
                Write-Host "  ..." -ForegroundColor DarkGray
            }
            
            for ($j = $start; $j -le $end; $j++) {
                $currentLine = $lines[$j]
                $lineNum = $j + 1
                
                if ($j -eq $i) {
                    # Error line - highlight in red
                    Write-Host "  [$lineNum] $currentLine" -ForegroundColor Red
                } elseif ($currentLine -match "traceback|Traceback") {
                    # Traceback line - highlight in yellow
                    Write-Host "  [$lineNum] $currentLine" -ForegroundColor Yellow
                } else {
                    # Context line
                    Write-Host "  [$lineNum] $currentLine" -ForegroundColor Gray
                }
            }
            
            if ($end -lt ($lines.Length - 1)) {
                Write-Host "  ..." -ForegroundColor DarkGray
            }
            Write-Host ""
        }
    }
}

function Show-Traceback {
    param([string]$FilePath)
    
    $content = Get-Content $FilePath -Raw
    $lines = Get-Content $FilePath
    
    $inTraceback = $false
    $tracebackLines = @()
    
    for ($i = 0; $i -lt $lines.Length; $i++) {
        $line = $lines[$i]
        
        if ($line -match "Traceback|traceback") {
            $inTraceback = $true
            $tracebackLines = @()
            $tracebackLines += $line
        } elseif ($inTraceback) {
            if ($line -match "^\s+File |^\s+at |^\s+in |^\s+raise |^\s+Exception:") {
                $tracebackLines += $line
            } elseif ($line.Trim() -eq "" -or $line -match "^\d{4}-\d{2}-\d{2}") {
                # End of traceback
                if ($tracebackLines.Count -gt 0) {
                    Write-Host "  Traceback found at line $($i - $tracebackLines.Count + 1):" -ForegroundColor Yellow
                    foreach ($tbLine in $tracebackLines) {
                        Write-Host "    $tbLine" -ForegroundColor Yellow
                    }
                    Write-Host ""
                }
                $inTraceback = $false
                $tracebackLines = @()
            } else {
                $tracebackLines += $line
            }
        }
    }
    
    # Handle traceback at end of file
    if ($inTraceback -and $tracebackLines.Count -gt 0) {
        Write-Host "  Traceback found at end of file:" -ForegroundColor Yellow
        foreach ($tbLine in $tracebackLines) {
            Write-Host "    $tbLine" -ForegroundColor Yellow
        }
        Write-Host ""
    }
}

if (-not $Filter) {
    # Show all logs - increased to 100 lines
    foreach ($file in $Files) {
        Write-Host "=== $($file.Name) ===" -ForegroundColor Cyan
        Get-Content $file.FullName -Tail 100
        Write-Host ""
    }
    
    if ($IncludeStderr -and $StderrFiles) {
        foreach ($file in $StderrFiles) {
            Write-Host "=== $($file.Name) ===" -ForegroundColor Magenta
            Get-Content $file.FullName -Tail 100
            Write-Host ""
        }
    }
} elseif ($Filter -eq "error") {
    # Filter errors with context
    foreach ($file in $Files) {
        Write-Host "=== Errors in $($file.Name) ===" -ForegroundColor Cyan
        if ($Verbose) {
            Show-ErrorWithContext -FilePath $file.FullName -ContextLines 10
        } else {
            Show-ErrorWithContext -FilePath $file.FullName -ContextLines 5
        }
        Write-Host ""
    }
    
    if ($IncludeStderr -and $StderrFiles) {
        foreach ($file in $StderrFiles) {
            Write-Host "=== Errors in $($file.Name) ===" -ForegroundColor Magenta
            if ($Verbose) {
                Show-ErrorWithContext -FilePath $file.FullName -ContextLines 10
            } else {
                Show-ErrorWithContext -FilePath $file.FullName -ContextLines 5
            }
            Write-Host ""
        }
    }
} elseif ($Filter -eq "traceback") {
    # Show only tracebacks
    foreach ($file in $Files) {
        Write-Host "=== Tracebacks in $($file.Name) ===" -ForegroundColor Cyan
        Show-Traceback -FilePath $file.FullName
        Write-Host ""
    }
    
    if ($IncludeStderr -and $StderrFiles) {
        foreach ($file in $StderrFiles) {
            Write-Host "=== Tracebacks in $($file.Name) ===" -ForegroundColor Magenta
            Show-Traceback -FilePath $file.FullName
            Write-Host ""
        }
    }
} elseif ($Filter -like "workflow_id=*") {
    # Filter by workflow_id
    $WorkflowId = $Filter -replace "workflow_id=", ""
    foreach ($file in $Files) {
        Write-Host "=== Workflow $WorkflowId in $($file.Name) ===" -ForegroundColor Cyan
        Get-Content $file.FullName | Select-String -Pattern $WorkflowId -Context 3,3
        Write-Host ""
    }
    
    if ($IncludeStderr -and $StderrFiles) {
        foreach ($file in $StderrFiles) {
            Write-Host "=== Workflow $WorkflowId in $($file.Name) ===" -ForegroundColor Magenta
            Get-Content $file.FullName | Select-String -Pattern $WorkflowId -Context 3,3
            Write-Host ""
        }
    }
} elseif ($Filter -like "record_id=*") {
    # Filter by record_id
    $RecordId = $Filter -replace "record_id=", ""
    foreach ($file in $Files) {
        Write-Host "=== Record $RecordId in $($file.Name) ===" -ForegroundColor Cyan
        Get-Content $file.FullName | Select-String -Pattern $RecordId -Context 3,3
        Write-Host ""
    }
    
    if ($IncludeStderr -and $StderrFiles) {
        foreach ($file in $StderrFiles) {
            Write-Host "=== Record $RecordId in $($file.Name) ===" -ForegroundColor Magenta
            Get-Content $file.FullName | Select-String -Pattern $RecordId -Context 3,3
            Write-Host ""
        }
    }
} else {
    Write-Host "[ERROR] Unknown filter: $Filter" -ForegroundColor Red
    exit 1
}
